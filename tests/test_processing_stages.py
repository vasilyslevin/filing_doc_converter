from pathlib import Path

from source_doc_converter import ocr_worker
from source_doc_converter.application_window import format_elapsed
from source_doc_converter.ocr_pipeline import DoclingResult, OcrResult
from source_doc_converter.ocr_worker import ProcessingWorker


def test_elapsed_time_formatting() -> None:
    assert format_elapsed(0) == "00:00"
    assert format_elapsed(65_000) == "01:05"
    assert format_elapsed(3_661_000) == "1:01:01"


def test_worker_reports_ocr_and_docling_stages(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    searchable = output_directory / "filing.searchable.pdf"
    markdown = output_directory / "filing.md"

    monkeypatch.setattr(
        ocr_worker,
        "run_ocr",
        lambda *args, **kwargs: OcrResult(source, searchable, (), "", ""),
    )
    monkeypatch.setattr(
        ocr_worker,
        "run_docling",
        lambda *args, **kwargs: DoclingResult(searchable, markdown, None),
    )
    worker = ProcessingWorker(
        (source,),
        output_directory,
        create_searchable_pdf=True,
        create_markdown=True,
        create_json=False,
        executable="ocrmypdf",
    )
    stages = []
    worker.stage_changed.connect(stages.append)

    worker.run()

    assert stages[0].startswith("Runtime: OCR workers=")
    assert stages[1:5] == [
        "Running OCRmyPDF",
        "OCR mode: Skip OCR",
        "Loading models and analyzing pages",
        "AI analysis mode: accurate",
    ]
    assert "Finalizing Markdown/JSON outputs" in stages
    assert stages[-1].startswith("Timing: Total batch ")
