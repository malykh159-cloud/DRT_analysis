from dataclasses import dataclass
import numpy as np
from scipy.signal import find_peaks
from .rp import integrate_rp


@dataclass(frozen=True)
class Peak:
    index: int
    tau_s: float
    frequency_hz: float
    gamma_ohm: float
    rp_ohm: float
    fraction: float
    left_tau_s: float
    right_tau_s: float
    edge: bool = False
    included: bool = True


def manual_peaks(tau, gamma, regions):
    """Integrate explicitly selected, non-overlapping ln(tau) regions.

    regions: (tau at marker, left tau, right tau, included). Markers on shoulders
    describe user-selected regions, not a deconvolution into physical processes.
    """
    x = np.log(tau)
    total = integrate_rp(x, gamma)
    regions = sorted(regions, key=lambda r: r[1])
    previous = float(tau[0])
    result = []
    for k, (center, left, right, included) in enumerate(regions, 1):
        if not (np.isfinite([center, left, right]).all()
                and tau[0] <= left <= center <= right <= tau[-1] and left < right):
            raise ValueError("Each peak needs left <= marker <= right within the DRT window, and left < right.")
        if left < previous:
            raise ValueError("Peak integration regions must not overlap (excluded regions count too).")
        previous = right
        inside = (tau > left) & (tau < right)
        xx = np.r_[np.log(left), x[inside], np.log(right)]
        yy = np.interp(xx, x, gamma)
        area = integrate_rp(xx, yy)
        result.append(Peak(k, float(center), float(1/(2*np.pi*center)),
                           float(np.interp(np.log(center), x, gamma)), area,
                           area/total if total else 0., float(left), float(right),
                           center in (tau[0], tau[-1]), bool(included)))
    return tuple(result)


def detect_peaks(tau, gamma, settings):
    ln_tau = np.log(tau)
    total = integrate_rp(ln_tau, gamma)
    if total <= 0 or np.max(gamma) <= 0:
        return (), ("No capacitive DRT mass detected.",)
    distance = max(1, int(settings.peak_distance_decades*np.log(10)/(ln_tau[1]-ln_tau[0])))
    indices, _ = find_peaks(gamma, prominence=settings.peak_prominence*gamma.max(), distance=distance)
    indices = list(indices)
    warnings = []
    # Report a monotone tail ending at a boundary as an unresolved edge maximum,
    # never quietly discard its resistance or claim a well-resolved process.
    for edge, neighbor in ((0, 1), (len(gamma)-1, len(gamma)-2)):
        if gamma[edge] > gamma[neighbor] and gamma[edge] > settings.peak_prominence*gamma.max():
            if all(abs(edge-i) >= distance for i in indices):
                indices.append(edge)
    indices.sort()
    if not indices:
        return (), ("No resolved peaks; Rp remains the integral of the complete DRT.",)
    boundaries = [0]
    for a, b in zip(indices[:-1], indices[1:]):
        boundaries.append(a+int(np.argmin(gamma[a:b+1])))
    boundaries.append(len(gamma)-1)
    peaks = []
    for k, i in enumerate(indices):
        lo, hi = boundaries[k:k+2]
        rp = integrate_rp(ln_tau[lo:hi+1], gamma[lo:hi+1])
        edge = i in (0, len(gamma)-1)
        peaks.append(Peak(k+1, float(tau[i]), float(1/(2*np.pi*tau[i])), float(gamma[i]), rp,
                          rp/total, float(tau[lo]), float(tau[hi]), edge))
        if edge:
            warnings.append(f"Peak {k+1} is an unresolved boundary maximum; tau and Rp are window-dependent.")
    if gamma[0] > 0.05*gamma.max() or gamma[-1] > 0.05*gamma.max():
        warnings.append("DRT has significant boundary mass; total Rp may omit processes outside the measured window.")
    return tuple(peaks), tuple(warnings)
