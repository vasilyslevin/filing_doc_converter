from pathlib import Path

from PySide6.QtCore import QSettings

from source_doc_converter import model_management
from source_doc_converter.model_management import (
    EXPECTED_MODEL_DIRECTORIES,
    MODEL_DIRECTORY_SETTING,
    downloaded_models_complete,
    load_model_directory,
    models_ready,
    reset_model_directory,
)


def make_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_complete_cli_download_is_ready_without_marker(tmp_path: Path) -> None:
    for relative in EXPECTED_MODEL_DIRECTORIES:
        directory = tmp_path / relative
        directory.mkdir()
        (directory / "model.bin").write_bytes(b"model")

    assert downloaded_models_complete(tmp_path)
    assert models_ready(tmp_path)


def test_partial_cli_download_is_not_ready(tmp_path: Path) -> None:
    for relative in EXPECTED_MODEL_DIRECTORIES[:-1]:
        directory = tmp_path / relative
        directory.mkdir()
        (directory / "model.bin").write_bytes(b"model")

    assert not downloaded_models_complete(tmp_path)
    assert not models_ready(tmp_path)


def test_reset_clears_saved_folder_without_deleting_it(monkeypatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    selected = tmp_path / "models-test"
    selected.mkdir()
    (selected / "keep.bin").write_bytes(b"keep")
    default = tmp_path / "default-models"
    settings.setValue(MODEL_DIRECTORY_SETTING, str(selected))
    monkeypatch.setattr(model_management, "default_model_directory", lambda: default)

    result = reset_model_directory(settings)
    state = load_model_directory(settings, environ={})

    assert result == default
    assert state.path == default
    assert state.source == "default"
    assert (selected / "keep.bin").read_bytes() == b"keep"
