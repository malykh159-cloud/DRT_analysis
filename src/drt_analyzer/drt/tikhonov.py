"""Nonnegative Tikhonov solver, independent of the GUI and lambda selectors."""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import lstsq
from scipy.optimize import nnls


@dataclass
class LinearProblem:
    a: np.ndarray
    y: np.ndarray
    penalty: np.ndarray
    impedance_matrix: np.ndarray
    n_frequency: int
    has_inductance: bool
    inductance_scale: float
    impedance_scale: float


def make_problem(frequency, impedance, matrices, include_inductance):
    # Unknowns are normalized by median |Z|. A series-L column is expressed as
    # j*w/wmax, avoiding microscopic coefficients and ill-conditioned columns.
    zscale = float(np.median(np.abs(impedance)))
    w = 2*np.pi*frequency
    columns = [np.ones(len(w), complex)]
    if include_inductance:
        columns.append(1j*w/w.max())
    columns.extend(matrices.kernel.T)
    c = np.column_stack(columns)
    # Relative modulus weighting, with a floor only in the weight, not the data.
    modulus = np.maximum(np.abs(impedance)/zscale, 1e-12)
    a = np.vstack((c.real/modulus[:, None], c.imag/modulus[:, None]))
    y = np.concatenate((impedance.real/zscale/modulus, impedance.imag/zscale/modulus))
    offset = 2 if include_inductance else 1
    penalty = np.pad(matrices.penalty, ((0, 0), (offset, 0)))
    return LinearProblem(a, y, penalty, c, len(w), include_inductance, 1/w.max(), zscale)


def solve(a, y, penalty, lambda_value, constrained=True):
    if not np.isfinite(lambda_value) or lambda_value <= 0:
        raise ValueError("Lambda must be finite and > 0.")
    # ||Ax-y||^2 + lambda ||Rx||^2; lambda is not squared again.
    augmented = np.vstack((a, np.sqrt(lambda_value)*penalty))
    rhs = np.concatenate((y, np.zeros(penalty.shape[0])))
    scale = np.linalg.norm(augmented, axis=0)
    if np.any(scale < 1e-15):
        raise ValueError("Unidentifiable zero matrix column.")
    if constrained:
        try:
            x, _ = nnls(augmented/scale, rhs, maxiter=50*augmented.shape[1])
        except RuntimeError as exc:
            raise ValueError("Nonnegative optimization did not converge; try larger lambda.") from exc
    else:
        x, _, rank, _ = lstsq(augmented/scale, rhs, cond=1e-12, lapack_driver="gelsd")
        if rank < augmented.shape[1]:
            raise ValueError("Singular regularized matrix; increase lambda or change RBF shape.")
    x = x/scale
    if not np.isfinite(x).all():
        raise ValueError("Optimization returned nonfinite coefficients.")
    return x
