from PySide6 import QtWidgets as QtW

PLOT_TYPES = ("Nyquist", "DRT", "Bode_modulus", "Bode_phase", "DRT_residuals", "LinKK_residuals")


class ExportDialog(QtW.QDialog):
    def __init__(self, total, selected, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export results and PNG plots")
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(QtW.QLabel("Exports the current analysis variant of each spectrum."))
        self.scope = QtW.QComboBox()
        self.scope.addItems([f"All calculated spectra ({total})", f"Selected calculated spectra ({selected})"])
        layout.addWidget(self.scope)
        self.xlsx = QtW.QCheckBox("Excel workbook (.xlsx)")
        self.xlsx.setChecked(True)
        self.txt = QtW.QCheckBox("Tab-separated tables (.txt)")
        layout.addWidget(self.xlsx)
        layout.addWidget(self.txt)
        layout.addWidget(QtW.QLabel("Separate PNG plots for every exported spectrum:"))
        self.plots = {}
        for name in PLOT_TYPES:
            box = QtW.QCheckBox(name.replace("_", " "))
            box.setChecked(name in ("Nyquist", "DRT"))
            self.plots[name] = box
            layout.addWidget(box)
        buttons = QtW.QDialogButtonBox(QtW.QDialogButtonBox.StandardButton.Save | QtW.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def plot_types(self):
        return [name for name, box in self.plots.items() if box.isChecked()]
