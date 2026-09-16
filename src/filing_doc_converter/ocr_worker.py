from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from filing_doc_converter.ocr_pipeline import OcrCancelledError, OcrResult, run_ocr


class OcrWorker(QObject):
    file_started = Signal(int, int, str)
    file_succeeded = Signal(str, str)
    file_failed = Signal(str, str)
    finished = Signal(bool, int, int)

    def __init__(
        self,
        input_paths: tuple[Path, ...],
        output_directory: Path,
        *,
        language: str = "eng",
        executable: str | None = None,
    ) -> None:
        super().__init__()
        self._input_paths = input_paths
        self._output_directory = output_directory
        self._language = language
        self._executable = executable
        self._cancel_event = Event()

    @Slot()
    def run(self) -> None:
        succeeded = 0
        failed = 0
        cancelled = False
        total = len(self._input_paths)

        for index, input_path in enumerate(self._input_paths, start=1):
            if self._cancel_event.is_set():
                cancelled = True
                break

            self.file_started.emit(index, total, input_path.name)
            try:
                result = run_ocr(
                    input_path,
                    self._output_directory,
                    language=self._language,
                    executable=self._executable,
                    cancel_event=self._cancel_event,
                )
            except OcrCancelledError:
                cancelled = True
                break
            except Exception as error:
                failed += 1
                self.file_failed.emit(str(input_path), str(error))
            else:
                succeeded += 1
                self._emit_success(result)

        self.finished.emit(cancelled, succeeded, failed)

    def cancel(self) -> None:
        self._cancel_event.set()

    def _emit_success(self, result: OcrResult) -> None:
        self.file_succeeded.emit(str(result.input_path), str(result.output_path))
