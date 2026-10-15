from dataclasses import replace
import numpy as np
import pytest
from drt_analyzer.analysis.pipeline import analyze, lambda_scan, auto_settings
from drt_analyzer.data.preprocessing import prepare
from drt_analyzer.drt.base import AnalysisSettings
from drt_analyzer.export.settings import metadata


def test_inclusive_selection_and_source_integrity(rc):
    before = [array.tobytes() for array in (rc.frequency, rc.real, rc.imaginary_original)]
    settings = AnalysisSettings(frequency_min_hz=float(rc.frequency[-8]), frequency_max_hz=float(rc.frequency[5]),
                                lambda_method="Manual", lambda_value=1e-6)
    v = analyze(rc, settings)
    np.testing.assert_array_equal(v.frequency, rc.frequency[5:-7])
    np.testing.assert_array_equal(v.impedance, rc.impedance[5:-7])
    assert v.preprocessing["source_row_indices"] == list(range(5, len(rc.frequency)-7))
    assert v.preprocessing["excluded_indices"] == list(range(5))+list(range(len(rc.frequency)-7, len(rc.frequency)))
    assert len(v.kk.residuals) == len(v.frequency)
    assert v.tau[0] == pytest.approx(1/(2*np.pi*v.frequency.max()))
    assert v.tau[-1] == pytest.approx(1/(2*np.pi*v.frequency.min()))
    exported = metadata(rc, v)
    assert exported["settings"]["frequency_min_hz"] == settings.frequency_min_hz
    assert exported["preprocessing"]["points_source"] == len(rc.frequency)
    assert [array.tobytes() for array in (rc.frequency, rc.real, rc.imaginary_original)] == before


@pytest.mark.parametrize("lower,upper", [(0, 1), (-1, 5), (5, 5), (6, 5), (float("nan"), 3), (1, float("inf"))])
def test_invalid_bounds(lower, upper):
    with pytest.raises(ValueError):
        AnalysisSettings(frequency_min_hz=lower, frequency_max_hz=upper).validate()


def test_empty_and_too_small_window(rc):
    for lower, upper in ((1e6, 1e7), (float(rc.frequency[3]), float(rc.frequency[0]))):
        with pytest.raises(ValueError, match="at least 8"):
            analyze(rc, AnalysisSettings(frequency_min_hz=lower, frequency_max_hz=upper))


def test_outside_requested_bounds_and_full_reset(rc):
    f, z, info = prepare(rc, AnalysisSettings(frequency_min_hz=1e-8, frequency_max_hz=1e8))
    np.testing.assert_array_equal(f, rc.frequency)
    assert not info["excluded_indices"]
    a = analyze(rc, AnalysisSettings(frequency_min_hz=.1, frequency_max_hz=1e4, lambda_method="Manual", validation=False))
    b = analyze(rc, replace(a.settings, frequency_min_hz=None, frequency_max_hz=None))
    assert len(a.frequency) < len(b.frequency) == len(rc.frequency)


def test_scan_and_auto_share_window(rc):
    settings = replace(auto_settings(.1, 1e4), lambda_count=7, validation=True)
    variants = lambda_scan(rc, settings)
    assert all(v.frequency.min() >= .1 and v.frequency.max() <= 1e4 for v in variants)
    assert all(v.settings.frequency_min_hz == .1 for v in variants)
    assert all(v.kk is variants[0].kk for v in variants)
