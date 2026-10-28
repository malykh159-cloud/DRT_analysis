from dataclasses import replace
from PySide6 import QtCore, QtGui, QtWidgets as QtW
from ..drt.base import AnalysisSettings
from ..drt.rbf import RBF_NAMES
from .parameter_help import add_parameter
from .bayesian_panel import BayesianPanel
from .collapsible_section import CollapsibleSection


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
        self._loading = False
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.mode = QtW.QLabel("MANUAL · editable settings")
        self.mode.setStyleSheet("font-weight: 600; color: #225e79;")
        layout.addWidget(self.mode)

        self.sections = {}
        def section(title):
            if title in {"FREQUENCY RANGE", "VALIDATION", "PEAKS"}:
                folded = CollapsibleSection(title)
                self.sections[title] = folded
                layout.addWidget(folded)
                return folded.form
            group = QtW.QGroupBox(title)
            form = QtW.QFormLayout(group)
            form.setFieldGrowthPolicy(QtW.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            layout.addWidget(group)
            return form

        form = section("METHOD")
        method = self.method = combo(["Tikhonov", "Bayesian DRT"])
        add_parameter(form, "DRT", method, "method")
        positive = QtW.QLabel("γ(τ) ≥ 0 · separate series L")
        form.addRow(positive)

        form = section("FREQUENCY RANGE")
        self.frequency_range = QtW.QCheckBox("Use manual frequency range")
        self.frequency_min = QtW.QLineEdit("0.01")
        self.frequency_max = QtW.QLineEdit("100000")
        add_parameter(form, "", self.frequency_range, "frequency_range")
        add_parameter(form, "f min (Hz)", self.frequency_min, "frequency_min")
        add_parameter(form, "f max (Hz)", self.frequency_max, "frequency_max")
        self.source_range = QtW.QLabel("Source range: —")
        self.source_range.setWordWrap(True)
        form.addRow(self.source_range)

        form = section("REGULARIZATION")
        self.lambda_method = combo(["Manual", "GCV", "mGCV", "rGCV", "L-curve", "k-fold"],
            "GCV: prediction score from a linear smoother. mGCV inflates effective degrees of freedom; "
            "rGCV reduces undersmoothing risk. These use an unconstrained surrogate. L-curve: constrained "
            "residual/smoothness corner. k-fold: paired complex frequency holdouts, fixed seed.")
        add_parameter(form, "λ method", self.lambda_method, "lambda_method")
        self.lambda_value = QtW.QLineEdit("0.001")
        self.lambda_value.setToolTip("Regularization strength in ||W(Ax−z)||² + λ||Rx||². "
            "Smaller λ permits detail and noise; larger λ penalizes structure more strongly. Enter e.g. 1e-3.")
        add_parameter(form, "Manual λ", self.lambda_value, "lambda_value")
        self.actual_lambda = QtW.QLabel("—")
        form.addRow("Actual λ", self.actual_lambda)
        self.regularization_advanced = CollapsibleSection("Advanced")
        form.addRow(self.regularization_advanced)
        form = self.regularization_advanced.form
        self.order = combo(["0", "1", "2"], "Penalty is ∫|dⁿγ/d(ln τ)ⁿ|² d ln τ. "
                           "0 penalizes magnitude, 1 slope, 2 curvature. Rs and L are unpenalized.")
        add_parameter(form, "Derivative order", self.order, "derivative_order")
        self.scan_min = spin(-14, 7, -6, 1, 1)
        self.scan_max = spin(-13, 8, 2, 1, 1)
        self.scan_count = QtW.QSpinBox()
        self.scan_count.setRange(7, 201)
        self.scan_count.setValue(41)
        add_parameter(form, "Scan log₁₀ λ min", self.scan_min, "scan_min")
        add_parameter(form, "Scan log₁₀ λ max", self.scan_max, "scan_max")
        add_parameter(form, "Scan values", self.scan_count, "scan_count")

        self.bayesian = BayesianPanel()
        layout.addWidget(self.bayesian)
        self.method.currentTextChanged.connect(lambda text: self.bayesian.setVisible(text == "Bayesian DRT"))
        self.bayesian.changed.connect(self._edited)
        self.method.activated.connect(self._edited)
        form = section("RBF")
        self.rbf = combo(RBF_NAMES, "Positive radial basis functions in ln τ. "
                         "Choice affects resolution and smoothness; compare stability across bases.")
        self.shape_mode = combo(["Auto", "Manual"])
        self.shape = spin(.05, 100, 6, 6)
        self.shape.setToolTip("ε scales distance in ln τ: larger ε gives narrower basis functions. "
                             "Auto: full width at half maximum equals one center spacing.")
        add_parameter(form, "Basis", self.rbf, "rbf")
        add_parameter(form, "Shape mode", self.shape_mode, "shape_mode")
        add_parameter(form, "Manual ε", self.shape, "shape_value")
        self.actual_shape = QtW.QLabel("—")
        self.actual_shape.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Actual ε", self.actual_shape)

        form = section("VALIDATION")
        self.validation = QtW.QCheckBox("Run Lin-KK before DRT")
        self.validation.setChecked(True)
        self.validation.setToolTip("Compatibility diagnostic, not proof of linearity or stationarity. "
                                  "A review result does not block DRT or remove samples.")
        add_parameter(form, "", self.validation, "validation")
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
        add_parameter(form, "μ cutoff", self.kk_mu, "kk_mu")
        add_parameter(form, "RMS review (%)", self.kk_rms, "kk_rms")
        add_parameter(form, "Max RC elements", self.kk_max, "kk_max")
        add_parameter(form, "Min RC / decade", self.kk_density, "kk_density")
        add_parameter(form, "", self.kk_cap, "kk_cap")

        form = section("PEAKS")
        self.prominence = spin(.1, 99, 3, 2, .5)
        self.prominence.setToolTip("Minimum prominence as % of maximum γ. "
                                   "Peak areas partition the entire measured-window DRT at local valleys.")
        self.distance = spin(0, 2, .15, 2, .05)
        add_parameter(form, "Prominence (%)", self.prominence, "peak_prominence")
        add_parameter(form, "Min distance (dec)", self.distance, "peak_distance")
        layout.addStretch()
        self.lambda_value.textEdited.connect(self._manual_lambda)
        self.shape.valueChanged.connect(self._manual_shape)
        self.frequency_min.textEdited.connect(self._manual_range)
        self.frequency_max.textEdited.connect(self._manual_range)
        for control in (self.lambda_method, self.order, self.rbf, self.shape_mode):
            control.activated.connect(self._edited)
        for control in (self.scan_min, self.scan_max, self.scan_count, self.kk_mu,
                        self.kk_rms, self.kk_max, self.kk_density, self.prominence, self.distance):
            control.valueChanged.connect(self._edited)
        for control in (self.validation, self.kk_cap, self.frequency_range):
            control.clicked.connect(self._edited)
        self.load(self._base)

    def _edited(self, *_):
        if not self._loading:
            self.mode.setText("MANUAL · settings changed")

    def _manual_lambda(self, *_):
        if not self._loading:
            self.lambda_method.setCurrentText("Manual")
            self._edited()

    def _manual_shape(self, *_):
        if not self._loading:
            self.shape_mode.setCurrentText("Manual")
            self._edited()

    def _manual_range(self, *_):
        if not self._loading:
            self.frequency_range.setChecked(True)
            self._edited()

    def set_source_range(self, raw):
        if raw is None:
            self.source_range.setText("Source range: —")
            return
        lower, upper = float(raw.frequency.min()), float(raw.frequency.max())
        self.source_range.setText(f"Source: {lower:.7g} … {upper:.7g} Hz · {len(raw.frequency)} points")
        if self._base.frequency_min_hz is None:
            self.frequency_min.setText(repr(lower))
        if self._base.frequency_max_hz is None:
            self.frequency_max.setText(repr(upper))

    def value(self):
        try:
            lam = float(self.lambda_value.text().replace(",", "."))
        except ValueError as exc:
            raise ValueError("Manual λ must be a number, e.g. 1e-3.") from exc
        lower = upper = None
        if self.frequency_range.isChecked():
            try:
                lower = float(self.frequency_min.text().replace(",", "."))
                upper = float(self.frequency_max.text().replace(",", "."))
            except ValueError as exc:
                raise ValueError("Frequency bounds must be numbers in Hz, e.g. 0.1 and 1e5.") from exc
        settings = replace(self._base, mode="Manual", method=self.method.currentText(), bayesian=self.bayesian.value(), lambda_method=self.lambda_method.currentText(), lambda_value=lam,
            lambda_min_exp=self.scan_min.value(), lambda_max_exp=self.scan_max.value(), lambda_count=self.scan_count.value(),
            rbf=self.rbf.currentText(), shape_mode=self.shape_mode.currentText(), shape_value=self.shape.value(),
            derivative_order=int(self.order.currentText()), validation=self.validation.isChecked(),
            kk_mu=self.kk_mu.value(), kk_max_elements=self.kk_max.value(), kk_min_per_decade=self.kk_density.value(),
            kk_tolerance=self.kk_rms.value()/100, kk_add_capacitance=self.kk_cap.isChecked(),
            peak_prominence=self.prominence.value()/100, peak_distance_decades=self.distance.value(),
            frequency_min_hz=lower, frequency_max_hz=upper)
        settings.validate()
        return settings

    def load(self, settings, actual=None):
        self._loading = True
        self._base = settings
        self.method.setCurrentText(settings.method)
        self.bayesian.setVisible(settings.method == "Bayesian DRT")
        self.bayesian.load(settings.bayesian, actual.uncertainty if actual else None)
        self.frequency_range.setChecked(settings.frequency_min_hz is not None or settings.frequency_max_hz is not None)
        if settings.frequency_min_hz is not None:
            self.frequency_min.setText(repr(settings.frequency_min_hz))
        if settings.frequency_max_hz is not None:
            self.frequency_max.setText(repr(settings.frequency_max_hz))
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
        self.shape.setValue(actual.shape_value if actual and settings.shape_mode == "Auto" else settings.shape_value)
        self.actual_shape.setText(f"{actual.shape_value:.7g}" if actual else "calculated from grid")
        self.validation.setChecked(settings.validation)
        self.kk_mu.setValue(settings.kk_mu)
        self.kk_rms.setValue(100*settings.kk_tolerance)
        self.kk_max.setValue(settings.kk_max_elements)
        self.kk_density.setValue(settings.kk_min_per_decade)
        self.kk_cap.setChecked(settings.kk_add_capacitance)
        self.prominence.setValue(100*settings.peak_prominence)
        self.distance.setValue(settings.peak_distance_decades)
        self._loading = False
