from contextlib import contextmanager
from pathlib import Path

import pytest

from filing_doc_converter import ocr_pipeline
from filing_doc_converter.docling_runtime import LocalModelsUnavailableError
from filing_doc_converter.ocr_pipeline import (
    ConversionError,
    DoclingModelsUnavailableError,
    OcrError,
    OcrUnavailableError,
    OutputCollisionError,
    build_ocr_command,
    json_output_path,
    markdown_output_path,
    run_docling,
    run_ocr,
    searchable_output_path,
)


def fake_converter_context(monkeypatch, converter) -> None:
    @contextmanager
    def factory(model_directory=None):
        yield converter

    monkeypatch.setattr(ocr_pipeline, "local_pdf_converter", factory)


def test_searchable_output_path() -> None:
    result = searchable_output_path(Path("filing.pdf"), Path("Converted"))

    assert result == Path("Converted/filing.searchable.pdf")


def test_markdown_output_path() -> None:
    assert markdown_output_path(Path("filing.pdf"), Path("Converted")) == Path(
        "Converted/filing.md"
    )


def test_json_output_path() -> None:
    assert json_output_path(Path("filing.pdf"), Path("Converted")) == Path(
        "Converted/filing.json"
    )


def test_build_ocr_command_uses_safe_argument_list() -> None:
    command = build_ocr_command(
        Path("filing with spaces.pdf"),
        Path("Converted/filing with spaces.searchable.pdf"),
        executable="/tools/ocrmypdf",
        language="eng",
    )

    assert command == [
        "/tools/ocrmypdf",
        "--output-type",
        "pdf",
        "--mode",
        "skip",
        "--rotate-pages",
        "--deskew",
        "--language",
        "eng",
        "filing with spaces.pdf",
        str(Path("Converted") / "filing with spaces.searchable.pdf"),
    ]


def test_missing_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(OcrError, match="does not exist"):
        run_ocr(tmp_path / "missing.pdf", tmp_path / "output", executable="ocrmypdf")


def test_missing_ocrmypdf_is_reported(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(ocr_pipeline, "find_ocrmypdf", lambda: None)

    with pytest.raises(OcrUnavailableError, match="not found"):
        run_ocr(source, tmp_path / "output")


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    destination = output_directory / "filing.searchable.pdf"
    destination.write_bytes(b"existing")

    with pytest.raises(OcrError, match="will not be overwritten"):
        run_ocr(source, output_directory, executable="ocrmypdf")

    assert destination.read_bytes() == b"existing"


def test_run_ocr_uses_subprocess_environment(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    captured: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs.get("env")
            Path(command[-1]).write_bytes(b"%PDF-1.4\n")

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(ocr_pipeline, "find_ocrmypdf", lambda: "/tools/ocrmypdf")
    monkeypatch.setattr(
        ocr_pipeline,
        "build_ocr_environment",
        lambda: {"PATH": "bundle", "TESSDATA_PREFIX": "bundle/tessdata"},
    )
    monkeypatch.setattr(ocr_pipeline.subprocess, "Popen", FakeProcess)

    result = run_ocr(source, output_directory)

    assert result.command[0] == "/tools/ocrmypdf"
    assert captured["env"] == {"PATH": "bundle", "TESSDATA_PREFIX": "bundle/tessdata"}


def test_docling_missing_models_are_reported(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    @contextmanager
    def unavailable(model_directory=None):
        raise LocalModelsUnavailableError("Open Help > System Check and Download Models")
        yield

    monkeypatch.setattr(ocr_pipeline, "local_pdf_converter", unavailable)

    with pytest.raises(DoclingModelsUnavailableError, match="Download Models"):
        run_docling(
            source,
            tmp_path / "output",
            export_markdown=True,
            export_json=False,
        )


def test_docling_outputs_are_exported_with_expected_options(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    captured: dict[str, str] = {}

    class FakeDocument:
        def export_to_markdown(self, *, page_break_placeholder: str) -> str:
            captured["page_break_placeholder"] = page_break_placeholder
            return "markdown body"

        def export_to_dict(self) -> dict[str, str]:
            return {"key": "значение"}

    class FakeResult:
        document = FakeDocument()

    class FakeConverter:
        def convert(self, input_path: Path) -> FakeResult:
            captured["converted_path"] = str(input_path)
            return FakeResult()

    fake_converter_context(monkeypatch, FakeConverter())

    result = run_docling(
        source,
        output_directory,
        export_markdown=True,
        export_json=True,
    )

    markdown_file = output_directory / "filing.md"
    json_file = output_directory / "filing.json"
    assert result.markdown_path == markdown_file
    assert result.json_path == json_file
    assert markdown_file.read_text(encoding="utf-8") == "markdown body"
    assert '"значение"' in json_file.read_text(encoding="utf-8")
    assert captured == {
        "converted_path": str(source.resolve()),
        "page_break_placeholder": "<!-- PDF_PAGE_BREAK -->",
    }


def test_docling_refuses_to_overwrite_existing_output(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    markdown_file = output_directory / "filing.md"
    markdown_file.write_text("existing", encoding="utf-8")

    class FakeConverter:
        def convert(self, input_path: Path) -> None:
            raise AssertionError(f"Should not convert {input_path}")

    fake_converter_context(monkeypatch, FakeConverter())

    with pytest.raises(OutputCollisionError, match="will not be overwritten"):
        run_docling(
            source,
            output_directory,
            export_markdown=True,
            export_json=False,
        )

    assert markdown_file.read_text(encoding="utf-8") == "existing"


def test_docling_export_failure_cleans_partial_outputs(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    output_directory.mkdir()

    class FakeDocument:
        def export_to_markdown(self, *, page_break_placeholder: str) -> str:
            return f"ok-{page_break_placeholder}"

        def export_to_dict(self) -> dict[str, str]:
            raise ValueError("bad json")

    class FakeResult:
        document = FakeDocument()

    class FakeConverter:
        def convert(self, input_path: Path) -> FakeResult:
            return FakeResult()

    fake_converter_context(monkeypatch, FakeConverter())

    with pytest.raises(ConversionError, match="Docling export failed"):
        run_docling(
            source,
            output_directory,
            export_markdown=True,
            export_json=True,
        )

    assert not (output_directory / "filing.md").exists()
    assert not (output_directory / "filing.json").exists()
