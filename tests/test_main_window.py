from pathlib import Path

from filing_doc_converter.main_window import MainWindow


def test_window_launches(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Filing Document Converter"
    assert window.queue.count() == 0


def test_adds_only_unique_pdf_files(qtbot, tmp_path: Path) -> None:
    pdf = tmp_path / "filing.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    text = tmp_path / "notes.txt"
    text.write_text("not a PDF", encoding="utf-8")

    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(pdf), str(pdf), str(text)])

    assert window.pdf_paths == (pdf.resolve(),)
    assert window.queue.count() == 1


def test_adds_pdfs_from_folder(qtbot, tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = tmp_path / "first.pdf"
    second = nested / "second.PDF"
    first.write_bytes(b"%PDF-1.4\n")
    second.write_bytes(b"%PDF-1.4\n")

    window = MainWindow()
    qtbot.addWidget(window)
    window.add_paths([str(tmp_path)])

    assert set(window.pdf_paths) == {first.resolve(), second.resolve()}
    assert window.queue.count() == 2
