import os
from pathlib import Path

from PySide6.QtCore import QSettings

from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.docling_runtime import (
    DOCLING_CPU_ONLY_ENV,
    DOCLING_OCR_ENV,
    DOCLING_TABLES_ENV,
)
from filing_doc_converter.model_management import ModelDirectoryState
from filing_doc_converter.system_diagnostics import OutputAvailability


def make_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def make_window(qtbot, settings: QSettings) -> ApplicationWindow:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True),
        model_state_provider=lambda: ModelDirectoryState(Path("models"), "settings", True),
        settings=settings,
    )
    qtbot.addWidget(window)
    return window


def test_docling_performance_controls_default_to_fast_mode(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, make_settings(tmp_path))

    assert not window.docling_ocr_checkbox.isChecked()
    assert not window.table_structure_checkbox.isChecked()
    assert window.cpu_only_checkbox.isChecked()

    window.start_processing()

    assert os.environ[DOCLING_OCR_ENV] == "0"
    assert os.environ[DOCLING_TABLES_ENV] == "0"
    assert os.environ[DOCLING_CPU_ONLY_ENV] == "1"


def test_processing_choices_persist_between_windows(qtbot, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    first = make_window(qtbot, settings)
    first.docling_ocr_checkbox.setChecked(True)
    first.table_structure_checkbox.setChecked(True)
    first.cpu_only_checkbox.setChecked(False)

    second = make_window(qtbot, settings)

    assert second.docling_ocr_checkbox.isChecked()
    assert second.table_structure_checkbox.isChecked()
    assert not second.cpu_only_checkbox.isChecked()


def test_gpu_auto_detection_can_be_selected(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, make_settings(tmp_path))
    window.cpu_only_checkbox.setChecked(False)

    window.start_processing()

    assert os.environ[DOCLING_CPU_ONLY_ENV] == "0"
