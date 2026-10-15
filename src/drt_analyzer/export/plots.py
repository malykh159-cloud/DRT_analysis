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
    if path.suffix.lower() != ".png":
        raise ValueError("Plot export supports PNG.")
    exporter = ImageExporter(item)
    exporter.parameters()["width"] = width
    exporter.export(str(path))
