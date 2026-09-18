import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.model_management import (
    resolve_model_downloader,
)
from filing_doc_converter.privacy_notice import show_first_run_privacy_notice

PACKAGE_SMOKE_TEST_FLAG = "--package-smoke-test"


def prepare_packaged_path() -> None:
    pass


def run_package_smoke_test() -> int:
    window = ApplicationWindow()
    window.close()
    resolve_model_downloader()
    return 0


def main() -> int:
    prepare_packaged_path()
    smoke_test = PACKAGE_SMOKE_TEST_FLAG in sys.argv
    arguments = [argument for argument in sys.argv if argument != PACKAGE_SMOKE_TEST_FLAG]
    application = QApplication(arguments)
    application.setOrganizationName("FilingDocumentConverter")
    application.setApplicationName("Filing Document Converter")
    icon_path = Path(__file__).parent / "assets" / "app_icon.svg"
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
    if smoke_test:
        return run_package_smoke_test()

    window = ApplicationWindow()
    window.show()
    show_first_run_privacy_notice(window)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
