from dataclasses import replace
import numpy as np
import pytest
from conftest import synthetic
from drt_analyzer.drt.base import AnalysisSettings, Cancelled
from drt_analyzer.analysis.pipeline import analyze, lambda_scan
from drt_analyzer.analysis.rp import integrate_rp
from drt_analyzer.drt.rbf import RBF_NAMES, evaluate
from drt_analyzer.drt.reconstruction import reconstruct
from drt_analyzer.validation.inductance import detect_inductance
from drt_analyzer.validation.linkk import lin_kk


MANUAL = AnalysisSettings(lambda_method="Manual", lambda_value=1e-6, validation=False, shape_mode="Auto")


def test_single_rc_known_peak_and_rp(rc):
    v = analyze(rc, MANUAL)
    assert abs(v.rp_total/80.-1) < 0.02
    assert len(v.peaks) == 1
    assert abs(np.log10(v.peaks[0].tau_s/0.01)) < 0.08
    assert v.quality["relative_rms"] < 0.01
    assert np.all(v.gamma >= 0)
    assert abs(v.rs_ohm-5) < 0.2


def test_two_resolved_rc():
    raw = synthetic(branches=((30., 1e-4), (70., .1)))
    v = analyze(raw, MANUAL)
    assert len(v.peaks) == 2
    assert abs(v.rp_total/100.-1) < 0.02
    np.testing.assert_allclose([p.tau_s for p in v.peaks], [1e-4, .1], rtol=.2)
    assert abs(sum(p.rp_ohm for p in v.peaks)-v.rp_total) < 1e-8
    assert v.quality["relative_rms"] < .01


def test_reconstruction_integral(rc):
    v = analyze(rc, MANUAL)
    from drt_analyzer.drt.discretization import trapezoid_weights
    z = reconstruct(v.frequency, v.tau, v.gamma, trapezoid_weights(np.log(v.tau)), v.rs_ohm, v.inductance_h)
    np.testing.assert_allclose(z, v.reconstructed, rtol=1e-10, atol=1e-10)


def test_ln_normalization():
    t = np.linspace(-7, 3, 2001)
    gamma = np.full_like(t, 2.)
    assert abs(integrate_rp(t, gamma)-20.) < 1e-10


@pytest.mark.parametrize("rbf", RBF_NAMES)
@pytest.mark.parametrize("order", [0, 1, 2])
def test_rbf_and_derivatives(rbf, order):
    x = np.array([-.7, -.2, .2, .7])
    h = 1e-5
    if order == 0:
        assert evaluate(0, 1.3, rbf) == pytest.approx(1.)
        assert np.all(evaluate(x, 1.3, rbf) > 0)
    else:
        numerical = (evaluate(x+h, 1.3, rbf, order-1)-evaluate(x-h, 1.3, rbf, order-1))/(2*h)
        np.testing.assert_allclose(evaluate(x, 1.3, rbf, order), numerical, rtol=1e-6, atol=1e-7)


@pytest.mark.parametrize("rbf", RBF_NAMES)
@pytest.mark.parametrize("order", [0, 1, 2])
def test_all_basis_orders(rc, rbf, order):
    v = analyze(rc, replace(MANUAL, rbf=rbf, derivative_order=order))
    assert abs(v.rp_total/80.-1) < .04
    assert v.quality["relative_rms"] < .02


@pytest.mark.parametrize("method", ["GCV", "mGCV", "rGCV", "L-curve", "k-fold"])
def test_lambda_methods_noise(method):
    raw = synthetic(f=np.geomspace(1e4, .01, 45), noise=.002)
    settings = replace(MANUAL, lambda_method=method, lambda_count=15)
    v = analyze(raw, settings)
    assert 1e-8 <= v.lambda_value <= 1e2
    assert abs(v.rp_total/80.-1) < .06
    assert v.quality["relative_rms"] < .03


def test_hf_inductance():
    raw = synthetic(inductance=2e-5)
    detection = detect_inductance(raw.frequency, raw.impedance)
    assert detection["detected"]
    v = analyze(raw, MANUAL)
    assert abs(v.inductance_h/2e-5-1) < .02
    assert v.preprocessing["points_used"] == len(raw.frequency)
    assert abs(v.rp_total/80.-1) < .02


def test_linkk_diagnostic():
    raw = synthetic(branches=((30., 1e-4), (70., .1)), inductance=1e-5)
    kk = lin_kk(raw.frequency, raw.impedance, AnalysisSettings())
    assert kk.relative_rms < .01
    assert kk.status in {"Compatible", "Inconclusive"}
    bad_z = raw.impedance.copy()
    bad_z[20] += 50j
    bad = lin_kk(raw.frequency, bad_z, AnalysisSettings())
    assert bad.status == "Review"
    assert bad.relative_rms > kk.relative_rms


def test_cancel(rc):
    with pytest.raises(Cancelled):
        analyze(rc, MANUAL, cancel=lambda: True)


def test_scan(rc):
    variants = lambda_scan(rc, replace(MANUAL, lambda_count=7, validation=True))
    assert len(variants) == 7
    assert all(v.kk is variants[0].kk for v in variants)
    assert all(v.settings.validation for v in variants)
    assert variants[0].penalty_norm > variants[-1].penalty_norm
