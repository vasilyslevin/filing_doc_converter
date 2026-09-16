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


class ProcessingWorker(QObject):
    file_started = Signal(int, int, str)
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
    ) -> None:
        super().__init__()
        self._input_paths = input_paths
        self._output_directory = output_directory
        self._create_searchable_pdf = create_searchable_pdf
        self._create_markdown = create_markdown
        self._create_json = create_json
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
            success_paths: list[str] = []
            try:
                docling_input = input_path
                if self._create_searchable_pdf:
                    ocr_result = run_ocr(
                        input_path,
                        self._output_directory,
                        language=self._language,
                        executable=self._executable,
                        cancel_event=self._cancel_event,
                    )
                    docling_input = ocr_result.output_path
                    success_paths.append(str(ocr_result.output_path))

                if self._create_markdown or self._create_json:
                    docling_result = run_docling(
                        docling_input,
                        self._output_directory,
                        export_markdown=self._create_markdown,
                        export_json=self._create_json,
                        output_stem=input_path.stem,
                        cancel_event=self._cancel_event,
                    )
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
