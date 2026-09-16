from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QWidget

PRIVACY_NOTICE_KEY = "privacy/notice_version"
PRIVACY_NOTICE_VERSION = 1
PRIVACY_NOTICE_TEXT = """Documents stay on this computer during conversion.

The application does not include telemetry or automatically upload documents, filenames, extracted text, or generated outputs.

Markdown and JSON conversion requires local AI model files. Those generic model files are downloaded only after you choose Download Models in Help > System Check and approve the download. Model-hosting services may receive ordinary connection metadata such as your IP address and request time, but the downloader is not given a document.

After model setup, conversion is configured to use local artifacts with remote services disabled. An operating-system firewall remains the strongest enforcement boundary for highly sensitive work."""


def show_first_run_privacy_notice(
    parent: QWidget | None = None,
    *,
    settings: QSettings | None = None,
) -> bool:
    active_settings = settings if settings is not None else QSettings()
    try:
        acknowledged_version = int(active_settings.value(PRIVACY_NOTICE_KEY, 0))
    except (TypeError, ValueError):
        acknowledged_version = 0
    if acknowledged_version >= PRIVACY_NOTICE_VERSION:
        return False

    QMessageBox.information(
        parent,
        "Privacy and local processing",
        PRIVACY_NOTICE_TEXT,
    )
    active_settings.setValue(PRIVACY_NOTICE_KEY, PRIVACY_NOTICE_VERSION)
    active_settings.sync()
    return True
