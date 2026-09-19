from pathlib import Path

from PySide6.QtCore import QSettings

from source_doc_converter import privacy_notice
from source_doc_converter.privacy_notice import (
    PRIVACY_NOTICE_KEY,
    PRIVACY_NOTICE_VERSION,
    show_first_run_privacy_notice,
)


def make_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_first_run_notice_is_shown_and_remembered(monkeypatch, qtbot, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    messages = []
    monkeypatch.setattr(
        privacy_notice.QMessageBox,
        "information",
        lambda parent, title, text: messages.append((title, text)),
    )

    shown = show_first_run_privacy_notice(settings=settings)

    assert shown
    assert len(messages) == 1
    assert "Documents stay on this computer" in messages[0][1]
    assert "model files are downloaded only after" in messages[0][1]
    assert settings.value(PRIVACY_NOTICE_KEY, type=int) == PRIVACY_NOTICE_VERSION


def test_acknowledged_notice_is_not_repeated(monkeypatch, qtbot, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.setValue(PRIVACY_NOTICE_KEY, PRIVACY_NOTICE_VERSION)
    messages = []
    monkeypatch.setattr(
        privacy_notice.QMessageBox,
        "information",
        lambda *args: messages.append(args),
    )

    shown = show_first_run_privacy_notice(settings=settings)

    assert not shown
    assert messages == []


def test_notice_contains_no_user_or_document_path() -> None:
    text = privacy_notice.PRIVACY_NOTICE_TEXT

    assert "C:" not in text
    assert "/home/" not in text
    assert ".pdf" not in text
