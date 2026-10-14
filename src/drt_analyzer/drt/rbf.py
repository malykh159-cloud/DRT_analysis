"""Original implementation of RBF definitions documented by Wan et al. (2015).

Formula reference: https://github.com/ciuccislab/pyDRTtools/blob/master/pyDRTtools/basics.py
No source code is copied. x means ln(tau) - ln(tau_center).
"""
import numpy as np
from numpy.polynomial import polynomial as poly
from scipy.optimize import brentq

RBF_NAMES = ("Gaussian", "C2 Matern", "C4 Matern", "C6 Matern")
_POLYS = {"C2 Matern": [1., 1.], "C4 Matern": [1., 1., 1/3],
          "C6 Matern": [1., 1., 2/5, 1/15]}


def evaluate(x, epsilon, kind="Gaussian", derivative=0):
    x = np.asarray(x)
    if derivative not in (0, 1, 2) or epsilon <= 0:
        raise ValueError("Invalid RBF derivative/shape.")
    r = epsilon * np.abs(x)
    if kind == "Gaussian":
        phi = np.exp(-r*r)
        if derivative == 0:
            return phi
        if derivative == 1:
            return -2 * epsilon**2 * x * phi
        return (4 * epsilon**4 * x*x - 2 * epsilon**2) * phi
    if kind not in _POLYS:
        raise ValueError(f"Unknown RBF: {kind}")
    p = np.asarray(_POLYS[kind])
    for _ in range(derivative):
        p = poly.polysub(poly.polyder(p), p)
    value = np.exp(-r) * poly.polyval(r, p) * epsilon**derivative
    return value * np.sign(x) if derivative == 1 else value


def auto_shape(center_spacing, kind):
    """FWHM = one center spacing. epsilon is per unit natural log tau."""
    half_width = brentq(lambda r: float(evaluate(r, 1., kind)) - 0.5, 1e-9, 30.)
    return 2 * half_width / center_spacing
