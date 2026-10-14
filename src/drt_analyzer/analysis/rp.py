import numpy as np


def integrate_rp(ln_tau, gamma):
    """Rp = integral gamma(tau) d ln(tau), in ohms, not d log10(tau)."""
    return float(np.trapezoid(gamma, ln_tau))
