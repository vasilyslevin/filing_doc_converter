from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class ErrorDetailsDialog(QDialog):
    def __init__(self, details: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Processing failure details")
        self.resize(720, 420)

        message = QLabel(
            "The document could not be processed. "
            "Copy the details below when reporting the issue."
        )
        message.setWordWrap(True)

        self.details_edit = QPlainTextEdit()
        self.details_edit.setReadOnly(True)
        self.details_edit.setPlainText(details)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.copy_button = buttons.addButton(
            "Copy Error",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.copy_button.clicked.connect(self.copy_error)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addWidget(self.details_edit)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def copy_error(self) -> None:
        QApplication.clipboard().setText(self.details_edit.toPlainText())
