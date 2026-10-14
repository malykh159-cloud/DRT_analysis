"""Executable-level smoke verification: synthetic numerical truth + real Qt export."""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from PySide6 import QtWidgets as QtW
from ..data.models import RawSpectrum, ImportInfo
from ..drt.base import AnalysisSettings
from ..analysis.pipeline import analyze
from ..export.tables import export_xlsx, export_csv_bundle
from ..export.settings import export_settings
from ..export.plots import export_plot
from .main_window import Entry


def run_smoke(window, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    f = np.geomspace(1e5, .01, 81)
    z = 5+30/(1+2j*np.pi*f*1e-4)+70/(1+2j*np.pi*f*.1)+2j*np.pi*f*1e-5
    raw = RawSpectrum("Synthetic two RC validation.csv", "synthetic-not-a-file-hash", f, z.real, z.imag,
        ImportInfo("synthetic", ",", ("Frequency", "Re", "Im"), (0, 1, 2), "Im(Z)", 1, "synthetic truth"))
    settings = AnalysisSettings(lambda_method="Manual", lambda_value=1e-6)
    v = analyze(raw, settings)
    assert len(v.peaks) == 2
    assert abs(v.rp_total-100) < 2
    assert v.quality["relative_rms"] < .01
    window.entries.append(Entry(raw))
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    window.table.selectRow(0)
    window.result_ready(0, v)
    second = analyze(raw, replace(settings, lambda_value=1e-4))
    window.result_ready(0, second)
    window.undo()
    assert window.current.history.current is v
    window.redo()
    assert window.current.history.current is second
    window.undo()
    window.plots.tabs.setCurrentIndex(2)
    window.plots.compare([(raw, v)], switch=False)
    QtW.QApplication.processEvents()
    window.grab().save(str(output/"workspace.png"))
    for name, item in window.plots.all_plots().items():
        for suffix in ("png", "svg"):
            export_plot(item, output/f"{name}.{suffix}")
    export_xlsx(output/"results.xlsx", [(raw, v)])
    export_csv_bundle(output/"csv", [(raw, v)])
    export_settings(output/"settings.json", raw, v)
    result = {"passed": True, "rp_total": v.rp_total, "peaks": len(v.peaks),
              "relative_rms": v.quality["relative_rms"], "kk_status": v.kk.status,
              "lambda": v.lambda_value, "shape": v.shape_value,
              "undo_redo": "passed", "plots": 14}
    (output/"smoke_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
