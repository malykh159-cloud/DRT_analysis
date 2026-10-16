from PySide6 import QtCore, QtWidgets as QtW
from ..drt.base import BayesianSettings
from .parameter_help import add_parameter


class BayesianPanel(QtW.QGroupBox):
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("BAYESIAN", parent)
        form = QtW.QFormLayout(self)
        self.controls = {}
        defaults = BayesianSettings()
        def integer(name, label, lo, hi, tip, target=form):
            box = QtW.QSpinBox()
            box.setRange(lo, hi)
            box.setValue(getattr(defaults, name))
            box.setToolTip(tip)
            box.valueChanged.connect(lambda *_: self.changed.emit())
            self.controls[name] = box
            add_parameter(target, label, box, "bayesian_"+name)
        def real(name, label, lo, hi, decimals, tip, target=form):
            box = QtW.QDoubleSpinBox()
            box.setRange(lo, hi)
            box.setDecimals(decimals)
            box.setValue(getattr(defaults, name))
            box.setToolTip(tip)
            box.valueChanged.connect(lambda *_: self.changed.emit())
            self.controls[name] = box
            add_parameter(target, label, box, "bayesian_"+name)
            return box
        integer("warmup", "Warm-up", 0, 100000, "Начальные итерации каждой цепочки, отбрасываемые до расчёта posterior. Exact HMC не требует адаптации шага.")
        integer("samples", "Samples / chain", 20, 100000, "Число сохраняемых posterior samples ПОСЛЕ warm-up в каждой цепочке. Увеличьте при низком ESS.")
        integer("chains", "Chains", 1, 16, "Независимые цепочки. Рекомендуется 4; при одной цепочке межцепочечный R-hat недоступен.")
        integer("seed", "Random seed", 0, 2147483647, "SeedSequence создаёт независимые воспроизводимые потоки случайных чисел для цепочек.")
        real("credible_interval", "Credible interval (%)", 50, 99.99, 2, "Центральный поточечный Bayesian интервал γ(τ); не одновременная область и не неопределённость выбора модели.")
        self.advanced_toggle = QtW.QToolButton()
        self.advanced_toggle.setText("Advanced")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        form.addRow(self.advanced_toggle)
        self.advanced = QtW.QWidget()
        advanced = QtW.QFormLayout(self.advanced)
        advanced.setContentsMargins(0, 0, 0, 0)
        sigma = real("noise_sigma", "Noise σ", 0, 1, 8,
            "0 = Auto: std остатков MAP в нормированных координатах с весами 1/|Z|. Положительное значение фиксирует σ; 0.01 примерно соответствует 1% шуму компоненты.", advanced)
        sigma.setSpecialValueText("Auto (residuals)")
        real("noise_floor", "Auto σ floor", 1e-12, .1, 12,
             "Нижний предел Auto σ в нормированных координатах. Укажите известный шум измерений, если он доступен; остатки включают ошибку модели.", advanced)
        real("trajectory_time", "Trajectory time", .05, 3, 16,
             "Длина точной гармонической траектории HMC в whitened coordinates. По умолчанию π/2 как в pyDRTtools. Leapfrog step отсутствует.", advanced)
        integer("max_reflections", "Max reflections", 10, 100000,
                "Предохранитель числа отражений за переход. При превышении сохраняется предыдущая точка и выдаётся numerical warning.", advanced)
        self.actual = QtW.QLabel("Actual σ: —")
        self.actual.setWordWrap(True)
        advanced.addRow(self.actual)
        form.addRow(self.advanced)
        self.advanced.hide()
        self.advanced_toggle.toggled.connect(self.toggle_advanced)

    def toggle_advanced(self, visible):
        self.advanced.setVisible(visible)
        self.advanced_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if visible else QtCore.Qt.ArrowType.RightArrow)

    def value(self):
        settings = BayesianSettings(**{name: box.value() for name, box in self.controls.items()})
        settings.validate()
        return settings

    def load(self, settings, actual=None):
        for name, box in self.controls.items():
            box.setValue(getattr(settings, name))
        self.actual.setText(f"Actual weighted σ: {actual.noise_sigma:.8g}" if actual else "Actual σ: —")
