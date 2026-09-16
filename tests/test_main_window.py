from pathlib import Path

from filing_doc_converter.main_window import MainWindow


def make_pdf(path: Path) -> Path:
    path.write_bytes(b"%PDF-1.4\n")
    return path


def test_window_launches(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Filing Document Converter"
    assert window.queue.count() == 0
    assert window.searchable_pdf_checkbox.isChecked()
    assert window.markdown_checkbox.isEnabled()
    assert window.json_checkbox.isEnabled()
    assert not window.process_button.isEnabled()
    assert not window.cancel_button.isEnabled()


def test_adds_only_unique_pdf_files(qtbot, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "filing.pdf")
    text = tmp_path / "notes.txt"
    text.write_text("not a PDF", encoding="utf-8")

    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(pdf), str(pdf), str(text)])

    assert window.pdf_paths == (pdf.resolve(),)
    assert window.queue.count() == 1
    assert window.output_directory == (tmp_path / "Converted").resolve()
    assert window.process_button.isEnabled()


def test_adds_pdfs_from_folder(qtbot, tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = make_pdf(tmp_path / "first.pdf")
    second = make_pdf(nested / "second.PDF")

    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(tmp_path)])

    assert set(window.pdf_paths) == {first.resolve(), second.resolve()}
    assert window.queue.count() == 2


def test_process_requires_any_output_selection(qtbot, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "filing.pdf")
    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(pdf)])

    window.searchable_pdf_checkbox.setChecked(False)
    assert not window.process_button.isEnabled()

    window.markdown_checkbox.setChecked(True)
    assert window.process_button.isEnabled()


def test_clear_disables_processing(qtbot, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "filing.pdf")
    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(pdf)])

    window.clear_queue()

    assert window.pdf_paths == ()
    assert not window.process_button.isEnabled()
