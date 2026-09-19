from contextlib import nullcontext
from pathlib import Path

from source_doc_converter import ocr_pipeline, ocr_worker
from source_doc_converter.docling_runtime import ConverterBuildMetrics
from source_doc_converter.ocr_pipeline import DoclingResult, OcrResult, run_docling
from source_doc_converter.ocr_worker import ProcessingWorker


def test_docling_uses_original_stem_for_combined_outputs(monkeypatch, tmp_path: Path) -> None:
    searchable = tmp_path / "case.record.searchable.pdf"
    searchable.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    output_directory.mkdir()

    class FakeDocument:
        def export_to_markdown(self, *, page_break_placeholder: str) -> str:
            return f"body-{page_break_placeholder}"

        def export_to_dict(self) -> dict[str, str]:
            return {"status": "ok"}

    class FakeResult:
        document = FakeDocument()

    class FakeConverter:
        def convert(self, input_path: Path) -> FakeResult:
            return FakeResult()

    model_dir = tmp_path / "models"
    model_dir.mkdir()
    monkeypatch.setattr(ocr_pipeline, "require_ready_model_directory", lambda _: model_dir)
    monkeypatch.setattr(
        ocr_pipeline,
        "offline_environment",
        lambda *args, **kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        ocr_pipeline,
        "create_local_pdf_converter_with_metrics",
        lambda *args, **kwargs: (
            FakeConverter(),
            ConverterBuildMetrics(cache_hit=False, init_seconds=0.01),
        ),
    )

    result = run_docling(
        searchable,
        output_directory,
        export_markdown=True,
        export_json=True,
        output_stem="case.record",
    )

    assert result.markdown_path == output_directory / "case.record.md"
    assert result.json_path == output_directory / "case.record.json"
    assert not (output_directory / "case.record.searchable.md").exists()
    assert not (output_directory / "case.record.searchable.json").exists()


def test_worker_passes_original_stem_while_docling_reads_searchable_pdf(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "case.record.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    searchable = output_directory / "case.record.searchable.pdf"
    markdown = output_directory / "case.record.md"
    json_file = output_directory / "case.record.json"
    calls: list[tuple[Path, str | None]] = []

    def fake_run_ocr(*args, **kwargs):
        return OcrResult(source, searchable, ("ocrmypdf",), "", "")

    def fake_run_docling(input_path, *args, **kwargs):
        calls.append((input_path, kwargs.get("output_stem")))
        return DoclingResult(input_path, markdown, json_file)

    monkeypatch.setattr(ocr_worker, "run_ocr", fake_run_ocr)
    monkeypatch.setattr(ocr_worker, "run_docling", fake_run_docling)
    worker = ProcessingWorker(
        (source,),
        output_directory,
        create_searchable_pdf=True,
        create_markdown=True,
        create_json=True,
        executable="ocrmypdf",
    )

    worker.run()

    assert calls == [(searchable, "case.record")]
