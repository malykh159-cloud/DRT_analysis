from dataclasses import replace
from PySide6 import QtCore, QtGui, QtWidgets as QtW
from ..drt.base import AnalysisSettings
from ..drt.rbf import RBF_NAMES


def combo(items, tooltip=""):
    box = QtW.QComboBox()
    box.addItems(items)
    box.setToolTip(tooltip)
    return box


def spin(lo, hi, value, decimals=3, step=.1):
    box = QtW.QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setValue(value)
    box.setSingleStep(step)
    return box


class SettingsPanel(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._base = AnalysisSettings()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.mode = QtW.QLabel("MANUAL · editable settings")
        self.mode.setStyleSheet("font-weight: 600; color: #225e79;")
        layout.addWidget(self.mode)

        def section(title):
            group = QtW.QGroupBox(title)
            form = QtW.QFormLayout(group)
            form.setFieldGrowthPolicy(QtW.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            layout.addWidget(group)
            return form

        form = section("METHOD")
        method = combo(["Tikhonov", "Bayesian DRT — unavailable"])
        method.model().item(1).setEnabled(False)
        method.setItemData(1, "Reserved for a validated likelihood, prior and posterior sampler.", QtCore.Qt.ItemDataRole.ToolTipRole)
        form.addRow("DRT", method)
        positive = QtW.QLabel("γ(τ) ≥ 0 · separate series L")
        form.addRow(positive)

        form = section("REGULARIZATION")
        self.lambda_method = combo(["Manual", "GCV", "mGCV", "rGCV", "L-curve", "k-fold"],
            "GCV: prediction score from a linear smoother. mGCV inflates effective degrees of freedom; "
            "rGCV reduces undersmoothing risk. These use an unconstrained surrogate. L-curve: constrained "
            "residual/smoothness corner. k-fold: paired complex frequency holdouts, fixed seed.")
        form.addRow("λ method", self.lambda_method)
        self.lambda_value = QtW.QLineEdit("0.001")
        self.lambda_value.setToolTip("Regularization strength in ||W(Ax−z)||² + λ||Rx||². "
            "Smaller λ permits detail and noise; larger λ penalizes structure more strongly. Enter e.g. 1e-3.")
        form.addRow("Manual λ", self.lambda_value)
        self.actual_lambda = QtW.QLabel("—")
        form.addRow("Actual λ", self.actual_lambda)
        self.order = combo(["0", "1", "2"], "Penalty is ∫|dⁿγ/d(ln τ)ⁿ|² d ln τ. "
                           "0 penalizes magnitude, 1 slope, 2 curvature. Rs and L are unpenalized.")
        form.addRow("Derivative order", self.order)
        self.scan_min = spin(-14, 7, -8, 1, 1)
        self.scan_max = spin(-13, 8, 2, 1, 1)
        self.scan_count = QtW.QSpinBox()
        self.scan_count.setRange(7, 201)
        self.scan_count.setValue(41)
        form.addRow("Scan log₁₀ λ min", self.scan_min)
        form.addRow("Scan log₁₀ λ max", self.scan_max)
        form.addRow("Scan values", self.scan_count)

        form = section("RBF")
        self.rbf = combo(RBF_NAMES, "Positive radial basis functions in ln τ. "
                         "Choice affects resolution and smoothness; compare stability across bases.")
        self.shape_mode = combo(["Auto", "Manual"])
        self.shape = spin(.05, 100, 1, 6)
        self.shape.setToolTip("ε scales distance in ln τ: larger ε gives narrower basis functions. "
                             "Auto: full width at half maximum equals one center spacing.")
        form.addRow("Basis", self.rbf)
        form.addRow("Shape mode", self.shape_mode)
        form.addRow("Manual ε", self.shape)
        self.actual_shape = QtW.QLabel("—")
        self.actual_shape.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Actual ε", self.actual_shape)

        form = section("VALIDATION")
        self.validation = QtW.QCheckBox("Run Lin-KK before DRT")
        self.validation.setChecked(True)
        self.validation.setToolTip("Compatibility diagnostic, not proof of linearity or stationarity. "
                                  "A review result does not block DRT or remove samples.")
        form.addRow(self.validation)
        self.kk_mu = spin(.01, .99, .85, 2, .05)
        self.kk_rms = spin(.01, 50, 2, 2, .25)
        self.kk_max = QtW.QSpinBox()
        self.kk_max.setRange(3, 100)
        self.kk_max.setValue(50)
        self.kk_density = spin(.1, 10, 3., 1, .5)
        self.kk_density.setToolTip("Application resolution guard before μ stopping: minimum RC elements "
                                   "per measured frequency decade. Heuristic; standard μ alone can stop too early for narrow RC peaks.")
        self.kk_cap = QtW.QCheckBox("Include series capacitance in KK")
        self.kk_cap.setChecked(True)
        form.addRow("μ cutoff", self.kk_mu)
        form.addRow("RMS review (%)", self.kk_rms)
        form.addRow("Max RC elements", self.kk_max)
        form.addRow("Min RC / decade", self.kk_density)
        form.addRow(self.kk_cap)

        form = section("PEAKS")
        self.prominence = spin(.1, 99, 3, 2, .5)
        self.prominence.setToolTip("Minimum prominence as % of maximum γ. "
                                   "Peak areas partition the entire measured-window DRT at local valleys.")
        self.distance = spin(0, 2, .15, 2, .05)
        form.addRow("Prominence (%)", self.prominence)
        form.addRow("Min distance (dec)", self.distance)
        layout.addStretch()
        self.lambda_method.currentTextChanged.connect(self._availability)
        self.shape_mode.currentTextChanged.connect(self._availability)
        self.load(self._base)

    def _availability(self, *_):
        self.lambda_value.setEnabled(self.lambda_method.currentText() == "Manual")
        self.shape.setEnabled(self.shape_mode.currentText() == "Manual")

    def value(self):
        try:
            lam = float(self.lambda_value.text())
        except ValueError as exc:
            raise ValueError("Manual λ must be a number, e.g. 1e-3.") from exc
        settings = replace(self._base, mode="Manual", lambda_method=self.lambda_method.currentText(), lambda_value=lam,
            lambda_min_exp=self.scan_min.value(), lambda_max_exp=self.scan_max.value(), lambda_count=self.scan_count.value(),
            rbf=self.rbf.currentText(), shape_mode=self.shape_mode.currentText(), shape_value=self.shape.value(),
            derivative_order=int(self.order.currentText()), validation=self.validation.isChecked(),
            kk_mu=self.kk_mu.value(), kk_max_elements=self.kk_max.value(), kk_min_per_decade=self.kk_density.value(),
            kk_tolerance=self.kk_rms.value()/100, kk_add_capacitance=self.kk_cap.isChecked(),
            peak_prominence=self.prominence.value()/100, peak_distance_decades=self.distance.value())
        settings.validate()
        return settings

    def load(self, settings, actual=None):
        self._base = settings
        self.mode.setText(f"{settings.mode.upper()} result → editable Manual" if actual else "MANUAL · editable settings")
        self.lambda_method.setCurrentText(settings.lambda_method)
        self.lambda_value.setText(f"{settings.lambda_value:.10g}")
        self.actual_lambda.setText(f"{actual.lambda_value:.9g}" if actual else "—")
        self.scan_min.setValue(settings.lambda_min_exp)
        self.scan_max.setValue(settings.lambda_max_exp)
        self.scan_count.setValue(settings.lambda_count)
        self.order.setCurrentText(str(settings.derivative_order))
        self.rbf.setCurrentText(settings.rbf)
        self.shape_mode.setCurrentText(settings.shape_mode)
        self.shape.setValue(settings.shape_value)
        self.actual_shape.setText(f"{actual.shape_value:.7g}" if actual else "calculated from grid")
        self.validation.setChecked(settings.validation)
        self.kk_mu.setValue(settings.kk_mu)
        self.kk_rms.setValue(100*settings.kk_tolerance)
        self.kk_max.setValue(settings.kk_max_elements)
        self.kk_density.setValue(settings.kk_min_per_decade)
        self.kk_cap.setChecked(settings.kk_add_capacitance)
        self.prominence.setValue(100*settings.peak_prominence)
        self.distance.setValue(settings.peak_distance_decades)
        self._availability()
