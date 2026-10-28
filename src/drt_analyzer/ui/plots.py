import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets as QtW
from .plot_hover import FrequencyHover
from .parameter_help import help_button

COLORS = ["#196e9b", "#c75b30", "#288365", "#8a5da8", "#bd8b24", "#487a89", "#a14765", "#6d7a31"]
pg.setConfigOptions(background="w", foreground="#293743", antialias=True)


def plot(title, xlabel, ylabel, xunits=None, yunits=None, logx=False):
    widget = pg.PlotWidget(title=title)
    item = widget.getPlotItem()
    item.setLabel("bottom", xlabel, units=xunits)
    item.setLabel("left", ylabel, units=yunits)
    item.showGrid(x=True, y=True, alpha=.17)
    item.setLogMode(x=logx)
    item.addLegend(offset=(8, 8), labelTextSize="9pt")
    return widget


def line(widget, x, y, name, color, symbol=None, dashed=False):
    pen = pg.mkPen(color, width=1.8, style=QtCore.Qt.PenStyle.DashLine if dashed else QtCore.Qt.PenStyle.SolidLine)
    return widget.plot(x, y, name=name, pen=None if symbol else pen, symbol=symbol,
                       symbolSize=5, symbolBrush=color, symbolPen=None)


class SpectrumPlots(QtW.QWidget):
    peak_selected = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw = self.variant = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        axisbar = QtW.QHBoxLayout()
        axisbar.addWidget(QtW.QLabel("DRT horizontal axis"))
        self.axis = QtW.QComboBox()
        self.axis.addItems(["τ (s)", "Frequency (Hz)"])
        axisbar.addWidget(self.axis)
        axisbar.addWidget(help_button("drt_axis", self))
        axisbar.addStretch()
        layout.addLayout(axisbar)
        self.cursor_readout = QtW.QLabel("Наведите курсор на график: частота и ближайшая точка появятся здесь.")
        self.cursor_readout.setWordWrap(True)
        self.cursor_readout.setMinimumHeight(34)
        self.cursor_readout.setStyleSheet("color: #225e79; padding: 2px 5px;")
        layout.addWidget(self.cursor_readout)
        self.tabs = QtW.QTabWidget()
        layout.addWidget(self.tabs)
        self.nyquist = plot("Nyquist", "Re(Z)", "−Im(Z)", "Ω", "Ω")
        self.nyquist.setAspectLocked(True)
        self.tabs.addTab(self.nyquist, "Nyquist")
        bode = QtW.QWidget()
        bl = QtW.QVBoxLayout(bode)
        self.magnitude = plot("Bode modulus", "Frequency", "|Z|", "Hz", "Ω", True)
        self.magnitude.setLogMode(y=True)
        self.phase = plot("Bode phase", "Frequency", "Phase(Z)", "Hz", "°", True)
        bl.addWidget(self.magnitude)
        bl.addWidget(self.phase)
        self.tabs.addTab(bode, "Bode")
        self.drt = plot("Distribution of relaxation times", "τ", "γ", "s", "Ω", True)
        self.tabs.addTab(self.drt, "DRT")
        residual = QtW.QWidget()
        rl = QtW.QVBoxLayout(residual)
        self.residual = plot("DRT residuals (observed − fit) / |observed|", "Frequency", "Residual", "Hz", "%", True)
        self.kk_residual = plot("Lin-KK residuals (observed − fit) / |observed|", "Frequency", "Residual", "Hz", "%", True)
        rl.addWidget(self.residual)
        rl.addWidget(self.kk_residual)
        self.tabs.addTab(residual, "Residuals / KK")
        self.comparison = plot("Selected spectra · DRT comparison", "τ", "γ", "s", "Ω", True)
        self.tabs.addTab(self.comparison, "Compare DRT")
        self.axis.currentIndexChanged.connect(self._axis_changed)
        self._pairs = []
        self.hovers = {
            self.nyquist: FrequencyHover(self.nyquist, self.cursor_readout, "nyquist"),
            self.magnitude: FrequencyHover(self.magnitude, self.cursor_readout, log_y=True, value_label="|Z| (Ω)"),
            self.phase: FrequencyHover(self.phase, self.cursor_readout, value_label="Phase (°)"),
            self.drt: FrequencyHover(self.drt, self.cursor_readout, "tau", value_label="γ (Ω)"),
            self.residual: FrequencyHover(self.residual, self.cursor_readout, value_label="Residual (%)"),
            self.kk_residual: FrequencyHover(self.kk_residual, self.cursor_readout, value_label="KK residual (%)"),
            self.comparison: FrequencyHover(self.comparison, self.cursor_readout, "tau", value_label="γ (Ω)"),
        }

    def _axis_changed(self):
        self.show_spectrum(self.raw, self.variant)
        self.compare(self._pairs, switch=False)

    def clear_plot(self, widget):
        widget.clear()
        self.hovers[widget].clear()
        if widget.plotItem.legend:
            widget.plotItem.legend.clear()

    def show_spectrum(self, raw, variant=None):
        self.raw, self.variant = raw, variant
        for widget in (self.nyquist, self.magnitude, self.phase, self.drt, self.residual, self.kk_residual):
            self.clear_plot(widget)
        if raw is None:
            return
        f, z = raw.frequency, raw.impedance
        nyquist = line(self.nyquist, z.real, -z.imag, "Experimental", COLORS[0], "o")
        details = np.full(len(f), "Experimental", dtype=object)
        excluded = np.asarray(variant.preprocessing["excluded_indices"], dtype=int) if variant else np.array([], dtype=int)
        if len(excluded):
            details[excluded] = "Outside analysis range"
        self.hovers[self.nyquist].add_curve(nyquist, z.real, -z.imag, f, "Experimental", details)
        magnitude = line(self.magnitude, f, np.abs(z), "Experimental", COLORS[0], "o")
        phase = line(self.phase, f, np.angle(z, deg=True), "Experimental", COLORS[0], "o")
        self.hovers[self.magnitude].add_curve(magnitude, f, np.abs(z), f, "Experimental")
        self.hovers[self.phase].add_curve(phase, f, np.angle(z, deg=True), f, "Experimental")
        if len(excluded):
            line(self.nyquist, z.real[excluded], -z.imag[excluded], "Outside analysis range", "#aeb8bf", "o")
            line(self.magnitude, f[excluded], np.abs(z[excluded]), "Outside analysis range", "#aeb8bf", "o")
            line(self.phase, f[excluded], np.angle(z[excluded], deg=True), "Outside analysis range", "#aeb8bf", "o")
        if variant is None:
            return
        v = variant
        line(self.nyquist, v.reconstructed.real, -v.reconstructed.imag, "DRT reconstruction", COLORS[1])
        for widget, values, name, color in (
                (self.magnitude, np.abs(v.reconstructed), "DRT reconstruction", COLORS[1]),
                (self.phase, np.angle(v.reconstructed, deg=True), "DRT reconstruction", COLORS[1]),
                (self.residual, 100*v.residuals.real, "Re", COLORS[0]),
                (self.residual, 100*v.residuals.imag, "Im", COLORS[1])):
            curve = line(widget, v.frequency, values, name, color)
            self.hovers[widget].add_curve(curve, v.frequency, values, v.frequency, name)
        if v.kk:
            line(self.nyquist, v.kk.reconstructed.real, -v.kk.reconstructed.imag, "Lin-KK", COLORS[2], dashed=True)
            for values, name, color in ((100*v.kk.residuals.real, "Re", COLORS[0]),
                                         (100*v.kk.residuals.imag, "Im", COLORS[1])):
                curve = line(self.kk_residual, v.frequency, values, name, color)
                self.hovers[self.kk_residual].add_curve(curve, v.frequency, values, v.frequency, name)
        is_frequency = self.axis.currentIndex() == 1
        x = 1/(2*np.pi*v.tau) if is_frequency else v.tau
        self.hovers[self.drt].mode = "frequency" if is_frequency else "tau"
        self.drt.setLabel("bottom", "Frequency" if is_frequency else "τ", units="Hz" if is_frequency else "s")
        name = "Bayesian DRT — posterior mean" if v.uncertainty is not None else f"DRT · λ={v.lambda_value:.3g}"
        curve = line(self.drt, x, v.gamma, name, COLORS[0])
        if v.uncertainty is not None:
            # A single enclosed PlotDataItem follows both credible boundaries,
            # supports the existing log-axis transform and native legend samples.
            band = self.drt.plot(np.r_[x, x[::-1]],
                np.r_[v.uncertainty.credible_upper, v.uncertainty.credible_lower[::-1]],
                pen=None, fillLevel="enclosed", fillBrush=pg.mkBrush(25, 110, 155, 45),
                name=f"{v.uncertainty.credible_interval:g}% credible interval")
            band.setZValue(-1)
        self.hovers[self.drt].add_curve(curve, x, v.gamma, 1/(2*np.pi*v.tau), raw.name)
        if v.peaks:
            scatter = pg.ScatterPlotItem(
                # ScatterPlotItem has no setLogMode: supply view coordinates.
                x=[np.log10(p.frequency_hz if is_frequency else p.tau_s) for p in v.peaks],
                y=[p.gamma_ohm for p in v.peaks], data=list(v.peaks), size=10,
                brush=[COLORS[1] if p.included else "#999999" for p in v.peaks], pen="w", hoverable=True, hoverSize=13,
                tip=lambda x, y, data: f"Peak {data.index}{' (edge)' if data.edge else ''}\n"
                    f"τ = {data.tau_s:.6g} s\nf = {data.frequency_hz:.6g} Hz\n"
                    f"γ = {data.gamma_ohm:.6g} Ω\nRp = {data.rp_ohm:.6g} Ω ({100*data.fraction:.2f}%)")
            scatter.sigClicked.connect(lambda item, points, event: self.peak_selected.emit(points[0].data().index-1))
            self.drt.addItem(scatter)
        for widget in (self.nyquist, self.magnitude, self.phase, self.drt, self.residual, self.kk_residual):
            widget.enableAutoRange()

    def compare(self, pairs, switch=True):
        self._pairs = list(pairs)
        self.clear_plot(self.comparison)
        is_frequency = self.axis.currentIndex() == 1
        self.hovers[self.comparison].mode = "frequency" if is_frequency else "tau"
        self.comparison.setLabel("bottom", "Frequency" if is_frequency else "τ", units="Hz" if is_frequency else "s")
        for i, (raw, v) in enumerate(self._pairs):
            x = 1/(2*np.pi*v.tau) if is_frequency else v.tau
            curve = line(self.comparison, x, v.gamma, raw.name, COLORS[i % len(COLORS)])
            self.hovers[self.comparison].add_curve(curve, x, v.gamma, 1/(2*np.pi*v.tau), raw.name)
        self.comparison.enableAutoRange()
        if switch:
            self.tabs.setCurrentIndex(4)

    def active_plot(self):
        index = self.tabs.currentIndex()
        return [self.nyquist, self.magnitude, self.drt, self.residual, self.comparison][index].plotItem

    def all_plots(self):
        return {"Nyquist": self.nyquist.plotItem, "Bode_modulus": self.magnitude.plotItem,
                "Bode_phase": self.phase.plotItem, "DRT": self.drt.plotItem,
                "DRT_residuals": self.residual.plotItem, "LinKK_residuals": self.kk_residual.plotItem,
                "Comparison": self.comparison.plotItem}
