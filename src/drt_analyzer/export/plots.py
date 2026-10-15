from pathlib import Path


def export_plot(item, path, width=1800):
    hover = getattr(item, "_frequency_hover", None)
    overlays = [(overlay, overlay.isVisible()) for overlay in hover.overlays] if hover else []
    for overlay, _ in overlays:
        overlay.hide()
    try:
        _export_plot(item, path, width)
    finally:
        for overlay, visible in overlays:
            overlay.setVisible(visible)


def _export_plot(item, path, width):
    from pyqtgraph.exporters import ImageExporter
    path = Path(path)
    if path.suffix.lower() == ".svg":
        # Native Qt vector rendering avoids pyqtgraph 0.14 SVG path parsing,
        # which is incompatible with the path serialization in Qt 6.12.
        from PySide6 import QtCore, QtGui, QtSvg
        rect = item.sceneBoundingRect()
        height = max(1, round(width*rect.height()/max(rect.width(), 1)))
        generator = QtSvg.QSvgGenerator()
        generator.setFileName(str(path))
        generator.setSize(QtCore.QSize(width, height))
        generator.setViewBox(QtCore.QRect(0, 0, width, height))
        generator.setTitle("DRT Analyzer scientific plot")
        painter = QtGui.QPainter(generator)
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            target = QtCore.QRectF(0, 0, width, height)
            painter.fillRect(target, QtGui.QColor("white"))
            item.scene().render(painter, target, rect)
        finally:
            painter.end()
        return
    elif path.suffix.lower() == ".png":
        exporter = ImageExporter(item)
    else:
        raise ValueError("Plot export supports PNG or SVG.")
    exporter.parameters()["width"] = width
    exporter.export(str(path))
