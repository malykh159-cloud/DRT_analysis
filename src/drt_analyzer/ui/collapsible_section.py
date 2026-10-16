from PySide6 import QtCore, QtWidgets as QtW


class CollapsibleSection(QtW.QWidget):
    """A display-only fold: hidden controls retain their values and stay enabled."""

    def __init__(self, title, parent=None, expanded=False):
        super().__init__(parent)
        self.setSizePolicy(QtW.QSizePolicy.Policy.Preferred, QtW.QSizePolicy.Policy.Maximum)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.toggle = QtW.QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setToolTip("Развернуть / свернуть настройки. Сворачивание не отключает их действие.")
        self.toggle.setAccessibleName("Развернуть / свернуть "+title)
        layout.addWidget(self.toggle)
        self.content = QtW.QWidget()
        self.form = QtW.QFormLayout(self.content)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setFieldGrowthPolicy(QtW.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(self.content)
        self.toggle.toggled.connect(self.set_expanded)
        self.toggle.setChecked(expanded)
        self.set_expanded(expanded)

    def set_expanded(self, expanded):
        if self.toggle.isChecked() != expanded:
            self.toggle.setChecked(expanded)
        self.content.setVisible(expanded)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)
