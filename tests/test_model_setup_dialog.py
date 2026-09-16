from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from filing_doc_converter import system_check_dialog
from filing_doc_converter.model_management import ModelDirectoryState
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
            ComponentStatus("tesseract", "Tesseract OCR", True, "5.5.0"),
            ComponentStatus("docling", "Docling", True, "2.0.0"),
        ),
    )


def make_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_model_status_shows_ready_without_hiding_folder(monkeypatch, qtbot, tmp_path: Path) -> None:
    model_directory = tmp_path / "models"
    monkeypatch.setattr(
        system_check_dialog,
        "load_model_directory",
        lambda settings: ModelDirectoryState(model_directory, "settings", True),
    )
    dialog = SystemCheckDialog(
        diagnostics_provider=sample_diagnostics,
        settings=make_settings(tmp_path),
    )
    qtbot.addWidget(dialog)

    assert "Ready for offline conversion" in dialog.model_status_label.text()
    assert str(model_directory) in dialog.model_status_label.text()


def test_choose_model_folder_is_persisted(monkeypatch, qtbot, tmp_path: Path) -> None:
    monkeypatch.delenv("FILING_DOC_CONVERTER_MODEL_DIR", raising=False)
    selected = tmp_path / "selected-models"
    selected.mkdir()
    monkeypatch.setattr(
        system_check_dialog.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: str(selected),
    )
    settings = make_settings(tmp_path)
    dialog = SystemCheckDialog(
        diagnostics_provider=sample_diagnostics,
        settings=settings,
    )
    qtbot.addWidget(dialog)

    dialog.choose_model_directory()

    assert dialog.model_state is not None
    assert dialog.model_state.path == selected.resolve()
    assert dialog.model_state.source == "settings"


def test_download_requires_explicit_consent(monkeypatch, qtbot, tmp_path: Path) -> None:
    model_directory = tmp_path / "models"
    monkeypatch.setattr(
        system_check_dialog,
        "load_model_directory",
        lambda settings: ModelDirectoryState(model_directory, "settings", False),
    )
    prompts = []

    def decline(*args, **kwargs):
        prompts.append(args[2])
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(system_check_dialog.QMessageBox, "question", decline)
    dialog = SystemCheckDialog(
        diagnostics_provider=sample_diagnostics,
        settings=make_settings(tmp_path),
    )
    qtbot.addWidget(dialog)
    starts = []
    monkeypatch.setattr(dialog, "start_model_download", starts.append)

    dialog.confirm_model_download()

    assert starts == []
    assert "No queued document" in prompts[0]
    assert "Downloads may be large" in prompts[0]


def test_privacy_safe_report_omits_model_path(monkeypatch, qtbot, tmp_path: Path) -> None:
    model_directory = tmp_path / "private" / "models"
    monkeypatch.setattr(
        system_check_dialog,
        "load_model_directory",
        lambda settings: ModelDirectoryState(model_directory, "settings", True),
    )
    dialog = SystemCheckDialog(
        diagnostics_provider=sample_diagnostics,
        settings=make_settings(tmp_path),
    )
    qtbot.addWidget(dialog)
    report = tmp_path / "report.txt"

    dialog.save_report(report)

    content = report.read_text(encoding="utf-8")
    assert "Models: Ready" in content
    assert "Offline conversion: Enabled by default" in content
    assert str(model_directory) not in content
