"""Batch export of immutable current variants; Qt plotting runs on the GUI thread."""
import re
from pathlib import Path
from PySide6 import QtCore, QtWidgets as QtW
from .tables import export_xlsx, export_txt_bundle
from .plots import export_plot
from ..ui.plots import SpectrumPlots
from ..ui.export_dialog import PLOT_TYPES


def export_batch(directory, pairs, *, xlsx=True, txt=False, plot_types=("Nyquist", "DRT"), progress=None):
    pairs = list(pairs)
    if not pairs:
        raise ValueError("No calculated spectra to export.")
    if set(plot_types)-set(PLOT_TYPES):
        raise ValueError("Unknown plot type.")
    if not (xlsx or txt or plot_types):
        raise ValueError("Choose at least one table format or plot type.")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    if xlsx:
        export_xlsx(directory/"results.xlsx", pairs)
    if txt:
        export_txt_bundle(directory/"txt", pairs)
    if not plot_types:
        return
    plots = SpectrumPlots()
    plots.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    plots.resize(1000, 750)
    plots.show()
    try:
        plot_dir = directory/"plots"
        plot_dir.mkdir()
        for index, (raw, variant) in enumerate(pairs, 1):
            plots.show_spectrum(raw, variant)
            stem = re.sub(r'[<>:"/\\|?*]', "_", Path(raw.name).stem)[:70]
            widgets = {"Nyquist": (0, plots.nyquist), "Bode_modulus": (1, plots.magnitude),
                       "Bode_phase": (1, plots.phase), "DRT": (2, plots.drt),
                       "DRT_residuals": (3, plots.residual), "LinKK_residuals": (3, plots.kk_residual)}
            for name in plot_types:
                tab, widget = widgets[name]
                plots.tabs.setCurrentIndex(tab)
                QtW.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                item = widget.plotItem
                item.setTitle(f"{raw.name} · {name.replace('_', ' ')}")
                export_plot(item, plot_dir/f"{index:03d}_{stem}_{name}.png")
            if progress:
                progress(index, len(pairs))
    finally:
        plots.close()
        plots.deleteLater()
