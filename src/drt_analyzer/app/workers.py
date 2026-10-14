import logging
import threading
from PySide6 import QtCore
from ..analysis.pipeline import analyze, lambda_scan
from ..drt.base import Cancelled

log = logging.getLogger(__name__)


class AnalysisWorker(QtCore.QObject):
    started_item = QtCore.Signal(int, str)
    result = QtCore.Signal(int, object)
    failed = QtCore.Signal(int, str)
    scan_result = QtCore.Signal(int, object)
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(bool)

    def __init__(self, jobs, scan=False):
        super().__init__()
        self.jobs = jobs
        self.scan = scan
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    @QtCore.Slot()
    def run(self):
        cancelled = False
        try:
            for n, (index, raw, settings) in enumerate(self.jobs):
                if self.cancel_event.is_set():
                    cancelled = True
                    break
                self.started_item.emit(index, raw.name)
                try:
                    if self.scan:
                        variants = lambda_scan(raw, settings, self.cancel_event.is_set,
                                               lambda done, total: self.progress.emit(done, total))
                        self.scan_result.emit(index, variants)
                    else:
                        v = analyze(raw, settings, self.cancel_event.is_set)
                        self.result.emit(index, v)
                        self.progress.emit(n+1, len(self.jobs))
                except Cancelled:
                    cancelled = True
                    break
                except Exception as exc:
                    log.exception("Analysis failed for %s", raw.source_path)
                    self.failed.emit(index, str(exc))
                    self.progress.emit(n+1, len(self.jobs))
        except Exception:
            log.exception("Unexpected batch failure")
            cancelled = True
        finally:
            self.finished.emit(cancelled)
