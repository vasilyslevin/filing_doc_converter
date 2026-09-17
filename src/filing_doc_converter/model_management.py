import os
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

MODEL_DIRECTORY_ENV = "FILING_DOC_CONVERTER_MODEL_DIR"
MODEL_DIRECTORY_SETTING = "models/directory"
MODEL_READY_MARKER = ".filing-doc-converter-models-ready"
PACKAGED_DOWNLOADER_NAME = "docling-tools.exe"


class ModelManagementError(RuntimeError):
    """Raised when local model setup cannot be completed safely."""


@dataclass(frozen=True)
class ModelDirectoryState:
    path: Path
    source: str
    ready: bool


def _normalise_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def default_model_directory() -> Path:
    data_root = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericDataLocation
    )
    if data_root:
        return _normalise_path(Path(data_root) / "FilingDocumentConverter" / "models")
    return _normalise_path(Path.home() / ".filing_doc_converter" / "models")


def load_model_directory(
    settings: QSettings | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ModelDirectoryState:
    environment = os.environ if environ is None else environ
    override = environment.get(MODEL_DIRECTORY_ENV, "").strip()
    if override:
        path = _normalise_path(override)
        return ModelDirectoryState(path, "environment", models_ready(path))

    active_settings = settings if settings is not None else QSettings()
    saved = str(active_settings.value(MODEL_DIRECTORY_SETTING, "")).strip()
    if saved:
        path = _normalise_path(saved)
        return ModelDirectoryState(path, "settings", models_ready(path))

    path = default_model_directory()
    return ModelDirectoryState(path, "default", models_ready(path))


def save_model_directory(path: str | Path, settings: QSettings | None = None) -> Path:
    directory = _normalise_path(path)
    active_settings = settings if settings is not None else QSettings()
    active_settings.setValue(MODEL_DIRECTORY_SETTING, str(directory))
    active_settings.sync()
    return directory


def models_ready(path: str | Path) -> bool:
    directory = _normalise_path(path)
    marker = directory / MODEL_READY_MARKER
    if not marker.is_file():
        return False
    return any(item.is_file() and item != marker for item in directory.rglob("*"))


def mark_models_ready(path: str | Path) -> Path:
    directory = _normalise_path(path)
    marker = directory / MODEL_READY_MARKER
    has_model_files = directory.is_dir() and any(
        item.is_file() and item != marker for item in directory.rglob("*")
    )
    if not has_model_files:
        raise ModelManagementError("No downloaded model files were found.")
    marker.write_text("ready\n", encoding="utf-8", newline="\n")
    return marker


def is_packaged_application() -> bool:
    return bool(getattr(sys, "frozen", False) or "__compiled__" in globals())


def resolve_model_downloader() -> str:
    if is_packaged_application():
        companion = Path(sys.executable).resolve().with_name(PACKAGED_DOWNLOADER_NAME)
        if companion.is_file():
            return str(companion)
        raise ModelManagementError(
            "The packaged docling-tools.exe companion is missing. Reinstall or replace the "
            "application folder before downloading models."
        )

    executable = shutil.which("docling-tools")
    if executable:
        return executable
    raise ModelManagementError(
        "docling-tools was not found. Install the Docling optional dependencies and try again."
    )


def build_model_download_command(
    path: str | Path,
    *,
    executable: str | None = None,
) -> list[str]:
    resolved_executable = executable or resolve_model_downloader()
    return [
        resolved_executable,
        "models",
        "download",
        "-o",
        str(_normalise_path(path)),
    ]
