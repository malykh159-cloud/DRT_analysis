import numpy as np


def detect_inductance(frequency, impedance):
    """Descending f. Heuristic screening, not proof of a physical mechanism.

    A contiguous HF prefix with Im/|Z| > 0.002 is evidence for series L.
    No points are removed. One HF point suffices, but is explicitly uncertain.
    """
    rel = impedance.imag / np.abs(impedance)
    significant = rel > 0.002
    prefix = 0
    for flag in significant:
        if not flag:
            break
        prefix += 1
    warnings = []
    if prefix == len(frequency):
        warnings.append("Completely inductive spectrum: capacitive DRT is not an adequate model.")
    if prefix == 1:
        warnings.append("HF induction detected at one point only; series-L inference is uncertain.")
    if significant[prefix:].any():
        warnings.append("Positive Im outside the contiguous HF region; series L may be insufficient.")
    if np.any((rel > 0) & ~significant):
        warnings.append("Weak positive Im below 0.2% modulus threshold; induction detection is uncertain.")
    return {
        "detected": bool(prefix), "n_points": prefix,
        "frequency_range_hz": [float(frequency[prefix-1]), float(frequency[0])] if prefix else None,
        "action": "fit nonnegative series j*omega*L; retain all points" if prefix else "no HF points excluded",
        "threshold_relative_imag": 0.002, "warnings": warnings,
    }
