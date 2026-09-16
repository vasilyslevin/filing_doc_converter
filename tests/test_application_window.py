from pathlib import Path

from PySide6.QtCore import QUrl

from filing_doc_converter import application_window
from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.model_management import ModelDirectoryState
from filing_doc_converter.system_diagnostics import (
    ComponentStatus,
    OutputAvailability,
    SystemDiagnostics,
)


def ready_models() -> ModelDirectoryState:
    return ModelDirectoryState(Path("models"), "settings", True)


def missing_models() -> ModelDirectoryState:
    return ModelDirectoryState(Path("models"), "settings", False)


def test_unavailable_components_disable_outputs(qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(False, False)
    )
    qtbot.addWidget(window)

    assert not window.searchable_pdf_checkbox.isEnabled()
    assert not window.searchable_pdf_checkbox.isChecked()
    assert not window.markdown_checkbox.isEnabled()
    assert not window.json_checkbox.isEnabled()


def test_available_components_enable_outputs(qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True)
    )
    qtbot.addWidget(window)

    assert window.searchable_pdf_checkbox.isEnabled()
    assert window.searchable_pdf_checkbox.isChecked()
    assert window.markdown_checkbox.isEnabled()
    assert window.json_checkbox.isEnabled()


def test_diagnostics_update_output_availability(qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(False, False),
        model_state_provider=ready_models,
    )
    qtbot.addWidget(window)
    diagnostics = SystemDiagnostics(
        application_version="0.1.0a0",
        operating_system="TestOS",
        operating_system_version="1",
        architecture="test",
        python_version="3.12",
        pyside_version="6.9",
        components=(
            ComponentStatus("ocrmypdf", "OCRmyPDF", True),
            ComponentStatus("tesseract", "Tesseract OCR", True),
            ComponentStatus("docling", "Docling", True),
        ),
    )

    window.apply_diagnostics(diagnostics)

    assert window.searchable_pdf_checkbox.isEnabled()
    assert window.markdown_checkbox.isEnabled()
    assert window.json_checkbox.isEnabled()


def test_missing_models_disable_only_docling_outputs(qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True),
        model_state_provider=missing_models,
    )
    qtbot.addWidget(window)
    diagnostics = SystemDiagnostics(
        application_version="0.1.0a0",
        operating_system="TestOS",
        operating_system_version="1",
        architecture="test",
        python_version="3.12",
        pyside_version="6.9",
        components=(
            ComponentStatus("ocrmypdf", "OCRmyPDF", True),
            ComponentStatus("tesseract", "Tesseract OCR", True),
            ComponentStatus("docling", "Docling", True),
        ),
    )

    window.apply_diagnostics(diagnostics)

    assert window.searchable_pdf_checkbox.isEnabled()
    assert not window.markdown_checkbox.isEnabled()
    assert not window.json_checkbox.isEnabled()
    assert "models are not ready" in window.markdown_checkbox.toolTip()


def test_open_output_folder_uses_desktop_services(monkeypatch, qtbot, tmp_path: Path) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True)
    )
    qtbot.addWidget(window)
    window.set_output_directory(tmp_path)
    opened_urls: list[QUrl] = []
    monkeypatch.setattr(
        application_window.QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url) or True,
    )

    window.open_output_directory()

    assert window.open_output_button.isEnabled()
    assert len(opened_urls) == 1
    assert Path(opened_urls[0].toLocalFile()).resolve() == tmp_path.resolve()


def test_open_output_button_waits_for_existing_folder(qtbot, tmp_path: Path) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(True, True)
    )
    qtbot.addWidget(window)

    window.set_output_directory(tmp_path / "not-created")

    assert not window.open_output_button.isEnabled()
