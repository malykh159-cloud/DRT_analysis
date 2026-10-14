from dataclasses import replace
import numpy as np
from ..drt.base import check_cancel
from ..drt.discretization import build_matrices
from ..drt.tikhonov import make_problem, solve
from ..data.preprocessing import prepare
from ..validation.inductance import detect_inductance
from ..validation.linkk import lin_kk
from ..validation.residuals import metrics
from ..regularization.selection import select_lambda
from ..state.analysis_variant import AnalysisVariant, identity
from .peaks import detect_peaks
from .rp import integrate_rp


def auto_settings():
    from ..drt.base import AnalysisSettings
    return AnalysisSettings(mode="Auto", lambda_method="rGCV", derivative_order=2,
                            rbf="Gaussian", shape_mode="Auto", validation=True)


def analyze(raw, settings, cancel=None):
    settings.validate()
    check_cancel(cancel)
    f, z, preprocessing = prepare(raw)
    induction = detect_inductance(f, z)
    preprocessing["inductance"] = induction
    kk = lin_kk(f, z, settings, cancel) if settings.validation else None
    check_cancel(cancel)
    matrices = build_matrices(tuple(f), settings.rbf, settings.shape_mode, settings.shape_value,
                              settings.derivative_order)
    problem = make_problem(f, z, matrices, induction["detected"])
    selection = select_lambda(problem, settings, cancel)
    check_cancel(cancel)
    x = solve(problem.a, problem.y, problem.penalty, selection.value)
    offset = 2 if problem.has_inductance else 1
    gamma = matrices.basis @ x[offset:]*problem.impedance_scale
    reconstructed = problem.impedance_matrix@x*problem.impedance_scale
    residuals, quality = metrics(z, reconstructed)
    rp = integrate_rp(matrices.ln_tau, gamma)
    peaks, peak_warnings = detect_peaks(matrices.tau, gamma, settings)
    warnings = list(raw.warnings)+induction["warnings"]+list(selection.warnings)+list(peak_warnings)
    if kk:
        warnings.extend(kk.warnings)
    if quality["relative_rms"] > 0.02:
        warnings.append("Reconstruction relative RMS exceeds 2%; inspect residuals and model adequacy.")
    preprocessing["tau_grid"] = {
        "min_s": float(matrices.tau[0]), "max_s": float(matrices.tau[-1]),
        "n_centers": len(matrices.centers), "n_quadrature": len(matrices.tau),
        "strategy": "finite measured window; 12 centers/decade, clipped 36–144; trapezoid quadrature"}
    preprocessing["weighting"] = "modulus: 1/|Z|; normalized unknowns by median |Z|"
    preprocessing["objective"] = "||W(Ax-z)||^2 + lambda*||R*x||^2; normalized coefficients"
    return AnalysisVariant(*identity(), settings, f, z, matrices.tau, gamma, reconstructed, residuals,
                           selection.value, matrices.epsilon, float(x[0]*problem.impedance_scale),
                           float(x[1]*problem.impedance_scale*problem.inductance_scale) if problem.has_inductance else 0.,
                           rp, peaks, quality, preprocessing, kk, selection, tuple(dict.fromkeys(warnings)),
                           float(np.linalg.norm(problem.penalty@x)))


def lambda_scan(raw, settings, cancel=None, progress=None):
    """Full cached variants: moving the GUI slider never recomputes a fit."""
    settings.validate()
    variants = []
    # Diagnostic is invariant to lambda and is performed once.
    diagnostic = None
    for i, lam in enumerate(np.logspace(settings.lambda_min_exp, settings.lambda_max_exp, settings.lambda_count)):
        check_cancel(cancel)
        s = replace(settings, mode="Manual", lambda_method="Manual", lambda_value=float(lam),
                    validation=settings.validation and i == 0)
        v = analyze(raw, s, cancel)
        if i == 0:
            diagnostic = v.kk
        if diagnostic is not None and i:
            v = replace(v, kk=diagnostic, settings=replace(s, validation=settings.validation),
                        warnings=tuple(dict.fromkeys(v.warnings+diagnostic.warnings)))
        variants.append(v)
        if progress:
            progress(i+1, settings.lambda_count)
    return variants
