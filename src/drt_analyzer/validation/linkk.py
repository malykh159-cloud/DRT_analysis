"""Independent complex weighted Lin-KK regression with the Schonleber mu rule.

Reference: https://doi.org/10.1016/j.electacta.2014.01.034
The RMS tolerance is a user-visible diagnostic heuristic, not a hypothesis test.
Compatibility does not prove linearity/stationarity from a single spectrum.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import lstsq
from .residuals import metrics
from ..drt.base import check_cancel


@dataclass(frozen=True)
class KKResult:
    status: str
    n_elements: int
    mu: float
    mu_reached: bool
    reconstructed: np.ndarray
    residuals: np.ndarray
    relative_rms: float
    warnings: tuple[str, ...]


def lin_kk(frequency, impedance, settings, cancel=None):
    w = 2*np.pi*frequency
    zscale = np.median(np.abs(impedance))
    modulus = np.abs(impedance)/zscale
    reached = False
    max_m = min(settings.kk_max_elements, max(3, len(w)-3))
    # Explicit resolution guard: a very coarse dictionary may cross mu while
    # still underfitting narrow RC peaks. This is a declared application heuristic,
    # not part of the original Schonleber mu criterion or a proof of validity.
    min_m = min(max_m, max(3, int(np.ceil(settings.kk_min_per_decade*np.log10(w.max()/w.min())))))
    for m in range(min_m, max_m+1):
        check_cancel(cancel)
        tau = np.geomspace(1/w.max(), 1/w.min(), m)
        rc = 1/(1+1j*w[:, None]*tau[None, :])
        parts = [np.ones(len(w)), *rc.T, 1j*w/w.max()]
        if settings.kk_add_capacitance:
            parts.append(-1j*w.min()/w)
        c = np.column_stack(parts)
        a = np.vstack((c.real/modulus[:, None], c.imag/modulus[:, None]))
        y = np.concatenate((impedance.real/zscale/modulus, impedance.imag/zscale/modulus))
        scales = np.linalg.norm(a, axis=0)
        solution, _, rank, _ = lstsq(a/scales, y, cond=1e-12)
        solution /= scales
        positive = np.sum(np.clip(solution[1:m+1], 0, None))
        negative = -np.sum(np.clip(solution[1:m+1], None, 0))
        mu = float(1-negative/positive) if positive > 1e-15 else -1.
        fitted = c @ solution*zscale
        if mu <= settings.kk_mu:
            reached = True
            break
    residuals, quality = metrics(impedance, fitted)
    warnings = []
    if not reached:
        warnings.append("Lin-KK mu cutoff not reached within the model-order limit; diagnostic is inconclusive.")
    if rank < a.shape[1]:
        warnings.append("Lin-KK design is rank deficient; diagnostic is inconclusive.")
    if quality["relative_rms"] > settings.kk_tolerance:
        status = "Review"
        warnings.append("Data may violate assumptions required for reliable DRT analysis.")
    elif not reached or rank < a.shape[1]:
        status = "Inconclusive"
    else:
        status = "Compatible"
    return KKResult(status, m, mu, reached, fitted, residuals, quality["relative_rms"], tuple(warnings))
