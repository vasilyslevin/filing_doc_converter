from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QPushButton

from filing_doc_converter.main_window import MainWindow
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
    ) -> None:
        self._availability_provider = availability_provider
        super().__init__()

        help_menu = self.menuBar().addMenu("Help")
        self.system_check_action = help_menu.addAction("System Check")
        self.system_check_action.triggered.connect(self.show_system_check)

        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_directory)
        self.statusBar().addPermanentWidget(self.open_output_button)

        self.refresh_output_availability()
        self._update_open_output_button()

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
                checkbox.setToolTip("Markdown and JSON output require Docling.")
            else:
                checkbox.setToolTip("")

        self.update_process_button()

    def apply_diagnostics(self, diagnostics: SystemDiagnostics) -> None:
        ocrmypdf = diagnostics.component("ocrmypdf")
        tesseract = diagnostics.component("tesseract")
        docling = diagnostics.component("docling")
        self.apply_output_availability(
            OutputAvailability(
                searchable_pdf=ocrmypdf.available and tesseract.available,
                docling=docling.available,
            )
        )

    def show_system_check(self) -> None:
        dialog = SystemCheckDialog(self)
        dialog.diagnostics_updated.connect(self.apply_diagnostics)
        dialog.exec()
        if dialog.diagnostics is not None:
            self.apply_diagnostics(dialog.diagnostics)

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

    def _on_processing_finished(self, cancelled: bool, succeeded: int, failed: int) -> None:
        super()._on_processing_finished(cancelled, succeeded, failed)
        self._update_open_output_button()

    def _update_open_output_button(self) -> None:
        output_directory = self.output_directory
        self.open_output_button.setEnabled(
            output_directory is not None and output_directory.is_dir()
        )
