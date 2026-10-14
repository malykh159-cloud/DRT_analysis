"""Reserved engine boundary. No pseudo-credible intervals or unverified sampler."""
from .base import AnalysisSettings


class BayesianEngine:
    available = False
    reason = "Bayesian DRT requires a validated likelihood, prior and constrained posterior sampler."

    def analyze(self, raw, settings: AnalysisSettings, cancel=None):
        raise NotImplementedError(self.reason)
