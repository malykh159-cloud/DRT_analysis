import numpy as np


def prepare(raw):
    """Sort a copy only; never exclude or modify experimental samples."""
    order = np.argsort(raw.frequency)[::-1]
    return raw.frequency[order].copy(), raw.impedance[order].copy(), {
        "sorting": "frequency descending", "source_row_indices": order.tolist(),
        "points_source": len(order), "points_used": len(order), "excluded_indices": [],
        "im_multiplier": raw.info.im_multiplier,
    }
