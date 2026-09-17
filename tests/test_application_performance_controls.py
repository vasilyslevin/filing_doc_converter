import os
from pathlib import Path

from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.docling_runtime import DOCLING_OCR_ENV, DOCLING_TABLES_ENV
from filing_doc_converter.model_management import ModelDirectoryState
from filing_doc_converter.system_diagnostics import OutputAvailability


def test_docling_performance_controls_default_to_fast_mode(monkeypatch, qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True),
        model_state_provider=lambda: ModelDirectoryState(Path("models"), "settings", True),
    )
    qtbot.addWidget(window)

    assert not window.docling_ocr_checkbox.isChecked()
    assert not window.table_structure_checkbox.isChecked()

    monkeypatch.setattr(window, "pdf_paths", (), raising=False)
    window.start_processing()

    assert os.environ[DOCLING_OCR_ENV] == "0"
    assert os.environ[DOCLING_TABLES_ENV] == "0"
