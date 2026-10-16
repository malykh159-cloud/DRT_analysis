"""Conditional Bayesian RBF DRT: Gaussian likelihood + smoothing prior, x >= 0.

Precision = (A.T A + lambda R.T R)/sigma**2, joint series Rs/L and RBF weights.
Noise and lambda are plug-in/fixed hyperparameters, not hierarchical inference.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import cholesky, cho_solve
from ..data.models import readonly
from .base import check_cancel
from .truncated_hmc import sample_chain
from .chain_diagnostics import diagnose


@dataclass(frozen=True)
class BayesianResult:
    credible_lower: np.ndarray
    credible_upper: np.ndarray
    coefficient_draws: np.ndarray  # chain, retained draw, normalized coefficient
    diagnostics: dict
    noise_sigma: float
    credible_interval: float
    warnings: tuple

    def __post_init__(self):
        for name in ("credible_lower", "credible_upper", "coefficient_draws"):
            object.__setattr__(self, name, readonly(getattr(self, name)))


def gaussian_posterior(problem, lam, map_x, settings):
    h = problem.a.T@problem.a+lam*(problem.penalty.T@problem.penalty)
    scale = np.sqrt(np.diag(h))
    try:
        factor = cholesky(h/scale[:, None]/scale[None, :], lower=True)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Bayesian precision is not positive definite; increase lambda or change RBF shape. No hidden jitter applied.") from exc
    mean = cho_solve((factor, True), (problem.a.T@problem.y)/scale)/scale
    sigma = settings.noise_sigma or max(settings.noise_floor, float(np.std(problem.a@map_x-problem.y)))
    covariance = sigma**2*cho_solve((factor, True), np.eye(len(scale)))/scale[:, None]/scale[None, :]
    return mean, (covariance+covariance.T)/2, sigma


def posterior(problem, matrices, lam, map_x, settings, cancel=None, progress=None):
    iterations = settings.warmup+settings.samples
    total_units = settings.chains*iterations+1
    if progress:
        progress(0, total_units, "Preparing posterior")
    mean, covariance, sigma = gaussian_posterior(problem, lam, map_x, settings)
    chains, reports = [], []
    children = np.random.SeedSequence(settings.seed).spawn(settings.chains)
    for chain, child in enumerate(children):
        check_cancel(cancel)
        rng = np.random.default_rng(child)
        initial = map_x+np.sqrt(np.diag(covariance))*rng.uniform(.01, .1, len(mean))
        def report(done, total):
            if progress:
                phase = "Warm-up" if done <= settings.warmup else "Sampling"
                phase_done = done if done <= settings.warmup else done-settings.warmup
                phase_total = settings.warmup if done <= settings.warmup else settings.samples
                progress(chain*iterations+done, total_units,
                         f"Chain {chain+1}/{settings.chains} · {phase} {phase_done}/{phase_total}")
        draws, info = sample_chain(mean, covariance, initial, settings, rng, cancel, report)
        chains.append(draws)
        reports.append(info)
    draws = np.stack(chains)
    check_cancel(cancel)
    if progress:
        progress(total_units-1, total_units, "Diagnostics / credible interval")
    rhat, bulk, tail = diagnose(draws)
    r_values = [] if rhat is None else [rhat]
    ess_bulk, ess_tail = [bulk], [tail]
    offset = 2 if problem.has_inductance else 1
    lower, upper = [], []
    alpha = (1-settings.credible_interval/100)/2
    for start in range(0, len(matrices.tau), 64):
        check_cancel(cancel)
        gamma_draws = (draws[:, :, offset:]@matrices.basis[start:start+64].T)*problem.impedance_scale
        rh, eb, et = diagnose(gamma_draws)
        if rh is not None:
            r_values.append(rh)
        ess_bulk.append(eb)
        ess_tail.append(et)
        quantiles = np.quantile(gamma_draws, [alpha, 1-alpha], axis=(0, 1))
        lower.extend(quantiles[0])
        upper.extend(quantiles[1])
    max_rhat = float(np.nanmax(np.concatenate(r_values))) if r_values else None
    min_bulk = float(np.nanmin(np.concatenate(ess_bulk)))
    min_tail = float(np.nanmin(np.concatenate(ess_tail)))
    warnings = ["Bayesian intervals are pointwise and conditional on selected lambda, basis and plug-in/fixed noise; they do not include hyperparameter or model uncertainty."]
    if settings.noise_sigma == 0:
        warnings.append(f"Bayesian noise: residual plug-in sigma={sigma:.6g} in modulus-weighted normalized coordinates (floor={settings.noise_floor:g}).")
    if max_rhat is None:
        warnings.append("Bayesian convergence: one chain; between-chain R-hat cannot be assessed.")
    if max_rhat is not None and (not np.isfinite(max_rhat) or max_rhat > 1.01):
        warnings.append(f"Bayesian sampler convergence warning: rank/folded split R-hat max={max_rhat:.4g} > 1.01; increase warm-up/samples and inspect sensitivity.")
    if min_bulk < 400 or min_tail < 400:
        warnings.append(f"Bayesian sampler convergence warning: minimum bulk ESS={min_bulk:.1f}, tail ESS={min_tail:.1f}; recommended minimum 400.")
    problematic = sum(r["problematic_transitions"] for r in reports)
    if problematic:
        warnings.append(f"Bayesian numerical warning: {problematic} problematic transitions retained the preceding state; inspect sampler settings.")
    diagnostics = {"sampler": "Exact reflecting Gaussian HMC (Pakman-Paninski)",
                   "rhat_max": max_rhat, "ess_bulk_min": min_bulk, "ess_tail_min": min_tail,
                   "chains": reports, "seed_spawn_keys": [list(c.spawn_key) for c in children],
                   "problematic_transitions": problematic, "divergences": None,
                   "divergences_note": "Exact dynamics: divergences not applicable; numerical failures counted separately.",
                   "convergence_ok": max_rhat is not None and max_rhat <= 1.01 and min_bulk >= 400 and min_tail >= 400 and not problematic}
    result = BayesianResult(np.array(lower), np.array(upper), draws, diagnostics, sigma,
                            settings.credible_interval, tuple(warnings))
    if progress:
        progress(total_units, total_units, "Posterior complete")
    return draws.mean(axis=(0, 1)), result


class BayesianEngine:
    available = True

    def analyze(self, raw, settings, cancel=None):
        from ..analysis.pipeline import analyze
        from dataclasses import replace
        return analyze(raw, replace(settings, method="Bayesian DRT"), cancel)
