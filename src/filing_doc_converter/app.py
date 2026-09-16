import sys

from PySide6.QtWidgets import QApplication

from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.privacy_notice import show_first_run_privacy_notice


def main() -> int:
    application = QApplication(sys.argv)
    application.setOrganizationName("FilingDocumentConverter")
    application.setApplicationName("Filing Document Converter")
    window = ApplicationWindow()
    window.show()
    show_first_run_privacy_notice(window)
    return application.exec()
