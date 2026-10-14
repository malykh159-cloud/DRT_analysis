import numpy as np


def metrics(observed, fitted):
    """Residual = (observed - fitted)/|observed|; RMS units as named."""
    absolute = observed - fitted
    relative = absolute/np.abs(observed)
    return relative, {
        "relative_rms": float(np.sqrt(np.mean(np.abs(relative)**2))),
        "rms_real_ohm": float(np.sqrt(np.mean(absolute.real**2))),
        "rms_imag_ohm": float(np.sqrt(np.mean(absolute.imag**2))),
        "rms_relative_real": float(np.sqrt(np.mean(relative.real**2))),
        "rms_relative_imag": float(np.sqrt(np.mean(relative.imag**2))),
    }
