"""Model-dependent R||CPE approximation of a finite DRT integration region.

Z = R / (1 + (j omega tau_peak)**n), Q = tau_peak**n / R.
See https://doi.org/10.3390/en15030792, equations 33-34.
This is not an independent equivalent-circuit fit to the measured spectrum.
"""
import numpy as np
from scipy.optimize import minimize_scalar


def estimate_cpe(tau, gamma, peak, frequency):
    if peak.edge or peak.rp_ohm <= 0:
        return None, None, "Unavailable: unresolved boundary peak or zero area."
    left, right = np.log([peak.left_tau_s, peak.right_tau_s])
    x = np.log(tau)
    inside = (x > left) & (x < right)
    grid = np.r_[left, x[inside], right]
    mass = np.interp(grid, x, gamma)
    omega = 2*np.pi*np.asarray(frequency)
    z = np.trapezoid(mass[None, :]/(1+1j*omega[:, None]*np.exp(grid)), grid, axis=1)/peak.rp_ohm

    def loss(n):
        model = 1/(1+(1j*omega*peak.tau_s)**n)
        return float(np.sum(np.abs(model-z)**2))

    fit = minimize_scalar(loss, bounds=(.05, 1.), method="bounded")
    n = 1. if loss(1.) <= fit.fun else float(fit.x)
    error = float(np.sqrt(loss(n)/max(np.sum(np.abs(z)**2), np.finfo(float).tiny)))
    note = (f"Approximate R||CPE projection of this finite DRT region; R=integrated Rp, "
            f"tau=marker tau. Q=tau^n/R (S s^n). Relative complex projection error={error:.3%}. "
            "Not an independent circuit fit; overlapping/truncated peaks are model-dependent. "
            "Q and n omitted if projection error exceeds 10%.")
    if not fit.success or error > .1:
        return None, None, note
    return float(peak.tau_s**n/peak.rp_ohm), n, note
