import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)

from filing_doc_converter.docling_runtime import DOCLING_OCR_ENV, DOCLING_TABLES_ENV
from filing_doc_converter.error_dialog import ErrorDetailsDialog
from filing_doc_converter.main_window import MainWindow
from filing_doc_converter.model_management import (
    ModelDirectoryState,
    load_model_directory,
)
from filing_doc_converter.system_check_dialog import SystemCheckDialog
from filing_doc_converter.system_diagnostics import (
    OutputAvailability,
    SystemDiagnostics,
    check_output_availability,
)


class ApplicationWindow(MainWindow):
    def __init__(
        self,
        *,
        availability_provider: Callable[[], OutputAvailability] = check_output_availability,
        model_state_provider: Callable[[], ModelDirectoryState] = load_model_directory,
    ) -> None:
        self._availability_provider = availability_provider
        self._model_state_provider = model_state_provider
        super().__init__()
        self.queue.itemClicked.connect(self.show_queue_item_details)
        self._add_docling_performance_controls()

        help_menu = self.menuBar().addMenu("Help")
        self.system_check_action = help_menu.addAction("System Check")
        self.system_check_action.triggered.connect(self.show_system_check)

        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_directory)
        self.statusBar().addPermanentWidget(self.open_output_button)

        self.refresh_output_availability()
        self._update_open_output_button()

    def _add_docling_performance_controls(self) -> None:
        self.docling_ocr_checkbox = QCheckBox("OCR scanned pages in AI output")
        self.docling_ocr_checkbox.setChecked(False)
        self.docling_ocr_checkbox.setToolTip(
            "Enable only for scanned PDFs without selectable text. This is slower."
        )
        self.table_structure_checkbox = QCheckBox("Analyze table structure")
        self.table_structure_checkbox.setChecked(False)
        self.table_structure_checkbox.setToolTip(
            "Improves complex tables but adds substantial CPU processing time."
        )

        options_row = QHBoxLayout()
        options_row.addWidget(self.docling_ocr_checkbox)
        options_row.addWidget(self.table_structure_checkbox)
        options_row.addStretch()
        output_parent = self.markdown_checkbox.parentWidget()
        if output_parent is not None and output_parent.layout() is not None:
            output_parent.layout().addLayout(options_row)

    def set_output_directory(self, path: Path) -> None:
        super().set_output_directory(path)
        if hasattr(self, "open_output_button"):
            self._update_open_output_button()

    def refresh_output_availability(self) -> None:
        self.apply_output_availability(self._availability_provider())

    def apply_output_availability(self, availability: OutputAvailability) -> None:
        self.searchable_pdf_checkbox.setEnabled(availability.searchable_pdf)
        if not availability.searchable_pdf:
            self.searchable_pdf_checkbox.setChecked(False)
            self.searchable_pdf_checkbox.setToolTip(
                "Searchable PDF requires OCRmyPDF and Tesseract OCR."
            )
        else:
            self.searchable_pdf_checkbox.setToolTip("")

        for checkbox in (self.markdown_checkbox, self.json_checkbox):
            checkbox.setEnabled(availability.docling)
            if not availability.docling:
                checkbox.setChecked(False)
                checkbox.setToolTip(
                    availability.docling_reason
                    or "Markdown and JSON require Docling and downloaded local models."
                )
            else:
                checkbox.setToolTip("")

        self.docling_ocr_checkbox.setEnabled(availability.docling)
        self.table_structure_checkbox.setEnabled(availability.docling)
        self.update_process_button()

    def apply_diagnostics(self, diagnostics: SystemDiagnostics) -> None:
        ocrmypdf = diagnostics.component("ocrmypdf")
        tesseract = diagnostics.component("tesseract")
        docling = diagnostics.component("docling")
        model_state = self._model_state_provider()
        reason = None
        if not docling.available:
            reason = "Docling is not installed. Open Help > System Check for setup guidance."
        elif not model_state.ready:
            reason = (
                "Local Docling models are not ready. "
                "Open Help > System Check and download models."
            )
        self.apply_output_availability(
            OutputAvailability(
                searchable_pdf=ocrmypdf.available and tesseract.available,
                docling=docling.available and model_state.ready,
                docling_reason=reason,
            )
        )

    def show_system_check(self) -> None:
        dialog = SystemCheckDialog(self)
        dialog.diagnostics_updated.connect(self.apply_diagnostics)
        dialog.exec()
        self.refresh_output_availability()

    def show_queue_item_details(self, item: QListWidgetItem) -> None:
        if not item.text().startswith("Failed:"):
            return
        detail = item.toolTip().strip()
        if not detail:
            return
        ErrorDetailsDialog(detail, self).exec()

    def start_processing(self) -> None:
        os.environ[DOCLING_OCR_ENV] = "1" if self.docling_ocr_checkbox.isChecked() else "0"
        os.environ[DOCLING_TABLES_ENV] = (
            "1" if self.table_structure_checkbox.isChecked() else "0"
        )
        super().start_processing()

    def open_output_directory(self) -> None:
        output_directory = self.output_directory
        if output_directory is None or not output_directory.is_dir():
            QMessageBox.warning(
                self,
                "Output folder unavailable",
                "The output folder does not exist yet.",
            )
            self._update_open_output_button()
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_directory)))
        if not opened:
            QMessageBox.warning(
                self,
                "Could not open folder",
                "The operating system could not open the output folder.",
            )

    def _on_file_started(self, index: int, total: int, name: str) -> None:
        super()._on_file_started(index, total, name)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(f"Processing {index}/{total}: {name}")

    def _on_file_succeeded(self, input_path: str, output_files: object) -> None:
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_file_succeeded(input_path, output_files)

    def _on_file_failed(self, input_path: str, error: str) -> None:
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_file_failed(input_path, error)

    def _on_processing_finished(self, cancelled: bool, succeeded: int, failed: int) -> None:
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_processing_finished(cancelled, succeeded, failed)
        self._update_open_output_button()

    def _update_open_output_button(self) -> None:
        output_directory = self.output_directory
        self.open_output_button.setEnabled(
            output_directory is not None and output_directory.is_dir()
        )
