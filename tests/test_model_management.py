from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from filing_doc_converter import model_management
from filing_doc_converter.model_management import (
    MODEL_DIRECTORY_SETTING,
    MODEL_READY_MARKER,
    ModelManagementError,
    build_model_download_command,
    load_model_directory,
    mark_models_ready,
    models_ready,
    resolve_model_downloader,
    save_model_directory,
)


def make_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_environment_override_takes_precedence(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.setValue(MODEL_DIRECTORY_SETTING, str(tmp_path / "saved"))
    override = tmp_path / "managed-models"

    state = load_model_directory(
        settings,
        environ={"FILING_DOC_CONVERTER_MODEL_DIR": str(override)},
    )

    assert state.path == override.resolve()
    assert state.source == "environment"
    assert not state.ready


def test_saved_directory_is_persistent(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    selected = tmp_path / "models"

    saved = save_model_directory(selected, settings)
    state = load_model_directory(settings, environ={})

    assert saved == selected.resolve()
    assert state.path == selected.resolve()
    assert state.source == "settings"


def test_default_directory_is_used_without_override(monkeypatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    expected = tmp_path / "default-models"
    monkeypatch.setattr(model_management, "default_model_directory", lambda: expected)

    state = load_model_directory(settings, environ={})

    assert state.path == expected
    assert state.source == "default"


def test_directory_is_ready_only_after_completed_download(tmp_path: Path) -> None:
    directory = tmp_path / "models"
    directory.mkdir()
    (directory / "model.bin").write_bytes(b"model")

    assert not models_ready(directory)

    marker = mark_models_ready(directory)

    assert marker == directory / MODEL_READY_MARKER
    assert models_ready(directory)


def test_empty_directory_cannot_be_marked_ready(tmp_path: Path) -> None:
    directory = tmp_path / "models"
    directory.mkdir()

    with pytest.raises(ModelManagementError, match="No downloaded model files"):
        mark_models_ready(directory)


def test_download_command_is_an_argument_list(tmp_path: Path) -> None:
    destination = tmp_path / "models with spaces"

    command = build_model_download_command(
        destination,
        executable="docling-tools",
    )

    assert command == [
        "docling-tools",
        "models",
        "download",
        "-o",
        str(destination.resolve()),
    ]
    assert not any("document" in argument.lower() for argument in command)


def test_source_run_resolves_downloader_from_path(monkeypatch) -> None:
    monkeypatch.setattr(model_management, "is_packaged_application", lambda: False)
    monkeypatch.setattr(
        model_management.shutil,
        "which",
        lambda executable: "C:/tools/docling-tools.exe",
    )

    assert resolve_model_downloader() == "C:/tools/docling-tools.exe"


def test_packaged_run_resolves_sibling_downloader(monkeypatch, tmp_path: Path) -> None:
    application = tmp_path / "FilingDocumentConverter.exe"
    companion = tmp_path / "docling-tools.exe"
    companion.write_bytes(b"packaged tool")
    monkeypatch.setattr(model_management, "is_packaged_application", lambda: True)
    monkeypatch.setattr(model_management.sys, "executable", str(application))
    monkeypatch.setattr(
        model_management.shutil,
        "which",
        lambda executable: pytest.fail("PATH must not be used for a packaged application"),
    )

    assert resolve_model_downloader() == str(companion.resolve())


def test_packaged_run_fails_closed_without_companion(monkeypatch, tmp_path: Path) -> None:
    application = tmp_path / "FilingDocumentConverter.exe"
    monkeypatch.setattr(model_management, "is_packaged_application", lambda: True)
    monkeypatch.setattr(model_management.sys, "executable", str(application))
    monkeypatch.setattr(
        model_management.shutil,
        "which",
        lambda executable: pytest.fail("PATH must not be used for a packaged application"),
    )

    with pytest.raises(ModelManagementError, match="packaged docling-tools.exe companion"):
        resolve_model_downloader()


def test_missing_downloader_is_reported(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(model_management, "is_packaged_application", lambda: False)
    monkeypatch.setattr(model_management.shutil, "which", lambda executable: None)

    with pytest.raises(ModelManagementError, match="docling-tools was not found"):
        build_model_download_command(tmp_path / "models")
