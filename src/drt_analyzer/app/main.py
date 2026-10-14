import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="DRT Analyzer desktop application")
    parser.add_argument("files", nargs="*", help="EIS TXT/CSV/XLSX files")
    parser.add_argument("--smoke-test", action="store_true", help="Run a synthetic GUI/export check and exit")
    parser.add_argument("--output", default="artifacts/smoke", help="Smoke test artifact directory")
    args = parser.parse_args(argv)
    # Small dense inversions are faster and responsive with one BLAS thread.
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    if args.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets as QtW
    from .main_window import MainWindow
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
    log_dir = root/"logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir/"drt_analyzer.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = QtW.QApplication.instance() or QtW.QApplication(sys.argv[:1])
    # The Windows offscreen plugin does not enumerate system fonts. Load a
    # system font explicitly so automated scientific exports contain real text.
    if not QtGui.QFontDatabase.families():
        fonts = Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts"
        for name in ("segoeui.ttf", "arial.ttf"):
            if (fonts/name).exists():
                QtGui.QFontDatabase.addApplicationFont(str(fonts/name))
    app.setFont(QtGui.QFont("Segoe UI", 9))
    app.setApplicationName("DRT Analyzer")
    app.setStyle("Fusion")
    app.setStyleSheet("QMainWindow { background: #f5f7f9; } QGroupBox { font-weight: 600; "
        "border: 1px solid #ccd5dd; border-radius: 3px; margin-top: 10px; padding-top: 10px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; } "
        "QToolBar { spacing: 5px; padding: 5px; } QTableWidget { gridline-color: #e2e7eb; } "
        "QHeaderView::section { background: #edf2f6; padding: 5px; border: 1px solid #d5dee5; }")
    window = MainWindow()
    window.show()

    def exception_hook(type_, value, tb):
        logging.critical("Unhandled exception", exc_info=(type_, value, tb))
        QtW.QMessageBox.critical(window, "Unexpected error", f"{value}\nDetails saved in {log_dir}.")
    sys.excepthook = exception_hook
    if args.smoke_test:
        from .smoke import run_smoke
        outcome = {"code": 1}
        def execute():
            try:
                run_smoke(window, args.output)
                outcome["code"] = 0
            except Exception:
                logging.exception("Smoke test failed")
            finally:
                window.close()
                app.quit()
        QtCore.QTimer.singleShot(150, execute)
        app.exec()
        return outcome["code"]
    if args.files:
        QtCore.QTimer.singleShot(0, lambda: window.add_files(args.files))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
