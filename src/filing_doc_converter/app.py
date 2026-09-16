import sys

from PySide6.QtWidgets import QApplication

from filing_doc_converter.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()
