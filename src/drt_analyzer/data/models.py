from dataclasses import dataclass
from pathlib import Path
import numpy as np


def readonly(values, dtype=float):
    """Use immutable bytes backing; even setflags(write=True) cannot mutate raw data."""
    array = np.ascontiguousarray(values, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


@dataclass(frozen=True)
class ImportInfo:
    encoding: str
    delimiter: str
    columns: tuple[str, str, str]
    column_indices: tuple[int, int, int]
    im_convention: str
    im_multiplier: int
    sign_evidence: str
    sheet: str = ""
    header_row: int = 1


@dataclass(frozen=True, eq=False)
class RawSpectrum:
    source_path: str
    source_hash: str
    frequency: np.ndarray
    real: np.ndarray
    imaginary_original: np.ndarray
    info: ImportInfo
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("frequency", "real", "imaginary_original"):
            object.__setattr__(self, name, readonly(getattr(self, name)))
        if not (self.frequency.ndim == 1 and self.frequency.shape == self.real.shape
                == self.imaginary_original.shape):
            raise ValueError("Spectrum columns must be equal one-dimensional arrays.")

    @property
    def name(self):
        return Path(self.source_path).name

    @property
    def impedance(self):
        return self.real + 1j * self.info.im_multiplier * self.imaginary_original
