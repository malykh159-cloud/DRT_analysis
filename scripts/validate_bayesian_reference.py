"""Compare identical conditional posterior with pinned, unmodified pyDRTtools HMC.

No GUI/framework dependencies from pyDRTtools are required. Reference sources and
MIT license live in tests/reference_pydrttools. See docs/BAYESIAN_DRT.md for scope.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tests")]
import contextlib
import io
import json
import numpy as np
from dataclasses import replace
from reference_pydrttools.HMC import generate_tmg
from drt_analyzer.data.models import RawSpectrum, ImportInfo
from drt_analyzer.drt.base import AnalysisSettings, BayesianSettings
from drt_analyzer.drt.discretization import build_matrices
from drt_analyzer.drt.tikhonov import make_problem, solve
from drt_analyzer.drt.chain_diagnostics import diagnose
from drt_analyzer.analysis.pipeline import analyze


def validate(output=ROOT/"artifacts"/"bayesian_reference_validation", samples=2000):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    f = np.geomspace(1e3, 1., 25)
    matrices = build_matrices(tuple(f), "Gaussian", "Manual", 6., 2)
    coefficients = .2+10*np.exp(-.5*((matrices.centers-np.log(.005))/.35)**2)
    z = 5+matrices.kernel@coefficients
    raw = RawSpectrum("synthetic_reference.txt", "synthetic", f, z.real, z.imag,
        ImportInfo("synthetic", "tab", ("f", "Re", "Im"), (0, 1, 2), "Im(Z)", 1, "synthetic"))
    settings = AnalysisSettings(method="Bayesian DRT", lambda_method="Manual", lambda_value=.0001,
        validation=False, bayesian=BayesianSettings(warmup=500, samples=samples, chains=2, noise_sigma=.02))
    ours = analyze(raw, settings)
    problem = make_problem(f, z, matrices, False)
    h = problem.a.T@problem.a+settings.lambda_value*(problem.penalty.T@problem.penalty)
    mean = np.linalg.solve(h, problem.a.T@problem.y)
    covariance = settings.bayesian.noise_sigma**2*np.linalg.inv(h)
    covariance = (covariance+covariance.T)/2
    np.linalg.cholesky(covariance)  # reference must not silently repair it
    map_x = solve(problem.a, problem.y, problem.penalty, settings.lambda_value)
    references = []
    for chain in range(2):
        np.random.seed(872+chain)
        initial = map_x+.01*np.sqrt(covariance.diagonal())
        with contextlib.redirect_stdout(io.StringIO()):
            draws = generate_tmg(np.eye(len(mean)), np.zeros(len(mean)), covariance, mean,
                                 initial, cov=True, L=settings.bayesian.warmup+samples+1)
        references.append(draws[:, settings.bayesian.warmup+1:].T)
    ref = np.stack(references)
    assert ref.min() >= -1e-10, "Reference sampler returned infeasible draws."
    ref_gamma = (ref[:, :, 1:]@matrices.basis.T)*problem.impedance_scale
    our_gamma = (ours.uncertainty.coefficient_draws[:, :, 1:]@matrices.basis.T)*problem.impedance_scale
    reference_mean = ref_gamma.mean(axis=(0, 1))
    low, high = np.quantile(ref_gamma, [.025, .975], axis=(0, 1))
    _, our_ess, _ = diagnose(our_gamma)
    ref_rhat, ref_ess, _ = diagnose(ref_gamma)
    mcse = np.sqrt(our_gamma.var(axis=(0, 1))/our_ess+ref_gamma.var(axis=(0, 1))/ref_ess)
    discrepancy = abs(ours.gamma-reference_mean)
    mean_error = float(np.linalg.norm(discrepancy)/np.linalg.norm(reference_mean))
    ci_error = float(np.linalg.norm(np.r_[ours.uncertainty.credible_lower-low,
        ours.uncertainty.credible_upper-high])/np.linalg.norm(np.r_[low, high]))
    rp_ref = np.trapezoid(ref_gamma, matrices.ln_tau, axis=-1)
    rp_ours = np.trapezoid(our_gamma, matrices.ln_tau, axis=-1)
    _, e1, _ = diagnose(rp_ours[:, :, None])
    _, e2, _ = diagnose(rp_ref[:, :, None])
    rp_se = np.sqrt(rp_ours.var()/e1[0]+rp_ref.var()/e2[0])
    tau_ours, tau_ref = matrices.tau[np.argmax(ours.gamma)], matrices.tau[np.argmax(reference_mean)]
    true_gamma = matrices.basis@coefficients
    true_coverage = float(np.mean((true_gamma >= ours.uncertainty.credible_lower) &
                                 (true_gamma <= ours.uncertainty.credible_upper)))
    report = {"reference_commit": (ROOT/"tests/reference_pydrttools/COMMIT.txt").read_text().strip(),
        "comparison": "same joint conditional posterior, same A/R/tau/RBF/epsilon/lambda/sigma; independent HMC code and RNG",
        "posterior_mean_relative_l2": mean_error, "credible_bounds_relative_l2": ci_error,
        "finite_rbf_truth_pointwise_coverage": true_coverage,
        "fraction_mean_differences_within_4_mcse": float(np.mean(discrepancy <= 4*mcse)),
        "rp_ours": ours.rp_total, "rp_reference": float(rp_ref.mean()), "rp_combined_mcse": float(rp_se),
        "peak_tau_ours": float(tau_ours), "peak_tau_reference": float(tau_ref),
        "rhat_max_reference": float(np.max(ref_rhat)), "our_diagnostics": ours.uncertainty.diagnostics,
        "settings": {"warmup": 500, "samples_per_chain": samples, "chains": 2, "lambda": settings.lambda_value, "sigma": .02}}
    (output/"report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert mean_error < .03, report
    assert true_coverage >= .9, report
    assert ci_error < .05, report
    assert report["fraction_mean_differences_within_4_mcse"] >= .95, report
    assert abs(ours.rp_total-rp_ref.mean()) <= 4*rp_se, report
    assert abs(np.log10(tau_ours/tau_ref)) < .08, report
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    validate()
