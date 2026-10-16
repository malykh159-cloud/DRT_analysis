from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from scipy.stats import halfnorm
from conftest import synthetic
from drt_analyzer.analysis.pipeline import analyze, lambda_scan
from drt_analyzer.drt.base import AnalysisSettings, BayesianSettings, Cancelled
from drt_analyzer.drt.truncated_hmc import sample_chain
from drt_analyzer.drt.chain_diagnostics import diagnose


def settings(**kwargs):
    return AnalysisSettings(method="Bayesian DRT", lambda_method="Manual", lambda_value=1e-3,
                            validation=False, bayesian=BayesianSettings(warmup=80, samples=200, chains=2), **kwargs)


def test_tikhonov_unchanged_against_preimplementation_baseline(rc):
    baseline = np.load(Path(__file__).parent/"fixtures"/"tikhonov_before_bayesian.npz")
    for i, kwargs in enumerate(({}, dict(rbf="C6 Matern", shape_mode="Auto"),
                                dict(derivative_order=1, lambda_method="Manual", lambda_value=1e-5))):
        v = analyze(rc, AnalysisSettings(validation=False, **kwargs))
        for name in ("gamma", "reconstructed", "residuals", "tau"):
            np.testing.assert_allclose(getattr(v, name), baseline[f"{i}_{name}"], rtol=1e-10, atol=1e-11)
        np.testing.assert_allclose([v.lambda_value, v.rp_total, v.rs_ohm, v.shape_value], baseline[f"{i}_scalars"], rtol=1e-10)


def test_reflecting_sampler_matches_analytic_half_normal():
    s = BayesianSettings(warmup=200, samples=50000, chains=1)
    draws, info = sample_chain(np.zeros(2), np.eye(2), np.ones(2), s, np.random.default_rng(42))
    assert np.all(draws >= 0) and info["acceptance_rate"] == 1
    np.testing.assert_allclose(draws.mean(axis=0), halfnorm.mean(), atol=.025)
    np.testing.assert_allclose(np.quantile(draws, [.025, .975], axis=0),
                               np.broadcast_to(halfnorm.ppf([.025, .975])[:, None], (2, 2)), atol=.08)


@pytest.fixture(scope="module")
def single():
    raw = synthetic(f=np.geomspace(1e3, .1, 31))
    return raw, analyze(raw, settings())


def test_single_rc_mean_peak_rp_and_credible_region(single):
    raw, v = single
    assert abs(v.rp_total/80-1) < .08
    assert len(v.peaks) == 1 and abs(np.log10(v.peaks[0].tau_s/.01)) < .1
    u = v.uncertainty
    assert np.all(u.credible_lower >= 0) and np.all(u.credible_upper >= u.credible_lower)
    # An ideal RC has a delta DRT, not a finite peak amplitude. Its location must
    # be in the resolved credible peak region; pointwise delta coverage is undefined.
    i = np.argmin(abs(np.log(v.tau/.01)))
    assert u.credible_lower[i] > 0 and u.credible_upper[i] >= v.gamma[i]
    assert v.quality["relative_rms"] < .06
    assert u.coefficient_draws.shape[:2] == (2, 200)
    assert u.diagnostics["rhat_max"] is not None
    assert u.diagnostics["ess_bulk_min"] > 0
    with pytest.raises(ValueError):
        u.credible_lower.setflags(write=True)


def test_two_separated_rcs():
    raw = synthetic(f=np.geomspace(1e4, .01, 41), branches=((30., .001), (70., .1)))
    v = analyze(raw, settings())
    assert len(v.peaks) == 2
    assert abs(v.rp_total/100-1) < .08
    np.testing.assert_allclose(np.log10([p.tau_s for p in v.peaks]), [-3, -1], atol=.12)
    assert abs(sum(p.rp_ohm for p in v.peaks)-v.rp_total) < 1e-8


def test_seed_reproducibility_and_independence(single):
    raw, a = single
    b = analyze(raw, settings())
    np.testing.assert_array_equal(a.gamma, b.gamma)
    np.testing.assert_array_equal(a.uncertainty.coefficient_draws, b.uncertainty.coefficient_draws)
    assert not np.array_equal(b.uncertainty.coefficient_draws[0], b.uncertainty.coefficient_draws[1])
    c = analyze(raw, replace(settings(), bayesian=replace(settings().bayesian, seed=93)))
    assert not np.array_equal(a.gamma, c.gamma)
    # Same target estimates, judged against actual credible widths, not identity.
    width = a.uncertainty.credible_upper-a.uncertainty.credible_lower
    assert np.quantile(abs(a.gamma-c.gamma)/(width+1e-12), .95) < .5


def test_controlled_noise_widens_interval():
    s = settings()
    smooth = synthetic(f=np.geomspace(1e3, .1, 31))
    noisy = synthetic(f=smooth.frequency, noise=.04)
    a, b = analyze(smooth, s), analyze(noisy, s)
    assert b.uncertainty.noise_sigma > a.uncertainty.noise_sigma
    area = lambda v: np.trapezoid(v.uncertainty.credible_upper-v.uncertainty.credible_lower, np.log(v.tau))
    assert area(b) > area(a)


def test_chain_diagnostics_identify_bad_mixing():
    rng = np.random.default_rng(7)
    draws = rng.normal(size=(4, 1000, 3))
    rhat, bulk, tail = diagnose(draws)
    assert np.max(rhat) < 1.01 and np.min(bulk) > 1000 and np.min(tail) > 1000
    draws[0] += 3
    rhat, bulk, _ = diagnose(draws)
    assert np.min(rhat) > 1.1 and np.max(bulk) < 100


def test_cancel_within_current_chain():
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        return calls > 30
    with pytest.raises(Cancelled):
        analyze(synthetic(f=np.geomspace(1e3, .1, 31)), settings(), cancel)
    assert calls == 31


def test_scan_progress_inside_first_lambda():
    raw = synthetic(f=np.geomspace(1e3, .1, 21))
    s = replace(settings(), lambda_min_exp=-3, lambda_max_exp=-2, lambda_count=7,
                bayesian=BayesianSettings(warmup=3, samples=20, chains=1))
    completed, events = [], []
    variants = lambda_scan(raw, s, progress=lambda done, total: completed.append(done),
        sampling_progress=lambda done, total, message: events.append((len(completed), done, total, message)))
    assert len(variants) == 7 and completed == list(range(1, 8))
    assert any(n == 0 and done > 0 and "λ 1/7" in message and "Chain 1/1" in message
               for n, done, total, message in events)
    assert any("Diagnostics / credible interval" in message for _, _, _, message in events)
    assert [done for _, done, _, _ in events] == sorted(done for _, done, _, _ in events)
    assert len({total for _, _, total, _ in events}) == 1
    assert events[-1][1] == events[-1][2]
    for v in variants:
        assert v.settings.method == "Bayesian DRT" and v.uncertainty is not None
    np.testing.assert_allclose([v.lambda_value for v in variants], np.logspace(-3, -2, 7))


@pytest.mark.parametrize("method", ["Manual", "GCV", "mGCV", "rGCV", "L-curve", "k-fold"])
def test_lambda_selectors_retain_same_map_choice(method):
    raw = synthetic(f=np.geomspace(1e3, .1, 21))
    # End just after posterior entry: prove selectors operate unchanged without
    # paying for 6 full MCMC runs, especially at tiny selected lambda values.
    from drt_analyzer.drt import bayesian
    from unittest.mock import patch
    s = AnalysisSettings(lambda_method=method, lambda_count=7, validation=False)
    original = analyze(raw, s)
    captured = []
    def capture(problem, matrices, lam, x, *args):
        captured.append((lam, x))
        raise Cancelled()
    with patch.object(bayesian, "posterior", capture), pytest.raises(Cancelled):
        analyze(raw, replace(s, method="Bayesian DRT"))
    assert captured[0][0] == original.lambda_value
