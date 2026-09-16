from pathlib import Path

from filing_doc_converter import ocr_worker
from filing_doc_converter.ocr_pipeline import OcrError, OcrResult
from filing_doc_converter.ocr_worker import OcrWorker


def test_worker_reports_success(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    destination = tmp_path / "output" / "filing.searchable.pdf"

    def fake_run_ocr(*args, **kwargs):
        return OcrResult(source, destination, ("ocrmypdf",), "", "")

    monkeypatch.setattr(ocr_worker, "run_ocr", fake_run_ocr)
    worker = OcrWorker((source,), tmp_path / "output", executable="ocrmypdf")
    successes = []
    summaries = []
    worker.file_succeeded.connect(lambda source_path, output: successes.append((source_path, output)))
    worker.finished.connect(lambda cancelled, ok, failed: summaries.append((cancelled, ok, failed)))

    worker.run()

    assert successes == [(str(source), str(destination))]
    assert summaries == [(False, 1, 0)]


def test_worker_continues_after_failure(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_bytes(b"%PDF-1.4\n")
    second.write_bytes(b"%PDF-1.4\n")

    def fake_run_ocr(input_path, output_directory, **kwargs):
        if input_path == first:
            raise OcrError("test failure")
        destination = output_directory / "second.searchable.pdf"
        return OcrResult(second, destination, ("ocrmypdf",), "", "")

    monkeypatch.setattr(ocr_worker, "run_ocr", fake_run_ocr)
    worker = OcrWorker((first, second), tmp_path / "output", executable="ocrmypdf")
    failures = []
    summaries = []
    worker.file_failed.connect(lambda source_path, error: failures.append((source_path, error)))
    worker.finished.connect(lambda cancelled, ok, failed: summaries.append((cancelled, ok, failed)))

    worker.run()

    assert failures == [(str(first), "test failure")]
    assert summaries == [(False, 1, 1)]


def test_worker_can_be_cancelled_before_start(tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    worker = OcrWorker((source,), tmp_path / "output", executable="ocrmypdf")
    summaries = []
    worker.finished.connect(lambda cancelled, ok, failed: summaries.append((cancelled, ok, failed)))

    worker.cancel()
    worker.run()

    assert summaries == [(True, 0, 0)]
