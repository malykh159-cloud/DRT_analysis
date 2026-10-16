from dataclasses import replace
import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets as QtW
from test_gui import app, wait_until
from conftest import synthetic
from drt_analyzer.app.main_window import MainWindow, Entry
from drt_analyzer.analysis.pipeline import analyze
from drt_analyzer.drt.base import AnalysisSettings, BayesianSettings


def fast_settings():
    return AnalysisSettings(method="Bayesian DRT", lambda_method="Manual", lambda_value=.001,
        validation=False, bayesian=BayesianSettings(warmup=10, samples=30, chains=2))


def test_method_block_defaults_history_and_credible_plot(app):
    window = MainWindow()
    window.show()
    panel = window.settings
    assert panel.bayesian.isHidden()
    groups = [panel.layout().itemAt(i).widget() for i in range(panel.layout().count())]
    titles = [w.title() for w in groups if isinstance(w, QtW.QGroupBox)]
    i = titles.index("BAYESIAN")
    assert titles[i-1:i+2] == ["REGULARIZATION", "BAYESIAN", "RBF"]
    panel.method.setCurrentText("Bayesian DRT")
    assert not panel.bayesian.isHidden() and panel.bayesian.advanced.isHidden()
    assert panel.value().bayesian == BayesianSettings()
    raw = synthetic(f=np.geomspace(1e3, .1, 21))
    window.entries = [Entry(raw)]
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    t = analyze(raw, AnalysisSettings(validation=False))
    b = analyze(raw, fast_settings())
    window.result_ready(0, t)
    window.result_ready(0, b)
    assert "Bayesian" in window.history_list.currentItem().text()
    assert "R-hat" in window.report.toPlainText()
    assert any(item.name() == "95% credible interval" for item in window.plots.drt.listDataItems())
    app.processEvents()
    assert not window.grab().isNull()
    window.plots.axis.setCurrentIndex(1)
    assert any(item.name() == "95% credible interval" for item in window.plots.drt.listDataItems())
    window.undo()
    assert window.current.history.current is t and panel.bayesian.isHidden()
    assert not any(item.name() == "95% credible interval" for item in window.plots.drt.listDataItems())
    window.redo()
    assert window.current.history.current is b and not panel.bayesian.isHidden()
    window.close()


def test_bayesian_stop_current_batch_and_restart(app):
    window = MainWindow()
    raw = synthetic(f=np.geomspace(1e3, .1, 21))
    window.entries = [Entry(raw), Entry(raw)]
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    old = analyze(raw, AnalysisSettings(validation=False))
    window.result_ready(0, old)
    slow = replace(fast_settings(), bayesian=BayesianSettings(samples=100000))
    window.start_jobs([(0, raw, slow), (1, raw, slow)])
    ticks = []
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(5)
    wait_until(app, lambda: window.progress.maximum() > 2)
    window.stop_button.click()
    wait_until(app, lambda: window.thread is None, timeout=5)
    timer.stop()
    assert ticks and window.entries[0].history.current is old
    assert all(e.status == "Cancelled" for e in window.entries)
    assert window.entries[1].history.current is None
    window.start_jobs([(0, raw, fast_settings())])
    wait_until(app, lambda: window.thread is None, timeout=20)
    assert window.entries[0].history.current.settings.method == "Bayesian DRT"
    assert not window.stop_button.isEnabled()
    window.close()


def test_bayesian_auto_all_dispatch_only_bayesian(app, monkeypatch):
    window = MainWindow()
    raw = synthetic(f=np.geomspace(1e3, .1, 21))
    window.entries = [Entry(raw), Entry(raw)]
    window.refresh_table()
    window.table.setCurrentCell(0, 0)
    window.settings.load(fast_settings())
    jobs = []
    monkeypatch.setattr(window, "start_jobs", lambda pending: jobs.extend(pending))
    window.auto_all()
    assert len(jobs) == 2
    assert all(s.method == "Bayesian DRT" and s.bayesian == fast_settings().bayesian for _, _, s in jobs)
    window.close()
