"""Cursor readouts in view coordinates, including logarithmic axes.

Nyquist has no frequency-valued x axis: use the nearest measured sample in
screen distance. Tau/frequency views have a continuous axis conversion.
"""
from dataclasses import dataclass
import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore


@dataclass
class HoverCurve:
    item: object
    x: np.ndarray
    y: np.ndarray
    frequency: np.ndarray
    label: str
    details: object = None


class FrequencyHover(QtCore.QObject):
    def __init__(self, widget, readout, mode="frequency", log_y=False, value_label=""):
        super().__init__(widget)
        self.widget, self.readout = widget, readout
        self.mode, self.log_y, self.value_label = mode, log_y, value_label
        self.curves = []
        self.cursor_frequency = None
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#7a8d99", style=QtCore.Qt.PenStyle.DashLine))
        self.marker = pg.ScatterPlotItem(size=9, pen=pg.mkPen("#334f60", width=1.5), brush=pg.mkBrush(255, 255, 255, 180))
        self.overlays = [self.vline, self.marker]
        for item in self.overlays:
            item.setZValue(100)
        self.attach()
        widget.plotItem._frequency_hover = self
        widget.scene().sigMouseMoved.connect(self.mouse_moved)
        widget.viewport().installEventFilter(self)
        widget.setMouseTracking(True)

    def attach(self):
        for item in self.overlays:
            self.widget.addItem(item, ignoreBounds=True)
            item.hide()

    def clear(self):
        self.curves.clear()
        self.hide()
        self.attach()

    def hide(self):
        for item in self.overlays:
            item.hide()
        self.cursor_frequency = None
        if getattr(self.readout, "hover_owner", None) is self:
            self.readout.setText("Наведите курсор на график: частота и ближайшая точка появятся здесь.")
            self.readout.hover_owner = None
        self.widget.setToolTip("")

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Leave:
            self.hide()
        return False

    def add_curve(self, item, x, y, frequency, label, details=None):
        x, y, frequency = np.asarray(x), np.asarray(y), np.asarray(frequency)
        view_x = x if self.mode == "nyquist" else np.log10(x)
        view_y = np.log10(y) if self.log_y else y
        finite = np.isfinite(view_x) & np.isfinite(view_y) & np.isfinite(frequency)
        if finite.any():
            self.curves.append(HoverCurve(item, view_x[finite], view_y[finite], frequency[finite], label,
                                          np.asarray(details)[finite] if details is not None else None))

    def mouse_moved(self, position):
        view = self.widget.plotItem.vb
        if not view.sceneBoundingRect().contains(position):
            self.hide()
            return
        point = view.mapSceneToView(position)
        x, y = float(point.x()), float(point.y())
        if not np.isfinite([x, y]).all():
            self.hide()
            return
        visible = [curve for curve in self.curves if curve.item.isVisible()]
        if not visible:
            self.hide()
            return
        if self.mode == "nyquist":
            rect = view.sceneBoundingRect()
            ranges = view.viewRange()
            sx = rect.width()/max(ranges[0][1]-ranges[0][0], 1e-300)
            sy = rect.height()/max(ranges[1][1]-ranges[1][0], 1e-300)
            nearest = None
            for curve in visible:
                distances = ((curve.x-x)*sx)**2+((curve.y-y)*sy)**2
                index = int(np.argmin(distances))
                if nearest is None or distances[index] < nearest[0]:
                    nearest = (distances[index], curve, index)
            _, curve, index = nearest
            frequency = float(curve.frequency[index])
            mx, my = float(curve.x[index]), float(curve.y[index])
            label = str(curve.details[index]) if curve.details is not None else curve.label
            text = f"Ближайшая точка · f = {frequency:.7g} Hz · Re = {mx:.7g} Ω · −Im = {my:.7g} Ω · {label}"
            self.vline.hide()
        else:
            # Avoid overflow when the user zooms far beyond the data.
            if not -300 < x < 300:
                self.hide()
                return
            axis_value = 10.**x
            frequency = 1/(2*np.pi*axis_value) if self.mode == "tau" else axis_value
            tau = 1/(2*np.pi*frequency)
            text = f"Курсор · f = {frequency:.7g} Hz · τ = {tau:.7g} s"
            nearest = None
            for curve in visible:
                order = np.argsort(curve.x)
                if not curve.x[order[0]] <= x <= curve.x[order[-1]]:
                    continue
                interpolated = float(np.interp(x, curve.x[order], curve.y[order]))
                distance = abs(interpolated-y)
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, curve, interpolated)
            self.vline.setPos(x)
            self.vline.show()
            if nearest is None:
                self.marker.hide()
                text += " · вне диапазона кривых"
                self._publish(text, frequency)
                return
            _, curve, my = nearest
            mx = x
            value = 10.**my if self.log_y else my
            text += f" · {self.value_label or 'y'} ≈ {value:.7g} · {curve.label}"
        self.marker.setData([mx], [my])
        self.marker.show()
        self._publish(text, frequency)

    def _publish(self, text, frequency):
        self.cursor_frequency = frequency
        self.readout.hover_owner = self
        self.readout.setText(text)
        self.widget.setToolTip(text)
