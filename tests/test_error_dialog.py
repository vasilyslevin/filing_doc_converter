from PySide6.QtWidgets import QApplication

from filing_doc_converter.error_dialog import ErrorDetailsDialog


def test_error_details_are_selectable_and_copyable(qtbot) -> None:
    dialog = ErrorDetailsDialog("full error details")
    qtbot.addWidget(dialog)

    assert dialog.details_edit.isReadOnly()
    assert dialog.details_edit.toPlainText() == "full error details"

    dialog.copy_button.click()

    assert QApplication.clipboard().text() == "full error details"
