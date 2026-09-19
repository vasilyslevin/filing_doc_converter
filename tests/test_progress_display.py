from pathlib import Path

from source_doc_converter.application_window import ApplicationWindow
from source_doc_converter.model_management import ModelDirectoryState
from source_doc_converter.system_diagnostics import OutputAvailability


def test_progress_is_busy_while_document_is_processing(qtbot) -> None:
    window = ApplicationWindow(
        availability_provider=lambda: OutputAvailability(False, False),
        model_state_provider=lambda: ModelDirectoryState(Path("models"), "settings", False),
    )
    qtbot.addWidget(window)
    window.queue.addItem("filing.pdf")
    window._pdf_paths.append(Path("filing.pdf"))

    window._on_file_started(1, 1, "filing.pdf")

    assert window.progress_bar.minimum() == 0
    assert window.progress_bar.maximum() == 0
    assert window.progress_bar.format() == "Processing 1 of 1: filing.pdf"

    window._on_file_failed("filing.pdf", "test error")

    assert window.progress_bar.maximum() == 1
    assert window.progress_bar.value() == 1
