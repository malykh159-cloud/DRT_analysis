"""Exact Gaussian dynamics with reflecting linear walls (Pakman & Paninski).

Adapted from ciuccislab/pyDRTtools HMC.py, MIT, copyright (c) 2023 ciuccislab.
See THIRD_PARTY_NOTICES.md. No leapfrog discretization or acceptance tuning.
Uses local Generator, correct elementwise feasibility, outward root selection,
bounded reflection work and cancellation at each reflection.
"""
import numpy as np
from scipy.linalg import cholesky
from .base import check_cancel


def sample_chain(mean, covariance, initial, settings, rng, cancel=None, progress=None):
    transform = cholesky(covariance, lower=True)
    # Work in projected constraint coordinates F*y rather than recomputing
    # F@position and F@velocity at every impact. F F.T = covariance, so this
    # is algebraically the same whitened exact HMC, with O(d) reflections.
    norms = np.diag(covariance)
    position = initial-mean
    if np.any(initial < 0):
        raise ValueError("HMC initial position violates positivity.")
    draws = np.empty((settings.samples, len(mean)))
    rejected = reflections = 0
    total = settings.warmup+settings.samples
    tolerance = 1e-10*np.maximum(1., np.abs(mean))
    for iteration in range(total):
        check_cancel(cancel)
        old = position.copy()
        velocity = transform@rng.normal(size=len(mean))
        remaining = settings.trajectory_time
        last = -1
        valid = False
        for bounce in range(settings.max_reflections):
            check_cancel(cancel)
            fa, fb = velocity, position
            radius = np.hypot(fa, fb)
            times = np.full(len(mean), np.inf)
            hit = (radius > 0) & (np.abs(mean) <= radius)
            # f(t)=fa*sin(t)+fb*cos(t)+mean. Select the outward crossing.
            times[hit] = np.mod(np.arctan2(fa[hit], fb[hit])+
                                np.arccos(np.clip(-mean[hit]/radius[hit], -1, 1)), 2*np.pi)
            if last >= 0 and times[last] < 1e-10:
                times[last] = np.inf
            wall = int(np.argmin(times))
            travel = min(remaining, times[wall])
            c, s = np.cos(travel), np.sin(travel)
            position, velocity = position*c+velocity*s, velocity*c-position*s
            remaining -= travel
            if remaining <= 1e-12:
                valid = True
                break
            velocity -= 2*velocity[wall]/norms[wall]*covariance[:, wall]
            last = wall
            reflections += 1
        candidate = mean+position
        if not valid or not np.isfinite(candidate).all() or np.any(candidate < -tolerance):
            position = old
            rejected += 1
            candidate = mean+position
        # Reject any negative round-off draw rather than clipping samples.
        if np.any(candidate < 0):
            position = old
            candidate = mean+position
            if valid:
                rejected += 1
        if iteration >= settings.warmup:
            draws[iteration-settings.warmup] = candidate
        if progress and (iteration % 10 == 0 or iteration+1 == total):
            progress(iteration+1, total)
    return draws, {"acceptance_rate": 1-rejected/total, "problematic_transitions": rejected,
                   "reflections": reflections, "iterations": total}
