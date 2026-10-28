from PySide6 import QtCore, QtWidgets as QtW
from .plots import SpectrumPlots, plot, line, COLORS


class LambdaScanDialog(QtW.QDialog):
    def __init__(self, raw, variants, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Lambda Scan — {raw.name}")
        self.resize(1050, 780)
        self.raw, self.variants = raw, variants
        layout = QtW.QVBoxLayout(self)
        self.description = QtW.QLabel("Cached constrained fits · choose a value, inspect DRT and residuals, then apply.")
        layout.addWidget(self.description)
        self.plot = SpectrumPlots()
        self.plot.tabs.setCurrentIndex(2)
        layout.addWidget(self.plot, 1)
        self.summary = QtW.QLabel()
        self.summary.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.summary)
        self.slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, len(variants)-1)
        layout.addWidget(self.slider)
        self.table = QtW.QTableWidget(len(variants), 5)
        self.table.setHorizontalHeaderLabels(["λ", "Relative RMS (%)", "Penalty norm", "Rp (Ω)", "Peaks"])
        self.table.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(165)
        self.table.horizontalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.Stretch)
        for i, v in enumerate(variants):
            for j, value in enumerate((v.lambda_value, 100*v.quality["relative_rms"], v.penalty_norm, v.rp_total, len(v.peaks))):
                self.table.setItem(i, j, QtW.QTableWidgetItem(f"{value:.6g}"))
        layout.addWidget(self.table)
        edit = QtW.QPushButton("Manual peaks… (current lambda)")
        edit.clicked.connect(self.edit_peaks)
        layout.addWidget(edit)
        buttons = QtW.QDialogButtonBox(QtW.QDialogButtonBox.StandardButton.Apply | QtW.QDialogButtonBox.StandardButton.Close)
        buttons.button(QtW.QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.slider.valueChanged.connect(self.select)
        self.table.currentCellChanged.connect(lambda row, col, oldrow, oldcol: self.slider.setValue(row) if row >= 0 else None)
        self.select(0)

    @property
    def chosen(self):
        return self.variants[self.slider.value()]

    def edit_peaks(self):
        from dataclasses import replace
        from .peak_editor import PeakEditor
        from ..state.analysis_variant import identity
        dialog = PeakEditor(self.raw, self.chosen, self)
        if dialog.exec() == QtW.QDialog.DialogCode.Accepted:
            id_, created = identity()
            v = replace(self.chosen, id=id_, created_utc=created, peaks=dialog.result_peaks,
                        warnings=self.chosen.warnings + ("Manual peak regions/selection; full DRT and total Rp unchanged.",))
            self.variants = list(self.variants)
            self.variants[self.slider.value()] = v
            self.select(self.slider.value())

    def select(self, index):
        v = self.variants[index]
        self.plot.show_spectrum(self.raw, v)
        self.summary.setText(f"λ = {v.lambda_value:.7g}    Relative RMS = {100*v.quality['relative_rms']:.4g}%    "
            f"Smoothness ‖Rx‖ = {v.penalty_norm:.5g}    Rp = {v.rp_total:.6g} Ω    Peaks = {len(v.peaks)}")
        self.table.blockSignals(True)
        self.table.selectRow(index)
        self.table.blockSignals(False)
