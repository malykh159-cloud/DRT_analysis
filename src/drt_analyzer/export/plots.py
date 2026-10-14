from pathlib import Path


def export_plot(item, path, width=1800):
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
