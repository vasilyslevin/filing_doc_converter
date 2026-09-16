import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Event


class OcrError(RuntimeError):
    """Base error raised by the OCR pipeline."""


class OcrUnavailableError(OcrError):
    """Raised when OCRmyPDF cannot be found."""


class OcrCancelledError(OcrError):
    """Raised when an OCR job is cancelled."""


class DoclingUnavailableError(OcrError):
    """Raised when Docling cannot be imported."""


class ConversionError(OcrError):
    """Raised when conversion to markdown or JSON fails."""


class OutputCollisionError(OcrError):
    """Raised when one or more output files already exist."""


@dataclass(frozen=True)
class OcrResult:
    input_path: Path
    output_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str


@dataclass(frozen=True)
class DoclingResult:
    input_path: Path
    markdown_path: Path | None
    json_path: Path | None


def find_ocrmypdf() -> str | None:
    return shutil.which("ocrmypdf")


def searchable_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.searchable.pdf"


def markdown_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.md"


def json_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.json"


def build_ocr_command(
    input_path: Path,
    output_path: Path,
    *,
    executable: str = "ocrmypdf",
    language: str = "eng",
) -> list[str]:
    return [
        executable,
        "--output-type",
        "pdf",
        "--mode",
        "skip",
        "--rotate-pages",
        "--deskew",
        "--language",
        language,
        str(input_path),
        str(output_path),
    ]


def _load_docling_converter_class():
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as error:
        raise DoclingUnavailableError(
            "Docling was not found. Install the Docling optional dependencies and try again."
        ) from error
    return DocumentConverter


def _write_text_atomic(destination: Path, content: str) -> None:
    if destination.exists():
        raise OutputCollisionError(
            f"Output already exists and will not be overwritten: {destination}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            errors="strict",
            dir=destination.parent,
            delete=False,
            newline="\n",
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)

        if destination.exists():
            raise OutputCollisionError(
                f"Output already exists and will not be overwritten: {destination}"
            )
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def run_docling(
    input_path: Path,
    output_directory: Path,
    *,
    export_markdown: bool,
    export_json: bool,
    cancel_event: Event | None = None,
) -> DoclingResult:
    source = input_path.resolve()
    if not source.is_file():
        raise OcrError(f"Input PDF does not exist: {source}")
    if source.suffix.lower() != ".pdf":
        raise OcrError(f"Input is not a PDF: {source}")
    if not (export_markdown or export_json):
        raise OcrError("No Docling output format was requested.")
    if cancel_event is not None and cancel_event.is_set():
        raise OcrCancelledError(f"Processing cancelled: {source.name}")

    destination_directory = output_directory.resolve()
    markdown_destination = (
        markdown_output_path(source, destination_directory) if export_markdown else None
    )
    json_destination = json_output_path(source, destination_directory) if export_json else None

    for destination in (markdown_destination, json_destination):
        if destination is not None and destination.exists():
            raise OutputCollisionError(
                f"Output already exists and will not be overwritten: {destination}"
            )

    converter_class = _load_docling_converter_class()
    converter = converter_class()
    try:
        result = converter.convert(str(source))
    except Exception as error:
        raise ConversionError(f"Docling conversion failed for {source.name}: {error}") from error

    if cancel_event is not None and cancel_event.is_set():
        raise OcrCancelledError(f"Processing cancelled: {source.name}")

    created_paths: list[Path] = []
    try:
        if markdown_destination is not None:
            markdown = result.document.export_to_markdown(
                page_break_placeholder="<!-- PDF_PAGE_BREAK -->"
            )
            _write_text_atomic(markdown_destination, markdown)
            created_paths.append(markdown_destination)

        if json_destination is not None:
            exported = result.document.export_to_dict()
            payload = json.dumps(exported, ensure_ascii=False, indent=2)
            _write_text_atomic(json_destination, payload)
            created_paths.append(json_destination)
    except OcrError:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    except Exception as error:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise ConversionError(
            f"Docling export failed for {source.name}: {error}"
        ) from error

    return DoclingResult(
        input_path=source,
        markdown_path=markdown_destination,
        json_path=json_destination,
    )


def run_ocr(
    input_path: Path,
    output_directory: Path,
    *,
    language: str = "eng",
    executable: str | None = None,
    cancel_event: Event | None = None,
) -> OcrResult:
    source = input_path.resolve()
    if not source.is_file():
        raise OcrError(f"Input PDF does not exist: {source}")
    if source.suffix.lower() != ".pdf":
        raise OcrError(f"Input is not a PDF: {source}")

    resolved_executable = executable or find_ocrmypdf()
    if not resolved_executable:
        raise OcrUnavailableError(
            "OCRmyPDF was not found. Install the OCR optional dependencies and try again."
        )

    destination_directory = output_directory.resolve()
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = searchable_output_path(source, destination_directory)
    if destination.exists():
        raise OcrError(f"Output already exists and will not be overwritten: {destination}")

    command = build_ocr_command(
        source,
        destination,
        executable=resolved_executable,
        language=language,
    )
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                destination.unlink(missing_ok=True)
                raise OcrCancelledError(f"OCR cancelled: {source.name}") from None

    if process.returncode != 0:
        destination.unlink(missing_ok=True)
        detail = stderr.strip() or stdout.strip() or "Unknown OCRmyPDF error"
        raise OcrError(f"OCRmyPDF failed for {source.name}: {detail}")
    if not destination.is_file():
        raise OcrError(f"OCRmyPDF completed without creating: {destination}")

    return OcrResult(
        input_path=source,
        output_path=destination,
        command=tuple(command),
        stdout=stdout,
        stderr=stderr,
    )
