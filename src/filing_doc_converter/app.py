import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Filing Document Converter")
        self.resize(720, 480)

        status = QLabel("Work in progress", alignment=None)
        status.setStyleSheet("font-size: 20px;")
        status.setMargin(32)
        self.setCentralWidget(status)


def main() -> int:
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()
