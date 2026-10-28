"""Manual integration/selection of peaks; does not modify the fitted DRT."""
import numpy as np
from PySide6 import QtCore, QtWidgets as QtW
from ..analysis.peaks import manual_peaks, detect_peaks
from .plots import SpectrumPlots


class PeakEditor(QtW.QDialog):
    def __init__(self, raw, variant, parent=None):
        super().__init__(parent)
        self.raw, self.variant = raw, variant
        self.result_peaks = variant.peaks
        self.setWindowTitle("Manual peaks")
        self.resize(1050, 760)
        layout = QtW.QVBoxLayout(self)
        self.plot = SpectrumPlots()
        self.plot.tabs.setCurrentIndex(2)
        self.plot.show_spectrum(raw, variant)
        layout.addWidget(self.plot, 1)
        hint = QtW.QLabel("Uncheck Include to exclude a peak. Add a marker by frequency (Hz), then adjust its integration bounds.\n"
            "Areas integrate gamma d ln(tau). Splitting a shoulder partitions area; it does not resolve overlapping physical components.\n"
            "Adding a marker resets all region bounds to midpoints on log(tau); adjust them afterwards.\n"
            "The full DRT, fit and total Rp stay unchanged. Reset auto restores automatic peaks.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QtW.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Include", "Marker f (Hz)", "Left tau (s)", "Right tau (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QtW.QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(130)
        self.table.setMaximumHeight(210)
        layout.addWidget(self.table)
        controls = QtW.QHBoxLayout()
        for title, slot in (("Add marker…", self.add_marker), ("Reset auto", self.reset_auto)):
            button = QtW.QPushButton(title)
            button.clicked.connect(slot)
            controls.addWidget(button)
        self.total = QtW.QLabel()
        controls.addWidget(self.total)
        layout.addLayout(controls)
        buttons = QtW.QDialogButtonBox(QtW.QDialogButtonBox.StandardButton.Ok | QtW.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.table.itemChanged.connect(self.preview)
        self.plot.peak_selected.connect(self.table.selectRow)
        self.fill(variant.peaks)

    def fill(self, peaks):
        self.table.blockSignals(True)
        self.table.setRowCount(len(peaks))
        for row, p in enumerate(peaks):
            check = QtW.QTableWidgetItem()
            check.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(QtCore.Qt.CheckState.Checked if p.included else QtCore.Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)
            for col, value in enumerate((p.frequency_hz, p.left_tau_s, p.right_tau_s), 1):
                self.table.setItem(row, col, QtW.QTableWidgetItem(f"{value:.17g}"))
        self.table.blockSignals(False)
        self.preview()

    def read(self):
        regions = []
        for row in range(self.table.rowCount()):
            f, left, right = (float(self.table.item(row, col).text()) for col in (1, 2, 3))
            if not np.isfinite(f) or f <= 0:
                raise ValueError("Marker frequency must be positive and finite.")
            center = 1/(2*np.pi*f)
            # Round-tripping an edge marker through frequency can move it by 1 ULP.
            if np.isclose(center, left, rtol=1e-14, atol=0):
                center = left
            if np.isclose(center, right, rtol=1e-14, atol=0):
                center = right
            regions.append((center, left, right,
                            self.table.item(row, 0).checkState() == QtCore.Qt.CheckState.Checked))
        return manual_peaks(self.variant.tau, self.variant.gamma, regions)

    def preview(self, *_):
        try:
            self.result_peaks = self.read()
            from dataclasses import replace
            self.plot.show_spectrum(self.raw, replace(self.variant, peaks=self.result_peaks))
            self.total.setText(f"Selected Rp = {sum(p.rp_ohm for p in self.result_peaks if p.included):.7g} Ohm")
        except ValueError as exc:
            self.total.setText(str(exc))

    def reset_auto(self):
        self.fill(detect_peaks(self.variant.tau, self.variant.gamma, self.variant.settings)[0])

    def add_marker(self):
        text, ok = QtW.QInputDialog.getText(self, "Add marker", "Frequency (Hz), scientific notation allowed:")
        if not ok:
            return
        try:
            f = float(text)
            if not np.isfinite(f) or f <= 0:
                raise ValueError("Frequency must be positive and finite.")
            center = 1/(2*np.pi*f)
            tau = self.variant.tau
            if not tau[0] < center < tau[-1]:
                raise ValueError("Marker must be inside the DRT window.")
            old = self.read()
            if any(np.isclose(np.log(center), np.log(p.tau_s), atol=1e-8, rtol=0) for p in old):
                raise ValueError("A marker already exists at this frequency.")
            centers = sorted([(p.tau_s, p.included) for p in old] + [(center, True)])
            bounds = [float(tau[0])] + [float(np.sqrt(a[0]*b[0])) for a, b in zip(centers, centers[1:])] + [float(tau[-1])]
            self.fill(manual_peaks(tau, self.variant.gamma,
                [(c, bounds[i], bounds[i+1], included) for i, (c, included) in enumerate(centers)]))
        except ValueError as exc:
            QtW.QMessageBox.warning(self, "Invalid marker", str(exc))

    def accept(self):
        try:
            self.result_peaks = self.read()
        except ValueError as exc:
            QtW.QMessageBox.warning(self, "Invalid peak regions", str(exc))
            return
        super().accept()
