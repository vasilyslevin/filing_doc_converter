import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QSettings, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
)

from filing_doc_converter.docling_runtime import (
    DOCLING_CPU_ONLY_ENV,
    DOCLING_OCR_ENV,
    DOCLING_TABLES_ENV,
)
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

DOCLING_OCR_SETTING = "processing/docling_ocr"
DOCLING_TABLES_SETTING = "processing/docling_tables"
DOCLING_CPU_ONLY_SETTING = "processing/docling_cpu_only"


def format_elapsed(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class ApplicationWindow(MainWindow):
    def __init__(
        self,
        *,
        availability_provider: Callable[[], OutputAvailability] = check_output_availability,
        model_state_provider: Callable[[], ModelDirectoryState] = load_model_directory,
        settings: QSettings | None = None,
    ) -> None:
        self._availability_provider = availability_provider
        self._model_state_provider = model_state_provider
        self._settings = settings if settings is not None else QSettings()
        self._processing_clock = QElapsedTimer()
        self._processing_timer = QTimer(self)
        self._processing_timer.setInterval(1000)
        self._processing_timer.timeout.connect(self._refresh_processing_text)
        self._processing_stage = "Preparing"
        self._processing_file = ""
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

    def _setting_bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _add_docling_performance_controls(self) -> None:
        self.docling_ocr_checkbox = QCheckBox("OCR scanned pages in AI output")
        self.docling_ocr_checkbox.setChecked(
            self._setting_bool(DOCLING_OCR_SETTING, False)
        )
        self.docling_ocr_checkbox.setToolTip(
            "Enable only for scanned PDFs without selectable text. This is slower."
        )
        self.table_structure_checkbox = QCheckBox("Analyze table structure")
        self.table_structure_checkbox.setChecked(
            self._setting_bool(DOCLING_TABLES_SETTING, False)
        )
        self.table_structure_checkbox.setToolTip(
            "Improves complex tables but adds substantial CPU processing time."
        )
        self.cpu_only_checkbox = QCheckBox("CPU only (maximum compatibility)")
        self.cpu_only_checkbox.setChecked(
            self._setting_bool(DOCLING_CPU_ONLY_SETTING, True)
        )
        self.cpu_only_checkbox.setToolTip(
            "Uncheck to let Docling automatically use a supported GPU when available."
        )
        for checkbox in (
            self.docling_ocr_checkbox,
            self.table_structure_checkbox,
            self.cpu_only_checkbox,
        ):
            checkbox.toggled.connect(self._save_processing_preferences)

        options_row = QHBoxLayout()
        options_row.addWidget(self.docling_ocr_checkbox)
        options_row.addWidget(self.table_structure_checkbox)
        options_row.addWidget(self.cpu_only_checkbox)
        options_row.addStretch()
        output_parent = self.markdown_checkbox.parentWidget()
        if output_parent is not None and output_parent.layout() is not None:
            output_parent.layout().addLayout(options_row)

    def _save_processing_preferences(self) -> None:
        self._settings.setValue(DOCLING_OCR_SETTING, self.docling_ocr_checkbox.isChecked())
        self._settings.setValue(
            DOCLING_TABLES_SETTING,
            self.table_structure_checkbox.isChecked(),
        )
        self._settings.setValue(
            DOCLING_CPU_ONLY_SETTING,
            self.cpu_only_checkbox.isChecked(),
        )
        self._settings.sync()

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

        for checkbox in (
            self.docling_ocr_checkbox,
            self.table_structure_checkbox,
            self.cpu_only_checkbox,
        ):
            checkbox.setEnabled(availability.docling)
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
        dialog = SystemCheckDialog(self, settings=self._settings)
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
        os.environ[DOCLING_CPU_ONLY_ENV] = "1" if self.cpu_only_checkbox.isChecked() else "0"
        self._processing_stage = "Preparing"
        self._processing_file = ""
        self._processing_clock.start()
        self._processing_timer.start()
        super().start_processing()
        if not self._processing:
            self._processing_timer.stop()
            self._processing_clock.invalidate()
            return
        if self._worker is not None:
            self._worker.stage_changed.connect(self._on_processing_stage_changed)

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
        self._processing_file = f"{index}/{total}: {name}"
        self._processing_stage = "Preparing"
        self.progress_bar.setRange(0, 0)
        self._refresh_processing_text()

    def _on_processing_stage_changed(self, stage: str) -> None:
        self._processing_stage = stage
        self._refresh_processing_text()

    def _refresh_processing_text(self) -> None:
        if not self._processing_clock.isValid():
            return
        elapsed = format_elapsed(self._processing_clock.elapsed())
        parts = [self._processing_stage]
        if self._processing_file:
            parts.append(self._processing_file)
        parts.append(elapsed)
        self.progress_bar.setFormat(" — ".join(parts))

    def _on_file_succeeded(self, input_path: str, output_files: object) -> None:
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_file_succeeded(input_path, output_files)

    def _on_file_failed(self, input_path: str, error: str) -> None:
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_file_failed(input_path, error)

    def _on_processing_finished(self, cancelled: bool, succeeded: int, failed: int) -> None:
        self._processing_timer.stop()
        self.progress_bar.setRange(0, max(1, len(self._pdf_paths)))
        super()._on_processing_finished(cancelled, succeeded, failed)
        self._processing_clock.invalidate()
        self._update_open_output_button()

    def _update_open_output_button(self) -> None:
        output_directory = self.output_directory
        self.open_output_button.setEnabled(
            output_directory is not None and output_directory.is_dir()
        )
