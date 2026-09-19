from __future__ import annotations

from PySide6.QtCore import QSettings

from source_doc_converter.model_management import (
    MODEL_DIRECTORY_SETTING,
    default_model_directory,
    legacy_default_model_directory,
    models_ready,
)

LEGACY_ORGANIZATION_NAME = "FilingDocumentConverter"
LEGACY_APPLICATION_NAME = "Filing Document Converter"
ORGANIZATION_NAME = "SourceDocumentConverter"
APPLICATION_NAME = "Source Document Converter"
SETTINGS_MIGRATION_VERSION_KEY = "migration/settings_version"
SETTINGS_MIGRATION_VERSION = 1

_MIGRATABLE_PREFIXES = (
    "models/",
    "ocr/",
    "processing/",
    "privacy/",
    "setup/",
    "ui/",
)

_NON_MIGRATABLE_SUBSTRINGS = (
    "secret",
    "token",
    "password",
    "temp",
    "tmp",
    "log",
    "process_state",
)


def _legacy_settings() -> QSettings:
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        LEGACY_ORGANIZATION_NAME,
        LEGACY_APPLICATION_NAME,
    )


def _current_settings() -> QSettings:
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        ORGANIZATION_NAME,
        APPLICATION_NAME,
    )


def _is_migratable_key(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith(_MIGRATABLE_PREFIXES) and not any(
        blocked in lowered for blocked in _NON_MIGRATABLE_SUBSTRINGS
    )


def migrate_legacy_settings(
    target_settings: QSettings | None = None,
    source_settings: QSettings | None = None,
) -> bool:
    target = _current_settings() if target_settings is None else target_settings
    try:
        current_version = int(target.value(SETTINGS_MIGRATION_VERSION_KEY, 0))
    except (TypeError, ValueError):
        current_version = 0
    if current_version >= SETTINGS_MIGRATION_VERSION:
        return False

    source = _legacy_settings() if source_settings is None else source_settings
    try:
        for key in source.allKeys():
            if not _is_migratable_key(key) or target.contains(key):
                continue
            target.setValue(key, source.value(key))

        if not target.contains(MODEL_DIRECTORY_SETTING):
            fallback_model_directory = legacy_default_model_directory()
            if (
                fallback_model_directory != default_model_directory()
                and models_ready(fallback_model_directory)
            ):
                target.setValue(MODEL_DIRECTORY_SETTING, str(fallback_model_directory))

        target.setValue(SETTINGS_MIGRATION_VERSION_KEY, SETTINGS_MIGRATION_VERSION)
        target.sync()
        return True
    except (RuntimeError, TypeError, ValueError, OSError):
        return False
