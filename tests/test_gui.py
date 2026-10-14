from dataclasses import replace
import os
import time
from pathlib import Path
import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets as QtW
from drt_analyzer.app.main_window import MainWindow, Entry
from drt_analyzer.app.main_window import variant_status
from drt_analyzer.analysis.pipeline import analyze
from drt_analyzer.drt.base import AnalysisSettings
from drt_analyzer.ui.lambda_scan import LambdaScanDialog
from drt_analyzer.analysis.pipeline import lambda_scan
from drt_analyzer.export.plots import export_plot


@pytest.fixture(scope="module")
def app():
    return QtW.QApplication.instance() or QtW.QApplication([])


def wait_until(app, predicate, timeout=15):
    end = time.monotonic()+timeout
    while not predicate():
        app.processEvents()
        if time.monotonic() > end:
            raise AssertionError("GUI worker timed out")
        time.sleep(.005)
    app.processEvents()


def test_window_history_plots_and_export(app, rc, tmp_path):
    window = MainWindow()
    window.show()
    window.entries.append(Entry(rc))
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    settings = AnalysisSettings(lambda_method="Manual", lambda_value=1e-6, validation=False)
    a, b = analyze(rc, settings), analyze(rc, replace(settings, lambda_value=.001))
    window.result_ready(0, a)
    window.result_ready(0, b)
    window.undo()
    assert window.current.history.current is a
    assert window.current.status == variant_status(a)
    window.redo()
    assert window.current.history.current is b
    window.settings.lambda_method.setCurrentText("Manual")
    window.settings.lambda_value.setText("0.02")
    assert window.settings.value().lambda_value == .02
    window.plots.axis.setCurrentIndex(1)
    window.plots.compare([(rc, b)])
    app.processEvents()
    for name, plot in window.plots.all_plots().items():
        for suffix in ("png", "svg"):
            path = tmp_path/f"{name}.{suffix}"
            export_plot(plot, path)
            assert path.stat().st_size > 500
    window.close()


def test_background_result_and_cancellation(app, rc):
    window = MainWindow()
    window.entries = [Entry(rc), Entry(rc)]
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    settings = AnalysisSettings(lambda_method="Manual", lambda_value=1e-6, validation=False)
    window.start_jobs([(0, rc, settings), (1, rc, settings)])
    wait_until(app, lambda: window.thread is None)
    assert all(e.history.current for e in window.entries)
    assert window.progress.value() == 2
    old = window.entries[0].history.current
    slow = replace(settings, lambda_method="k-fold", lambda_count=81)
    window.start_jobs([(0, rc, slow), (1, rc, slow)])
    window.cancel()
    wait_until(app, lambda: window.thread is None)
    assert window.entries[0].history.current is old
    assert window.entries[1].status == "Cancelled"
    window.close()


def test_scan_slider_uses_cached_objects(app, rc):
    settings = AnalysisSettings(lambda_method="Manual", lambda_count=7, validation=False)
    variants = lambda_scan(rc, settings)
    dialog = LambdaScanDialog(rc, variants)
    dialog.slider.setValue(4)
    assert dialog.chosen is variants[4]
    assert dialog.plot.variant is variants[4]
    dialog.close()
