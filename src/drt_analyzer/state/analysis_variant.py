from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np
from ..data.models import readonly


@dataclass(frozen=True, eq=False)
class AnalysisVariant:
    id: str
    created_utc: str
    settings: object
    frequency: np.ndarray
    impedance: np.ndarray
    tau: np.ndarray
    gamma: np.ndarray
    reconstructed: np.ndarray
    residuals: np.ndarray
    lambda_value: float
    shape_value: float
    rs_ohm: float
    inductance_h: float
    rp_total: float
    peaks: tuple
    quality: dict
    preprocessing: dict
    kk: object
    lambda_selection: object
    warnings: tuple[str, ...]
    penalty_norm: float
    uncertainty: object = None

    def __post_init__(self):
        for name in ("frequency", "impedance", "tau", "gamma", "reconstructed", "residuals"):
            value = getattr(self, name)
            object.__setattr__(self, name, readonly(value, complex if np.iscomplexobj(value) else float))


def identity():
    return str(uuid4()), datetime.now(timezone.utc).isoformat()
