import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from filing_doc_converter.application_window import ApplicationWindow


def main() -> int:
    application = QApplication(sys.argv)
    icon_path = Path(__file__).parent / "assets" / "app_icon.svg"
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
    window = ApplicationWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
