from pathlib import Path

from filing_doc_converter.system_check_dialog import SystemCheckDialog
from filing_doc_converter.system_diagnostics import ComponentStatus, SystemDiagnostics


def sample_diagnostics() -> SystemDiagnostics:
    return SystemDiagnostics(
        application_version="0.1.0a0",
        operating_system="TestOS",
        operating_system_version="1",
        architecture="test-arch",
        python_version="3.12.0",
        pyside_version="6.9.0",
        components=(
            ComponentStatus("ocrmypdf", "OCRmyPDF", True, "17.0.0"),
            ComponentStatus(
                "tesseract",
                "Tesseract OCR",
                True,
                "5.5.0",
                ("Languages: eng, spa",),
            ),
            ComponentStatus("docling", "Docling", False, error="Package not installed"),
        ),
    )


def test_dialog_displays_component_status(qtbot) -> None:
    dialog = SystemCheckDialog(diagnostics_provider=sample_diagnostics)
    qtbot.addWidget(dialog)

    assert dialog.component_table.rowCount() == 3
    assert dialog.component_table.item(0, 0).text() == "OCRmyPDF"
    assert dialog.component_table.item(0, 1).text() == "Available"
    assert dialog.component_table.item(2, 1).text() == "Unavailable"
    assert "Docling" in dialog.guidance_label.text()


def test_refresh_emits_updated_diagnostics(qtbot) -> None:
    dialog = SystemCheckDialog(diagnostics_provider=sample_diagnostics)
    qtbot.addWidget(dialog)
    reports = []
    dialog.diagnostics_updated.connect(reports.append)

    dialog.refresh()

    assert reports == [sample_diagnostics()]


def test_save_report_writes_privacy_safe_text(qtbot, tmp_path: Path) -> None:
    dialog = SystemCheckDialog(diagnostics_provider=sample_diagnostics)
    qtbot.addWidget(dialog)
    destination = tmp_path / "diagnostics.txt"

    dialog.save_report(destination)

    content = destination.read_text(encoding="utf-8")
    assert "Filing Document Converter - System Check" in content
    assert "Docling: Unavailable" in content
    assert "secret.pdf" not in content
    assert "/home/" not in content
    assert "C:\\Users\\" not in content
