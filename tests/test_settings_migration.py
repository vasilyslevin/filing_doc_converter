from pathlib import Path

from PySide6.QtCore import QSettings

from source_doc_converter.settings_migration import (
    SETTINGS_MIGRATION_VERSION,
    SETTINGS_MIGRATION_VERSION_KEY,
    migrate_legacy_settings,
)


def make_settings(path: Path) -> QSettings:
    return QSettings(str(path), QSettings.Format.IniFormat)


def test_first_migration_copies_known_values(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")
    source.setValue("processing/ocr_mode", "redo")
    source.setValue("ocr/tesseract_languages", "eng+spa")
    source.sync()

    changed = migrate_legacy_settings(target, source)

    assert changed
    assert str(target.value("processing/ocr_mode", "")) == "redo"
    assert str(target.value("ocr/tesseract_languages", "")) == "eng+spa"
    assert int(target.value(SETTINGS_MIGRATION_VERSION_KEY, 0)) == SETTINGS_MIGRATION_VERSION


def test_repeated_migration_is_idempotent(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")
    source.setValue("processing/ocr_mode", "smart")
    source.sync()
    migrate_legacy_settings(target, source)
    source.setValue("processing/ocr_mode", "redo")
    source.sync()

    changed = migrate_legacy_settings(target, source)

    assert not changed
    assert str(target.value("processing/ocr_mode", "")) == "smart"


def test_existing_new_values_are_not_overwritten(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")
    source.setValue("processing/ocr_mode", "redo")
    target.setValue("processing/ocr_mode", "smart")
    source.sync()
    target.sync()

    migrate_legacy_settings(target, source)

    assert str(target.value("processing/ocr_mode", "")) == "smart"


def test_migration_preserves_value_types(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")
    source.setValue("processing/docling_ocr", True)
    source.setValue("privacy/notice_version", 3)
    source.sync()

    migrate_legacy_settings(target, source)

    assert target.value("processing/docling_ocr", False, type=bool) is True
    assert target.value("privacy/notice_version", 0, type=int) == 3


def test_missing_legacy_settings_still_records_marker(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")

    changed = migrate_legacy_settings(target, source)

    assert changed
    assert int(target.value(SETTINGS_MIGRATION_VERSION_KEY, 0)) == SETTINGS_MIGRATION_VERSION


def test_migration_failure_is_safe(tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    source.setValue("processing/ocr_mode", "smart")
    source.sync()

    class FailingTarget:
        def value(self, *_args, **_kwargs):
            return 0

        def contains(self, *_args, **_kwargs):
            return False

        def setValue(self, *_args, **_kwargs):
            raise RuntimeError("simulated write error")

        def sync(self):
            pass

    changed = migrate_legacy_settings(FailingTarget(), source)

    assert not changed


def test_legacy_model_path_reuse_when_current_missing(monkeypatch, tmp_path: Path) -> None:
    source = make_settings(tmp_path / "legacy.ini")
    target = make_settings(tmp_path / "current.ini")
    legacy_models = (tmp_path / "legacy-models").resolve()
    legacy_models.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "source_doc_converter.settings_migration.legacy_default_model_directory",
        lambda: legacy_models,
    )
    monkeypatch.setattr(
        "source_doc_converter.settings_migration.default_model_directory",
        lambda: (tmp_path / "new-models").resolve(),
    )
    monkeypatch.setattr(
        "source_doc_converter.settings_migration.models_ready",
        lambda path: Path(path).resolve() == legacy_models,
    )

    migrate_legacy_settings(target, source)

    assert str(target.value("models/directory", "")) == str(legacy_models)
