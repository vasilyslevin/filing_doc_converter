from pathlib import Path

import pytest

from filing_doc_converter import ocr_pipeline
from filing_doc_converter.ocr_pipeline import (
    OcrError,
    OcrUnavailableError,
    build_ocr_command,
    run_ocr,
    searchable_output_path,
)


def test_searchable_output_path() -> None:
    result = searchable_output_path(Path("filing.pdf"), Path("Converted"))

    assert result == Path("Converted/filing.searchable.pdf")


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
        "Converted/filing with spaces.searchable.pdf",
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
