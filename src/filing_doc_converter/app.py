import sys

from PySide6.QtWidgets import QApplication

from filing_doc_converter.application_window import ApplicationWindow


def main() -> int:
    application = QApplication(sys.argv)
    window = ApplicationWindow()
    window.show()
    return application.exec()
