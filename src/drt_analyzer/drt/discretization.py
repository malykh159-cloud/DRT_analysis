from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from .rbf import evaluate, auto_shape
from ..data.models import readonly


def tau_grid(frequency):
    """Finite measured window, 12 centers per decade (36–144 centers)."""
    lo, hi = 1 / (2*np.pi*np.max(frequency)), 1 / (2*np.pi*np.min(frequency))
    count = int(np.clip(np.ceil(12*np.log10(hi/lo)) + 1, 36, 144))
    return np.geomspace(lo, hi, count)


def trapezoid_weights(x):
    x = np.asarray(x)
    w = np.empty_like(x)
    w[0], w[-1] = (x[1]-x[0])/2, (x[-1]-x[-2])/2
    w[1:-1] = (x[2:]-x[:-2])/2
    return w


@dataclass(frozen=True)
class Discretization:
    tau: np.ndarray
    ln_tau: np.ndarray
    weights: np.ndarray
    centers: np.ndarray
    basis: np.ndarray
    kernel: np.ndarray
    penalty: np.ndarray
    epsilon: float


@lru_cache(maxsize=16)
def build_matrices(frequency_tuple, rbf, shape_mode, shape_value, derivative_order):
    frequency = np.asarray(frequency_tuple)
    centers = np.log(tau_grid(frequency))
    epsilon = auto_shape(centers[1]-centers[0], rbf) if shape_mode == "Auto" else shape_value
    # At least 16 quadrature samples across the Gaussian FWHM, even in Manual.
    # Reject an unreasonable request rather than silently underintegrating it.
    spacing = min((centers[1]-centers[0])/12, 0.1/epsilon)
    n = max(721, int(np.ceil((centers[-1]-centers[0])/spacing)) + 1)
    if n > 30001:
        raise ValueError("RBF shape too narrow for reliable quadrature in this frequency window.")
    ln_tau = np.linspace(centers[0], centers[-1], n)
    weights = trapezoid_weights(ln_tau)
    delta = ln_tau[:, None]-centers[None, :]
    basis = evaluate(delta, epsilon, rbf)
    deriv = evaluate(delta, epsilon, rbf, derivative_order)
    tau = np.exp(ln_tau)
    response = 1 / (1 + 2j*np.pi*frequency[:, None]*tau[None, :])
    kernel = (response * weights) @ basis
    penalty = np.sqrt(weights)[:, None] * deriv
    return Discretization(*(readonly(a, complex if np.iscomplexobj(a) else float)
                            for a in (tau, ln_tau, weights, centers, basis, kernel, penalty)), epsilon)
