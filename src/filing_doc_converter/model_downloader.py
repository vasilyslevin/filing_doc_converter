import subprocess
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from filing_doc_converter.model_management import (
    ModelManagementError,
    build_model_download_command,
    mark_models_ready,
)


class ModelDownloadWorker(QObject):
    status_changed = Signal(str)
    completed = Signal()
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        model_directory: Path,
        *,
        executable: str | None = None,
    ) -> None:
        super().__init__()
        self._model_directory = model_directory.resolve()
        self._executable = executable
        self._cancel_event = Event()
        self._process: subprocess.Popen[str] | None = None

    @Slot()
    def run(self) -> None:
        try:
            if self._cancel_event.is_set():
                self.cancelled.emit()
                return

            command = build_model_download_command(
                self._model_directory,
                executable=self._executable,
            )
            self._model_directory.mkdir(parents=True, exist_ok=True)
            self.status_changed.emit("Downloading generic Docling model files...")
            self._process = subprocess.Popen(
                command,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            output = ""
            while True:
                if self._cancel_event.is_set():
                    self._stop_process()
                    self.cancelled.emit()
                    return
                try:
                    output, _ = self._process.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    continue

            if self._process.returncode != 0:
                detail = output.strip()
                message = "The model download did not complete."
                if detail:
                    separator = "\n\n" if "\n" in detail else " "
                    message = f"{message}{separator}{detail}"
                self.failed.emit(message)
                return

            mark_models_ready(self._model_directory)
            self.status_changed.emit("Local model setup is complete.")
            self.completed.emit()
        except (OSError, ModelManagementError) as error:
            self.failed.emit(str(error))
        finally:
            self._process = None
            self.finished.emit()

    def cancel(self) -> None:
        self._cancel_event.set()

    def _stop_process(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
