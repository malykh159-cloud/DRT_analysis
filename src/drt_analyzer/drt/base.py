from dataclasses import dataclass
from typing import Protocol, Callable


class Cancelled(Exception):
    """Cooperative cancellation, checked between all expensive operations."""


def check_cancel(cancel):
    if cancel and cancel():
        raise Cancelled("Analysis cancelled.")


@dataclass(frozen=True)
class BayesianSettings:
    warmup: int = 1000
    samples: int = 2000  # retained draws per chain
    chains: int = 4
    seed: int = 42
    credible_interval: float = 95.
    noise_sigma: float = 0.  # zero = residual plug-in estimate in weighted coordinates
    noise_floor: float = 1e-6
    trajectory_time: float = 1.5707963267948966
    max_reflections: int = 10000

    def validate(self):
        import math
        if not (isinstance(self.warmup, int) and 0 <= self.warmup <= 100000
                and isinstance(self.samples, int) and 20 <= self.samples <= 100000
                and isinstance(self.chains, int) and 1 <= self.chains <= 16
                and isinstance(self.seed, int) and 0 <= self.seed <= 2147483647):
            raise ValueError("Bayesian: invalid warm-up, samples, chains or seed.")
        if not (50 <= self.credible_interval < 100 and math.isfinite(self.noise_sigma)
                and 0 <= self.noise_sigma <= 1 and 1e-12 <= self.noise_floor <= .1
                and .05 <= self.trajectory_time <= 3 and 10 <= self.max_reflections <= 100000):
            raise ValueError("Bayesian: invalid interval, noise or trajectory settings.")


@dataclass(frozen=True)
class AnalysisSettings:
    method: str = "Tikhonov"
    mode: str = "Manual"
    lambda_method: str = "rGCV"
    lambda_value: float = 1e-3
    lambda_min_exp: float = -6
    lambda_max_exp: float = 2
    lambda_count: int = 41
    rbf: str = "Gaussian"
    shape_mode: str = "Manual"
    shape_value: float = 6.0
    derivative_order: int = 2
    validation: bool = True
    kk_mu: float = 0.85
    kk_max_elements: int = 50
    kk_min_per_decade: float = 3.0
    kk_tolerance: float = 0.02
    kk_add_capacitance: bool = True
    peak_prominence: float = 0.03
    peak_distance_decades: float = 0.15
    kfold_splits: int = 5
    random_seed: int = 34054
    frequency_min_hz: float | None = None
    frequency_max_hz: float | None = None
    bayesian: BayesianSettings = BayesianSettings()

    def validate(self):
        import math
        for bound in (self.frequency_min_hz, self.frequency_max_hz):
            if bound is not None and (not math.isfinite(bound) or bound <= 0):
                raise ValueError("Frequency bounds must be finite and strictly positive.")
        if (self.frequency_min_hz is not None and self.frequency_max_hz is not None
                and self.frequency_min_hz >= self.frequency_max_hz):
            raise ValueError("Minimum frequency must be less than maximum frequency.")
        if self.method not in {"Tikhonov", "Bayesian DRT"}:
            raise ValueError("Unknown DRT method.")
        if self.method == "Bayesian DRT":
            self.bayesian.validate()
        if self.mode not in {"Auto", "Manual"}:
            raise ValueError("Mode must be Auto or Manual.")
        if self.lambda_method not in {"Manual", "GCV", "mGCV", "rGCV", "L-curve", "k-fold"}:
            raise ValueError("Unknown lambda selection method.")
        if not math.isfinite(self.lambda_value) or self.lambda_value <= 0:
            raise ValueError("Lambda must be finite and positive.")
        if not (-14 <= self.lambda_min_exp < self.lambda_max_exp <= 8 and 7 <= self.lambda_count <= 201):
            raise ValueError("Lambda scan: -14 <= min exponent < max <= 8; 7–201 samples.")
        if self.rbf not in {"Gaussian", "C2 Matern", "C4 Matern", "C6 Matern"}:
            raise ValueError("Unknown RBF.")
        if self.shape_mode not in {"Auto", "Manual"} or not 0.05 <= self.shape_value <= 100:
            raise ValueError("Shape must be in [0.05, 100].")
        if self.derivative_order not in (0, 1, 2):
            raise ValueError("Derivative order must be 0, 1 or 2.")
        if not (0 < self.peak_prominence < 1 and 0 <= self.peak_distance_decades <= 2):
            raise ValueError("Invalid peak detection settings.")
        if not (0 < self.kk_mu < 1 and 3 <= self.kk_max_elements <= 100
                and 0 < self.kk_min_per_decade <= 10 and 0 < self.kk_tolerance < 1
                and 2 <= self.kfold_splits <= 10):
            raise ValueError("Invalid validation settings.")


class DRTEngine(Protocol):
    def analyze(self, raw, settings: AnalysisSettings, cancel: Callable | None = None): ...
