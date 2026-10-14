"""Lambda criteria verified against Maradesa et al. JES 170 (2023) 030502.

https://doi.org/10.1149/1945-7111/acbca4
GCV family uses the UNCONSTRAINED smoother as a documented surrogate, not a
claimed exact degrees-of-freedom calculation for a positivity-constrained fit.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import lstsq
from ..drt.base import check_cancel
from ..drt.tikhonov import solve


@dataclass(frozen=True)
class LambdaSelection:
    value: float
    method: str
    lambdas: np.ndarray
    scores: np.ndarray
    residual_norms: np.ndarray
    penalty_norms: np.ndarray
    warnings: tuple[str, ...]
    details: dict


def smoother_statistics(a, y, penalty, lam):
    """SVD augmented solve, avoids normal-equation inversion and hidden jitter."""
    n = len(y)
    augmented = np.vstack((a, np.sqrt(lam)*penalty))
    rhs = np.vstack((np.eye(n), np.zeros((penalty.shape[0], n))))
    scale = np.linalg.norm(augmented, axis=0)
    inverse, _, rank, _ = lstsq(augmented/scale, rhs, cond=1e-12)
    if rank < a.shape[1]:
        raise ValueError("Singular smoother matrix.")
    h = a @ (inverse/scale[:, None])
    residual = y-h@y
    return float(residual@residual), float(np.trace(h)), float(np.sum(h*h))


def gcv_score(sse, trace_h, trace_hth, n, method):
    rho = 1.3 if n < 50 else 2.
    xi = 0.2 if n < 100 else 0.3
    denominator = 1 - (rho if method == "mGCV" else 1.)*trace_h/n
    # Restrict to the positive denominator branch, as required for a stable
    # modified score; squaring a negative denominator creates a spurious minimum.
    if denominator <= 1e-10:
        return np.inf
    score = (sse/n)/denominator**2
    if method == "rGCV":
        score *= xi+(1-xi)*trace_hth/n
    return float(score)


def lcurve_curvature(lambdas, residuals, penalties):
    t = np.log(lambdas)
    x = np.log(np.maximum(residuals, 1e-300))
    y = np.log(np.maximum(penalties, 1e-300))
    dx, dy = np.gradient(x, t), np.gradient(y, t)
    ddx, ddy = np.gradient(dx, t), np.gradient(dy, t)
    curvature = (dx*ddy-dy*ddx)/np.maximum((dx*dx+dy*dy)**1.5, 1e-30)
    curvature[:2] = curvature[-2:] = -np.inf
    return curvature


def kfold_score(problem, lam, settings, cancel=None):
    n = problem.n_frequency
    folds = np.array_split(np.random.default_rng(settings.random_seed).permutation(n), settings.kfold_splits)
    total = 0.
    count = 0
    for held in folds:
        check_cancel(cancel)
        test = np.r_[held, held+n]  # always hold out both components of one frequency
        train = np.ones(2*n, bool)
        train[test] = False
        x = solve(problem.a[train], problem.y[train], problem.penalty, lam)
        r = problem.a[test]@x-problem.y[test]
        total += float(r@r)
        count += len(test)
    return total/count


def select_lambda(problem, settings, cancel=None):
    method = settings.lambda_method
    if method == "Manual":
        return LambdaSelection(settings.lambda_value, method, np.array([settings.lambda_value]),
                               np.array([]), np.array([]), np.array([]), (), {})
    lambdas = np.logspace(settings.lambda_min_exp, settings.lambda_max_exp, settings.lambda_count)
    scores, residuals, penalties, warnings = [], [], [], []
    for lam in lambdas:
        check_cancel(cancel)
        try:
            if method in {"GCV", "mGCV", "rGCV"}:
                sse, tr, tr2 = smoother_statistics(problem.a, problem.y, problem.penalty, lam)
                score = gcv_score(sse, tr, tr2, len(problem.y), method)
            elif method == "k-fold":
                score = kfold_score(problem, lam, settings, cancel)
            else:
                score = 0.
            if method == "L-curve":
                x = solve(problem.a, problem.y, problem.penalty, lam)
                residuals.append(np.linalg.norm(problem.a@x-problem.y))
                penalties.append(np.linalg.norm(problem.penalty@x))
            scores.append(score)
        except ValueError:
            scores.append(np.inf)
            if method == "L-curve":
                residuals.append(np.nan)
                penalties.append(np.nan)
    scores = np.asarray(scores)
    if method == "L-curve":
        if not np.isfinite(residuals).all() or not np.isfinite(penalties).all():
            raise ValueError("L-curve contains failed fits. Change scan limits or RBF shape.")
        scores = -lcurve_curvature(lambdas, residuals, penalties)
        if not np.any(np.isfinite(scores) & (scores < 0)):
            raise ValueError("No positive L-curve corner found in the requested range.")
    if not np.isfinite(scores).any():
        raise ValueError("Lambda selection failed throughout the scan. Change range or RBF shape.")
    index = int(np.argmin(scores))
    if index in (0, len(lambdas)-1) or (method == "L-curve" and index in (2, len(lambdas)-3)):
        warnings.append("Selected lambda is near the scan boundary; inspect Lambda Scan and widen limits.")
    if method in {"GCV", "mGCV", "rGCV"}:
        warnings.append("GCV-family selection uses an unconstrained linear smoother; final DRT is nonnegative.")
    details = {"surrogate": method in {"GCV", "mGCV", "rGCV"},
               "rho_mgcv": 1.3 if len(problem.y) < 50 else 2.,
               "xi_rgcv": 0.2 if len(problem.y) < 100 else 0.3,
               "kfold_splits": settings.kfold_splits, "random_seed": settings.random_seed,
               "paired_complex_folds": True, "scan_index": index}
    return LambdaSelection(float(lambdas[index]), method, lambdas, scores,
                           np.asarray(residuals), np.asarray(penalties), tuple(warnings), details)
