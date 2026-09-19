from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from filing_doc_converter.ocr_pipeline import (
    DoclingResult,
    OcrCancelledError,
    OcrError,
    run_docling,
    run_ocr,
)
from filing_doc_converter.ocr_runtime import TesseractRuntimeProfile


class ProcessingWorker(QObject):
    file_started = Signal(int, int, str)
    stage_changed = Signal(str)
    file_succeeded = Signal(str, str)
    file_failed = Signal(str, str)
    finished = Signal(bool, int, int)

    def __init__(
        self,
        input_paths: tuple[Path, ...],
        output_directory: Path,
        *,
        create_searchable_pdf: bool,
        create_markdown: bool,
        create_json: bool,
        language: str = "eng",
        executable: str | None = None,
        tesseract_profile: TesseractRuntimeProfile | None = None,
        ocr_mode: str = "smart",
    ) -> None:
        super().__init__()
        self._input_paths = input_paths
        self._output_directory = output_directory
        self._create_searchable_pdf = create_searchable_pdf
        self._create_markdown = create_markdown
        self._create_json = create_json
        self._language = language
        self._executable = executable
        self._tesseract_profile = tesseract_profile
        self._ocr_mode = ocr_mode
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
            success_paths: list[str] = []
            try:
                docling_input = input_path
                if self._create_searchable_pdf:
                    self.stage_changed.emit("Running OCRmyPDF")
                    ocr_result = run_ocr(
                        input_path,
                        self._output_directory,
                        language=self._language,
                        executable=self._executable,
                        tesseract_profile=self._tesseract_profile,
                        cancel_event=self._cancel_event,
                        mode=self._ocr_mode,
                    )
                    self.stage_changed.emit(
                        f"OCR mode: {ocr_result.effective_mode.title()} OCR"
                    )
                    docling_input = ocr_result.output_path
                    success_paths.append(str(ocr_result.output_path))
                    for warning in ocr_result.warnings:
                        success_paths.append(f"Warning: {warning}")

                if self._create_markdown or self._create_json:
                    self.stage_changed.emit("Loading models and analyzing pages")
                    docling_result = run_docling(
                        docling_input,
                        self._output_directory,
                        export_markdown=self._create_markdown,
                        export_json=self._create_json,
                        output_stem=input_path.stem,
                        cancel_event=self._cancel_event,
                    )
                    self.stage_changed.emit("Finalizing Markdown/JSON outputs")
                    self._append_docling_outputs(success_paths, docling_result)
            except OcrCancelledError:
                cancelled = True
                break
            except OcrError as error:
                failed += 1
                self.file_failed.emit(str(input_path), str(error))
            else:
                succeeded += 1
                self.file_succeeded.emit(str(input_path), "\n".join(success_paths))

        self.finished.emit(cancelled, succeeded, failed)

    def cancel(self) -> None:
        self._cancel_event.set()

    @staticmethod
    def _append_docling_outputs(outputs: list[str], result: DoclingResult) -> None:
        if result.markdown_path is not None:
            outputs.append(str(result.markdown_path))
        if result.json_path is not None:
            outputs.append(str(result.json_path))


OcrWorker = ProcessingWorker
