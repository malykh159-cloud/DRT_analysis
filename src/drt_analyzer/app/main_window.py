import logging
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets as QtW
from .. import __version__
from ..analysis.pipeline import auto_settings
from ..data.importers import load_spectrum
from ..drt.base import AnalysisSettings
from ..state.history import History
from ..ui.settings_panel import SettingsPanel
from ..ui.plots import SpectrumPlots
from ..ui.lambda_scan import LambdaScanDialog
from ..export.tables import export_xlsx, export_csv_bundle
from ..export.settings import export_settings
from ..export.plots import export_plot
from .workers import AnalysisWorker

log = logging.getLogger(__name__)


def variant_status(variant):
    return "Review" if (variant.quality["relative_rms"] > .02 or
        (variant.kk and variant.kk.status != "Compatible") or any(p.edge for p in variant.peaks)) else "Ready"


@dataclass
class Entry:
    raw: object
    history: History = field(default_factory=History)
    draft: AnalysisSettings = field(default_factory=AnalysisSettings)
    status: str = "Imported"
    error: str = ""


class MainWindow(QtW.QMainWindow):
    def __init__(self):
        super().__init__()
        self.entries = []
        self.current_index = -1
        self.worker = self.thread = None
        self._closing = False
        self._pending_scan = None
        self.setWindowTitle(f"DRT Analyzer {__version__}")
        self.resize(1550, 950)
        self.setMinimumSize(1050, 700)
        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self):
        toolbar = self.addToolBar("Analysis")
        toolbar.setMovable(False)

        def action(text, slot, shortcut=None):
            item = QtGui.QAction(text, self)
            item.triggered.connect(slot)
            if shortcut:
                item.setShortcut(shortcut)
            toolbar.addAction(item)
            return item

        self.import_action = action("Import EIS…", self.import_files, "Ctrl+O")
        self.calculate_action = action("Run analysis", self.calculate, "F5")
        self.auto_action = action("Auto Analyze Selected", self.auto_selected)
        self.auto_all_action = action("Auto All", self.auto_all)
        self.cancel_action = action("Cancel", self.cancel)
        self.cancel_action.setEnabled(False)
        toolbar.addSeparator()
        self.undo_action = action("Undo", self.undo, "Ctrl+Z")
        self.redo_action = action("Redo", self.redo, "Ctrl+Y")
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self.scan_action = action("Lambda Scan", self.scan)
        self.compare_action = action("Compare DRT", self.compare_selected)
        toolbar.addSeparator()
        export_menu = QtW.QMenu("Export", self)
        for text, slot in (("Results XLSX…", self.save_xlsx), ("CSV bundle + JSON…", self.save_csv),
                           ("Current settings JSON…", self.save_json), ("Active plot PNG / SVG…", self.save_plot),
                           ("All plots PNG + SVG…", self.save_all_plots)):
            export_menu.addAction(text, slot)
        export_button = QtW.QToolButton()
        export_button.setText("Export")
        export_button.setMenu(export_menu)
        export_button.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(export_button)
        self.menuBar().addMenu(export_menu)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("Mathematics and limitations", self.help_math)
        help_menu.addAction("About", self.about)

        splitter = QtW.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        left = QtW.QWidget()
        ll = QtW.QVBoxLayout(left)
        ll.setContentsMargins(8, 8, 4, 8)
        heading = QtW.QLabel("SPECTRA")
        heading.setStyleSheet("font-weight: 600;")
        ll.addWidget(heading)
        hint = QtW.QLabel("Ctrl / Shift: select several · Del: remove")
        hint.setStyleSheet("color: #586974;")
        ll.addWidget(hint)
        self.table = QtW.QTableWidget(0, 9)
        self.table.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.currentCellChanged.connect(self.selection_changed)
        ll.addWidget(self.table, 1)
        self.remove_files_button = QtW.QPushButton("Remove selected spectra (Del)")
        self.remove_files_button.setToolTip("Remove from this session only. Original files remain on disk.")
        self.remove_files_button.clicked.connect(self.remove_selected_spectra)
        ll.addWidget(self.remove_files_button)
        history_label = QtW.QLabel("ANALYSIS HISTORY")
        history_label.setStyleSheet("font-weight: 600;")
        ll.addWidget(history_label)
        self.history_list = QtW.QListWidget()
        self.history_list.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.history_list.setMaximumHeight(150)
        self.history_list.currentRowChanged.connect(self.history_selected)
        ll.addWidget(self.history_list)
        self.remove_history_button = QtW.QPushButton("Remove selected variants (Del)")
        self.remove_history_button.clicked.connect(self.remove_selected_history)
        ll.addWidget(self.remove_history_button)
        self._delete_shortcuts = []
        for widget, callback in ((self.table, self.remove_selected_spectra),
                                 (self.history_list, self.remove_selected_history)):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence("Delete"), widget)
            shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._delete_shortcuts.append(shortcut)
        splitter.addWidget(left)

        center = QtW.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.plots = SpectrumPlots()
        center.addWidget(self.plots)
        details = QtW.QTabWidget()
        self.details_tabs = details
        self.peaks = QtW.QTableWidget(0, 7)
        self.peaks.setHorizontalHeaderLabels(["Peak", "τ (s)", "f (Hz)", "γ peak (Ω)", "Rp (Ω)", "Fraction (%)", "Edge"])
        self.peaks.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.peaks.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.peaks.horizontalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.Stretch)
        self.plots.peak_selected.connect(self.select_peak)
        details.addTab(self.peaks, "Peaks")
        self.report = QtW.QPlainTextEdit()
        self.report.setReadOnly(True)
        details.addTab(self.report, "Results / decisions")
        self.warnings = QtW.QPlainTextEdit()
        self.warnings.setReadOnly(True)
        details.addTab(self.warnings, "Warnings")
        center.addWidget(details)
        center.setSizes([620, 180])
        splitter.addWidget(center)
        self.settings = SettingsPanel()
        scroll = QtW.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.settings)
        scroll.setMinimumWidth(320)
        splitter.addWidget(scroll)
        splitter.setSizes([360, 840, 350])
        splitter.setStretchFactor(1, 1)
        self.progress = QtW.QProgressBar()
        self.progress.setMaximumWidth(280)
        self.progress.setValue(0)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("Import TXT / CSV / XLSX to begin. Original data are preserved.")
        self.refresh_table()

    @property
    def current(self):
        return self.entries[self.current_index] if 0 <= self.current_index < len(self.entries) else None

    def notify_error(self, title, message):
        log.error("%s: %s", title, message)
        QtW.QMessageBox.warning(self, title, message)

    def selected_indices(self):
        return sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})

    def import_files(self):
        paths, _ = QtW.QFileDialog.getOpenFileNames(self, "Import EIS spectra", "", "EIS (*.txt *.csv *.tsv *.xlsx)")
        self.add_files(paths)

    def add_files(self, paths):
        if self.thread:
            return
        failures = []
        for path in paths:
            try:
                raw = load_spectrum(path)
                if any(e.raw.source_path == raw.source_path and e.raw.source_hash == raw.source_hash for e in self.entries):
                    continue
                self.entries.append(Entry(raw))
            except Exception as exc:
                log.exception("Import failed: %s", path)
                failures.append(f"{Path(path).name}: {exc}")
        self.refresh_table()
        if self.entries and self.current_index < 0:
            self.table.setCurrentCell(0, 0)
            self.table.selectRow(0)
        self.statusBar().showMessage(f"{len(self.entries)} spectra loaded. Select a spectrum and Run analysis, or use Auto.")
        if failures:
            self.notify_error("Some files could not be imported", "\n\n".join(failures))

    def refresh_table(self):
        selected = self.selected_indices() if self.table.rowCount() else []
        current = self.current_index
        self.table.blockSignals(True)
        max_peaks = max((len(e.history.current.peaks) if e.history.current else 0 for e in self.entries), default=0)
        headers = ["File", "Status", "DRT method", "λ method", "λ", "RBF", "Order", "Rp total (Ω)", "Peaks"]
        headers += [f"τ{i+1} (s)" for i in range(max_peaks)]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            v = entry.history.current
            cells = [entry.raw.name, entry.status, v.settings.method if v else "—",
                     v.settings.lambda_method if v else "—", f"{v.lambda_value:.4g}" if v else "—",
                     v.settings.rbf if v else "—", str(v.settings.derivative_order) if v else "—",
                     f"{v.rp_total:.6g}" if v else "—", str(len(v.peaks)) if v else "—"]
            cells += [f"{p.tau_s:.5g}" for p in v.peaks] if v else []
            cells += [""]*(len(headers)-len(cells))
            for col, value in enumerate(cells):
                item = QtW.QTableWidgetItem(value)
                item.setToolTip(entry.raw.source_path if col == 0 else entry.error or ("\n".join(v.warnings) if v else ""))
                if col == 1 and entry.status in {"Error", "Review", "Cancelled"}:
                    item.setForeground(QtGui.QColor("#a54d1e"))
                self.table.setItem(row, col, item)
        self.table.setColumnWidth(0, 235)
        for col in range(1, len(headers)):
            self.table.setColumnWidth(col, 95 if col != 5 else 110)
        self.table.clearSelection()
        if 0 <= current < len(self.entries):
            self.table.setCurrentCell(current, 0, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)
        for row in selected:
            if row < len(self.entries):
                self.table.selectionModel().select(self.table.model().index(row, 0),
                    QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows)
        self.table.blockSignals(False)

    def selection_changed(self, row, column, oldrow, oldcolumn):
        if self.current:
            try:
                self.current.draft = self.settings.value()
            except ValueError:
                pass
        self.current_index = row
        self.show_current(load_settings=True)

    def show_current(self, load_settings=False, refresh_history=True):
        entry = self.current
        self.refresh_comparison()
        if not entry:
            self.plots.show_spectrum(None)
            self.peaks.setRowCount(0)
            self.report.clear()
            self.warnings.clear()
            self.history_list.blockSignals(True)
            self.history_list.clear()
            self.history_list.blockSignals(False)
            self.settings.load(AnalysisSettings())
            self.settings.set_source_range(None)
            self.undo_action.setEnabled(False)
            self.redo_action.setEnabled(False)
            return
        v = entry.history.current
        self.plots.show_spectrum(entry.raw, v)
        if load_settings:
            self.settings.load(entry.draft, v)
            self.settings.set_source_range(entry.raw)
        self.peaks.setRowCount(len(v.peaks) if v else 0)
        if v:
            for row, p in enumerate(v.peaks):
                values = [str(p.index), f"{p.tau_s:.6g}", f"{p.frequency_hz:.6g}", f"{p.gamma_ohm:.6g}",
                          f"{p.rp_ohm:.6g}", f"{100*p.fraction:.3f}", "unresolved" if p.edge else ""]
                for col, text in enumerate(values):
                    self.peaks.setItem(row, col, QtW.QTableWidgetItem(text))
            induction = v.preprocessing["inductance"]
            kk = f"{v.kk.status}; M={v.kk.n_elements}; μ={v.kk.mu:.4g}; RMS={100*v.kk.relative_rms:.4g}%" if v.kk else "Not run"
            self.report.setPlainText(
                f"{entry.raw.name}\n{v.settings.mode} · {v.settings.method} · {v.created_utc}\n"
                f"Rp (finite measured window) = {v.rp_total:.8g} Ω; Rs = {v.rs_ohm:.7g} Ω; L = {v.inductance_h:.7g} H\n"
                f"λ method = {v.settings.lambda_method}; actual λ = {v.lambda_value:.9g}; "
                f"{v.settings.rbf}; ε = {v.shape_value:.7g}; derivative order = {v.settings.derivative_order}\n"
                f"Relative RMS = {100*v.quality['relative_rms']:.5g}%; RMS Re = {v.quality['rms_real_ohm']:.6g} Ω; "
                f"RMS Im = {v.quality['rms_imag_ohm']:.6g} Ω\n"
                f"Lin-KK: {kk}\n"
                f"Im convention: {entry.raw.info.im_convention}; {entry.raw.info.sign_evidence}\n"
                f"HF inductive range (Hz): {induction['frequency_range_hz']}; {induction['action']}\n"
                f"Points used: {len(v.frequency)}/{len(entry.raw.frequency)}; "
                f"frequency range: {v.frequency.min():.7g} … {v.frequency.max():.7g} Hz; "
                f"τ window: {v.tau[0]:.6g} … {v.tau[-1]:.6g} s\n"
                f"Source SHA-256: {entry.raw.source_hash}\n"
                "Auto results can be edited directly; Run analysis creates a new Manual snapshot.")
            self.warnings.setPlainText("\n\n".join(v.warnings) or "No diagnostic warnings.")
        else:
            self.report.setPlainText(f"{entry.raw.name}\n{len(entry.raw.frequency)} source points\n"
                f"Im convention: {entry.raw.info.im_convention}\n{entry.raw.info.sign_evidence}\n"
                f"SHA-256: {entry.raw.source_hash}\nChoose settings and Run analysis, or Auto Analyze Selected.")
            self.warnings.setPlainText("\n".join(entry.raw.warnings))
        if refresh_history:
            self.history_list.blockSignals(True)
            self.history_list.clear()
            for i, previous in enumerate(entry.history.variants):
                self.history_list.addItem(f"{i+1}. {previous.settings.mode} · {previous.settings.rbf} · "
                                          f"λ={previous.lambda_value:.4g} · Rp={previous.rp_total:.5g} Ω")
            self.history_list.setCurrentRow(entry.history.position)
            self.history_list.blockSignals(False)
        self.undo_action.setEnabled(not self.thread and entry.history.position > 0)
        self.redo_action.setEnabled(not self.thread and entry.history.position < len(entry.history.variants)-1)

    def select_peak(self, index):
        self.details_tabs.setCurrentIndex(0)
        self.peaks.selectRow(index)

    def calculate(self):
        if not self.current or self.thread:
            return
        try:
            settings = self.settings.value()
            self.current.draft = settings
            self.start_jobs([(self.current_index, self.current.raw, settings)])
        except ValueError as exc:
            self.notify_error("Invalid settings", str(exc))

    def auto_selected(self):
        indices = self.selected_indices()
        if not indices and self.current:
            indices = [self.current_index]
        self.start_auto(indices)

    def auto_all(self):
        self.start_auto(range(len(self.entries)))

    def start_auto(self, indices):
        if self.thread:
            return
        try:
            if self.current:
                self.current.draft = self.settings.value()
            jobs = []
            for i in indices:
                entry = self.entries[i]
                settings = auto_settings(entry.draft.frequency_min_hz, entry.draft.frequency_max_hz)
                settings.validate()
                jobs.append((i, entry.raw, settings))
            self.start_jobs(jobs)
        except ValueError as exc:
            self.notify_error("Invalid settings", str(exc))

    def scan(self):
        if not self.current or self.thread:
            return
        try:
            settings = self.settings.value()
            self.start_jobs([(self.current_index, self.current.raw, settings)], scan=True)
        except ValueError as exc:
            self.notify_error("Invalid scan settings", str(exc))

    def start_jobs(self, jobs, scan=False):
        if not jobs or self.thread:
            return
        self._pending_scan = None
        for i, _, _ in jobs:
            self.entries[i].status = "Queued"
            self.entries[i].error = ""
        self.progress.setRange(0, jobs[0][2].lambda_count if scan else len(jobs))
        self.progress.setValue(0)
        self.thread = QtCore.QThread(self)
        self.worker = AnalysisWorker(jobs, scan)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.started_item.connect(self.item_started)
        self.worker.result.connect(self.result_ready)
        self.worker.failed.connect(self.item_failed)
        self.worker.scan_result.connect(self.scan_ready)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.batch_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.thread_stopped)
        self.set_busy(True)
        self.refresh_table()
        self.thread.start()

    def set_busy(self, busy):
        for action in (self.import_action, self.calculate_action, self.auto_action, self.auto_all_action,
                       self.scan_action, self.undo_action, self.redo_action):
            action.setEnabled(not busy)
        self.settings.setEnabled(not busy)
        self.cancel_action.setEnabled(busy)
        self.remove_files_button.setEnabled(not busy)
        self.remove_history_button.setEnabled(not busy)
        self.history_list.setEnabled(not busy)

    @QtCore.Slot(int, int)
    def update_progress(self, done, total):
        self.progress.setRange(0, total)
        self.progress.setValue(done)

    @QtCore.Slot(int, str)
    def item_started(self, index, name):
        self.entries[index].status = "Analyzing"
        self.refresh_table()
        self.statusBar().showMessage(f"Analyzing {name}…")

    @QtCore.Slot(int, object)
    def result_ready(self, index, variant):
        entry = self.entries[index]
        entry.history.push(variant)
        entry.draft = replace(variant.settings, lambda_value=variant.lambda_value)
        entry.status = variant_status(variant)
        self.refresh_table()
        if self.current_index == index:
            self.show_current(load_settings=True)
        else:
            self.refresh_comparison()

    @QtCore.Slot(int, str)
    def item_failed(self, index, message):
        self.entries[index].status = "Error"
        self.entries[index].error = message
        self.refresh_table()
        self.statusBar().showMessage(f"{self.entries[index].raw.name}: {message}")
        if self.current_index == index:
            self.warnings.setPlainText(message)
            self.details_tabs.setCurrentIndex(2)

    @QtCore.Slot(int, object)
    def scan_ready(self, index, variants):
        self._pending_scan = (index, variants)
        self.entries[index].status = "Scan ready"

    @QtCore.Slot(bool)
    def batch_finished(self, cancelled):
        for entry in self.entries:
            if entry.status in {"Analyzing", "Queued"}:
                entry.status = "Cancelled" if cancelled else "Imported"
        self.refresh_table()
        errors = sum(e.status == "Error" for e in self.entries)
        self.statusBar().showMessage("Cancelled; completed results retained." if cancelled else
                                   f"Analysis completed. {errors} error(s). Inspect Results / decisions and Warnings.")

    @QtCore.Slot()
    def thread_stopped(self):
        self.thread = self.worker = None
        self.set_busy(False)
        self.show_current()
        if self._closing:
            self.close()
        elif self._pending_scan:
            index, variants = self._pending_scan
            self._pending_scan = None
            dialog = LambdaScanDialog(self.entries[index].raw, variants, self)
            if dialog.exec() == QtW.QDialog.DialogCode.Accepted:
                self.result_ready(index, dialog.chosen)
                self.table.setCurrentCell(index, 0)
                self.show_current(load_settings=True)

    def cancel(self):
        if self.worker:
            self.worker.cancel()
            self.statusBar().showMessage("Cancelling after current numerical operation…")

    def undo(self):
        if self.current and not self.thread:
            v = self.current.history.undo()
            if v:
                self.current.draft = replace(v.settings, lambda_value=v.lambda_value)
                self.current.status = variant_status(v)
            self.refresh_table()
            self.show_current(load_settings=True)

    def redo(self):
        if self.current and not self.thread:
            v = self.current.history.redo()
            if v:
                self.current.draft = replace(v.settings, lambda_value=v.lambda_value)
                self.current.status = variant_status(v)
            self.refresh_table()
            self.show_current(load_settings=True)

    def history_selected(self, row):
        if self.current and not self.thread and row >= 0:
            v = self.current.history.select(row)
            self.current.draft = replace(v.settings, lambda_value=v.lambda_value)
            self.current.status = variant_status(v)
            self.refresh_table()
            self.show_current(load_settings=True, refresh_history=False)

    def refresh_comparison(self):
        shown = {id(raw) for raw, _ in self.plots._pairs}
        pairs = [(entry.raw, entry.history.current) for entry in self.entries
                 if id(entry.raw) in shown and entry.history.current]
        if shown:
            self.plots.compare(pairs, switch=False)

    def remove_selected_spectra(self):
        if self.thread:
            return
        removed = set(self.selected_indices())
        if not removed:
            return
        previous = self.current
        if previous and self.current_index not in removed:
            try:
                previous.draft = self.settings.value()
            except ValueError:
                pass
        self.entries = [entry for i, entry in enumerate(self.entries) if i not in removed]
        self.current_index = next((i for i, entry in enumerate(self.entries) if entry is previous),
                                  min(min(removed), len(self.entries)-1))
        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.blockSignals(False)
        self.refresh_table()
        if self.current:
            self.table.blockSignals(True)
            self.table.selectRow(self.current_index)
            self.table.blockSignals(False)
        self.show_current(load_settings=True)
        self.statusBar().showMessage(f"Removed {len(removed)} spectra from the session. Source files remain on disk.")

    def remove_selected_history(self):
        if not self.current or self.thread:
            return
        removed = [self.history_list.row(item) for item in self.history_list.selectedItems()]
        if not removed:
            return
        variant = self.current.history.remove(removed)
        self.current.error = ""
        self.current.status = variant_status(variant) if variant else "Imported"
        if variant:
            self.current.draft = replace(variant.settings, lambda_value=variant.lambda_value)
        self.refresh_table()
        self.show_current(load_settings=True)
        self.statusBar().showMessage(f"Removed {len(removed)} analysis variants from history.")

    def result_pairs(self):
        indices = self.selected_indices() or ([self.current_index] if self.current else [])
        return [(self.entries[i].raw, self.entries[i].history.current) for i in indices if self.entries[i].history.current]

    def compare_selected(self):
        pairs = self.result_pairs()
        if not pairs:
            self.notify_error("No results", "Select spectra with calculated DRT results.")
            return
        self.plots.compare(pairs)

    def save_xlsx(self):
        pairs = self.result_pairs()
        if not pairs:
            return self.notify_error("No results", "Run analysis and select result rows first.")
        path, _ = QtW.QFileDialog.getSaveFileName(self, "Export selected results", "DRT_results.xlsx", "Excel (*.xlsx)")
        if path:
            self.export_call(lambda: export_xlsx(path, pairs), path)

    def export_call(self, callback, path):
        try:
            callback()
            self.statusBar().showMessage(f"Exported: {path}")
        except Exception as exc:
            log.exception("Export failed")
            self.notify_error("Export failed", str(exc))

    def save_csv(self):
        pairs = self.result_pairs()
        if not pairs:
            return self.notify_error("No results", "Run analysis and select result rows first.")
        parent = QtW.QFileDialog.getExistingDirectory(self, "Choose parent directory for a new CSV bundle")
        if parent:
            path = Path(parent)/datetime.now().strftime("DRT_export_%Y%m%d_%H%M%S_%f")
            self.export_call(lambda: export_csv_bundle(path, pairs), path)

    def save_json(self):
        if not self.current or not self.current.history.current:
            return self.notify_error("No result", "Run analysis for the selected spectrum first.")
        path, _ = QtW.QFileDialog.getSaveFileName(self, "Export analysis settings", "DRT_settings.json", "JSON (*.json)")
        if path:
            self.export_call(lambda: export_settings(path, self.current.raw, self.current.history.current), path)

    def save_plot(self):
        path, selected = QtW.QFileDialog.getSaveFileName(self, "Export active plot", "DRT_plot.png", "PNG (*.png);;SVG (*.svg)")
        if path:
            if not Path(path).suffix:
                path += ".svg" if "SVG" in selected else ".png"
            self.export_call(lambda: export_plot(self.plots.active_plot(), path), path)

    def save_all_plots(self):
        parent = QtW.QFileDialog.getExistingDirectory(self, "Choose parent directory for plot exports")
        if parent:
            directory = Path(parent)/datetime.now().strftime("DRT_plots_%Y%m%d_%H%M%S_%f")
            def save():
                directory.mkdir()
                for name, plot in self.plots.all_plots().items():
                    for suffix in ("png", "svg"):
                        export_plot(plot, directory/f"{name}.{suffix}")
            self.export_call(save, directory)

    def about(self):
        QtW.QMessageBox.about(self, "About DRT Analyzer", f"DRT Analyzer {__version__}\n\n"
            "Transparent, reproducible and mathematically verifiable DRT analysis.\n"
            "Tikhonov / nonnegative RBF · local Windows desktop application.\n"
            "Bayesian DRT and uncertainty are not available in this release.\n"
            "Physical interpretation of peaks remains with the researcher.")

    def help_math(self):
        QtW.QMessageBox.information(self, "Mathematics and limitations",
            "Z = Rs + jωL + ∫ γ(τ)/(1+jωτ) d ln τ; γ ≥ 0.\n"
            "Rp is the integral over the finite measured τ window. Boundary peaks may be unresolved.\n\n"
            "GCV/mGCV/rGCV use an unconstrained linear surrogate; final DRT is nonnegative.\n"
            "Lin-KK compatibility cannot establish linearity/stationarity from one spectrum.\n"
            "Compare λ, basis and derivative order to assess sensitivity.\n\n"
            "Full definitions and references: docs/MATHEMATICS.md next to the application.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.thread:
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_files([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])

    def closeEvent(self, event):
        if self.thread:
            self._closing = True
            self.cancel()
            event.ignore()
        else:
            event.accept()
