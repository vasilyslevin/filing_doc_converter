from contextlib import contextmanager
from pathlib import Path

import pytest

from filing_doc_converter import ocr_pipeline
from filing_doc_converter.docling_runtime import LocalModelsUnavailableError
from filing_doc_converter.ocr_pipeline import (
    ConversionError,
    DoclingModelsUnavailableError,
    OcrError,
    OcrPageAnalysis,
    OcrUnavailableError,
    OutputCollisionError,
    build_ocr_command,
    json_output_path,
    markdown_output_path,
    normalize_ocr_mode,
    ocr_mode_label,
    plan_ocr_command,
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
        "--skip-text",
        "--rotate-pages",
        "--deskew",
        "--language",
        "eng",
        "filing with spaces.pdf",
        str(Path("Converted") / "filing with spaces.searchable.pdf"),
    ]


def test_plan_ocr_command_uses_mode_specific_flags() -> None:
    skip_plan = plan_ocr_command(Path("in.pdf"), Path("out.pdf"), mode="skip")
    redo_plan = plan_ocr_command(Path("in.pdf"), Path("out.pdf"), mode="redo")
    force_plan = plan_ocr_command(Path("in.pdf"), Path("out.pdf"), mode="force")

    assert "--skip-text" in skip_plan.command
    assert "--redo-ocr" in redo_plan.command
    assert "--force-ocr" in force_plan.command


def test_redo_mode_reports_incompatible_preprocessing_options() -> None:
    plan = plan_ocr_command(Path("in.pdf"), Path("out.pdf"), mode="redo")

    assert "--rotate-pages" not in plan.command
    assert "--deskew" not in plan.command
    assert any("incompatible with --rotate-pages" in item for item in plan.warnings)
    assert any("incompatible with --deskew" in item for item in plan.warnings)


def test_ocr_mode_normalization_and_label() -> None:
    assert normalize_ocr_mode("Skip existing text") == "skip"
    assert normalize_ocr_mode("redo_ocr") == "redo"
    assert ocr_mode_label("smart") == "Smart legal document (recommended)"


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
        lambda profile: {"PATH": "bundle", "TESSDATA_PREFIX": "bundle/tessdata"},
    )
    monkeypatch.setattr(ocr_pipeline, "resolve_tesseract_profile", lambda: object())
    monkeypatch.setattr(ocr_pipeline.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(ocr_pipeline, "_validate_pdf_text", lambda *_args, **_kwargs: None)

    result = run_ocr(source, output_directory)

    assert result.command[0] == "/tools/ocrmypdf"
    assert captured["env"] == {"PATH": "bundle", "TESSDATA_PREFIX": "bundle/tessdata"}


def test_run_ocr_failure_includes_exit_code_and_full_output(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "filing.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    class FailedProcess:
        returncode = 4

        def __init__(self, *args, **kwargs):
            pass

        def communicate(self, timeout=None):
            return ("stdout text", "stderr text")

    monkeypatch.setattr(ocr_pipeline, "find_ocrmypdf", lambda: "/tools/ocrmypdf")
    monkeypatch.setattr(ocr_pipeline, "resolve_tesseract_profile", lambda: None)
    monkeypatch.setattr(ocr_pipeline, "build_ocr_environment", lambda profile: {})
    monkeypatch.setattr(ocr_pipeline.subprocess, "Popen", FailedProcess)
    monkeypatch.setattr(ocr_pipeline, "_validate_pdf_text", lambda *_args, **_kwargs: None)

    with pytest.raises(OcrError, match=r"exit code 4"):
        run_ocr(source, tmp_path / "output")


def test_smart_mode_retries_with_redo_on_header_only_detection(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "synthetic_header_body.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    output_directory = tmp_path / "output"
    calls: list[tuple[str, ...]] = []
    validations = iter(
        (
            ocr_pipeline.OcrValidationReport((), (1, 2), (), ("weak pages",)),
            ocr_pipeline.OcrValidationReport((1, 2), (), (), ()),
        )
    )

    class FakeProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append(tuple(command))
            Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(command[-1]).write_bytes(b"%PDF-1.4\n")

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(ocr_pipeline, "find_ocrmypdf", lambda: "/tools/ocrmypdf")
    monkeypatch.setattr(ocr_pipeline, "resolve_tesseract_profile", lambda: None)
    monkeypatch.setattr(ocr_pipeline, "build_ocr_environment", lambda profile: {})
    monkeypatch.setattr(ocr_pipeline.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(ocr_pipeline, "_validate_pdf_text", lambda *_args, **_kwargs: next(validations))

    result = run_ocr(source, output_directory, mode="smart")

    assert len(calls) == 2
    assert "--skip-text" in calls[0]
    assert "--redo-ocr" in calls[1]
    assert result.effective_mode == "redo"
    assert any("retrying with Redo OCR" in warning for warning in result.warnings)


def test_validation_warning_recommends_retry_for_skip_mode(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "header_only.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    class FakeProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(command[-1]).write_bytes(b"%PDF-1.4\n")

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(ocr_pipeline, "find_ocrmypdf", lambda: "/tools/ocrmypdf")
    monkeypatch.setattr(ocr_pipeline, "resolve_tesseract_profile", lambda: None)
    monkeypatch.setattr(ocr_pipeline, "build_ocr_environment", lambda profile: {})
    monkeypatch.setattr(ocr_pipeline.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(
        ocr_pipeline,
        "_validate_pdf_text",
        lambda *_args, **_kwargs: ocr_pipeline.OcrValidationReport((), (1,), (), ("weak page",)),
    )

    result = run_ocr(source, tmp_path / "output", mode="skip")

    assert any("Skip is fastest" in warning for warning in result.warnings)
    assert any("Consider retrying with Redo OCR or Force OCR" in warning for warning in result.warnings)


def test_blank_pages_are_not_reported_as_weak(monkeypatch) -> None:
    monkeypatch.setattr(
        ocr_pipeline,
        "_analyze_pdf_pages",
        lambda _path: (
            OcrPageAnalysis(page_number=1, text="", has_raster_content=False),
            OcrPageAnalysis(page_number=2, text="", has_raster_content=False),
        ),
    )

    report = ocr_pipeline._validate_pdf_text(Path("ignored.pdf"))

    assert report is not None
    assert report.blank_pages == (1, 2)
    assert report.weak_pages == ()


def test_header_only_false_positive_is_detected(monkeypatch) -> None:
    header = "Case 1:23-cv-00001 Doc 12 Filed 10/02/2026 Page 1 of 2"
    monkeypatch.setattr(
        ocr_pipeline,
        "_analyze_pdf_pages",
        lambda _path: (
            OcrPageAnalysis(page_number=1, text=header, has_raster_content=False),
        ),
    )

    report = ocr_pipeline._validate_pdf_text(Path("ignored.pdf"))

    assert report is not None
    assert report.weak_pages == (1,)


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
