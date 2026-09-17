from pathlib import Path

from PySide6.QtWidgets import QListWidgetItem

from filing_doc_converter import application_window
from filing_doc_converter.application_window import ApplicationWindow
from filing_doc_converter.model_management import ModelDirectoryState
from filing_doc_converter.system_diagnostics import OutputAvailability


def test_clicking_failed_item_shows_stored_error(monkeypatch, qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(False, False),
        model_state_provider=lambda: ModelDirectoryState(Path("models"), "settings", False),
    )
    qtbot.addWidget(window)
    item = QListWidgetItem("Failed: filing.pdf")
    item.setToolTip("Could not import module AutoImageProcessor")
    window.queue.addItem(item)
    dialogs = []

    class FakeDialog:
        def __init__(self, details, parent) -> None:
            dialogs.append((details, parent))

        def exec(self) -> None:
            dialogs.append("shown")

    monkeypatch.setattr(application_window, "ErrorDetailsDialog", FakeDialog)

    window.queue.itemClicked.emit(item)

    assert dialogs == [
        ("Could not import module AutoImageProcessor", window),
        "shown",
    ]
