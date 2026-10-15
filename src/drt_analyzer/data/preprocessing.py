import numpy as np


def prepare(raw, settings=None):
    """Inclusive user-selected window on a sorted copy; preserve all source data."""
    lower = settings.frequency_min_hz if settings else None
    upper = settings.frequency_max_hz if settings else None
    mask = np.ones(len(raw.frequency), dtype=bool)
    if lower is not None:
        mask &= raw.frequency >= lower
    if upper is not None:
        mask &= raw.frequency <= upper
    included = np.flatnonzero(mask)
    if len(included) < 8:
        raise ValueError(f"Selected frequency range contains {len(included)} points; at least 8 are required.")
    order = included[np.argsort(raw.frequency[included])[::-1]]
    return raw.frequency[order].copy(), raw.impedance[order].copy(), {
        "sorting": "frequency descending", "source_row_indices": order.tolist(),
        "points_source": len(raw.frequency), "points_used": len(order),
        "excluded_indices": np.flatnonzero(~mask).tolist(),
        "frequency_range": {
            "requested_min_hz": lower, "requested_max_hz": upper,
            "used_min_hz": float(raw.frequency[order].min()),
            "used_max_hz": float(raw.frequency[order].max()),
            "bounds_inclusive": True,
            "selection": "manual frequency bounds" if lower is not None or upper is not None else "full source range",
        },
        "im_multiplier": raw.info.im_multiplier,
    }
