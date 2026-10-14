from dataclasses import asdict, is_dataclass
import json
import math
import platform
import importlib.metadata
from pathlib import Path
import numpy as np
from .. import __version__


def clean(value):
    if is_dataclass(value):
        return clean(asdict(value))
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def metadata(raw, variant):
    v = variant
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "PySide6", "pyqtgraph", "openpyxl")}
    return clean({
        "schema_version": 1, "software": "DRT Analyzer", "software_version": __version__,
        "python": platform.python_version(), "dependencies": versions,
        "source_filename": raw.name, "source_path": raw.source_path, "source_sha256": raw.source_hash,
        "import": raw.info, "source_warnings": raw.warnings,
        "variant_id": v.id, "created_utc": v.created_utc, "settings": v.settings,
        "actual_lambda": v.lambda_value, "actual_shape_epsilon": v.shape_value,
        "preprocessing": v.preprocessing, "warnings": v.warnings,
        "quality": v.quality, "rp_total_ohm": v.rp_total, "rs_ohm": v.rs_ohm,
        "inductance_h": v.inductance_h, "peaks": v.peaks,
        "lambda_selection": v.lambda_selection,
        "lin_kk": None if v.kk is None else {
            "status": v.kk.status, "n_elements": v.kk.n_elements, "mu": v.kk.mu,
            "mu_reached": v.kk.mu_reached, "relative_rms": v.kk.relative_rms,
            "warnings": v.kk.warnings},
        "uncertainty": None,
    })


def export_settings(path, raw, variant):
    Path(path).write_text(json.dumps(metadata(raw, variant), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
