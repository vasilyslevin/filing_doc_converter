import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Event

from filing_doc_converter.docling_runtime import (
    DoclingRuntimeUnavailableError,
    LocalModelsUnavailableError,
    local_pdf_converter,
)
from filing_doc_converter.ocr_runtime import (
    TesseractRuntimeProfile,
    build_ocr_environment,
    resolve_ocrmypdf_executable,
    resolve_tesseract_profile,
)
from filing_doc_converter.subprocess_utils import background_subprocess_kwargs


class OcrError(RuntimeError):
    """Base error raised by the OCR pipeline."""


class OcrUnavailableError(OcrError):
    """Raised when OCRmyPDF cannot be found."""


class OcrCancelledError(OcrError):
    """Raised when an OCR job is cancelled."""


class DoclingUnavailableError(OcrError):
    """Raised when Docling cannot be imported."""


class DoclingModelsUnavailableError(OcrError):
    """Raised when local Docling model setup is incomplete."""


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
    return resolve_ocrmypdf_executable()


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
    output_stem: str | None = None,
    model_directory: Path | None = None,
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
    if output_stem is not None and (
        not output_stem or Path(output_stem).name != output_stem
    ):
        raise OcrError("Output stem must be a plain filename stem.")

    destination_directory = output_directory.resolve()
    destination_stem = output_stem or source.stem
    markdown_destination = (
        destination_directory / f"{destination_stem}.md" if export_markdown else None
    )
    json_destination = (
        destination_directory / f"{destination_stem}.json" if export_json else None
    )

    for destination in (markdown_destination, json_destination):
        if destination is not None and destination.exists():
            raise OutputCollisionError(
                f"Output already exists and will not be overwritten: {destination}"
            )

    created_paths: list[Path] = []
    try:
        with local_pdf_converter(model_directory) as converter:
            try:
                result = converter.convert(source)
            except Exception as error:
                raise ConversionError(
                    f"Docling conversion failed for {source.name}: {error}"
                ) from error

            if cancel_event is not None and cancel_event.is_set():
                raise OcrCancelledError(f"Processing cancelled: {source.name}")

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
                raise
            except Exception as error:
                raise ConversionError(
                    f"Docling export failed for {source.name}: {error}"
                ) from error
    except LocalModelsUnavailableError as error:
        raise DoclingModelsUnavailableError(str(error)) from error
    except DoclingRuntimeUnavailableError as error:
        raise DoclingUnavailableError(str(error)) from error
    except OcrError:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    except Exception as error:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise ConversionError(
            f"Docling conversion failed for {source.name}: {error}"
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
    tesseract_profile: TesseractRuntimeProfile | None = None,
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
    profile = tesseract_profile or resolve_tesseract_profile()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=build_ocr_environment(profile),
        **background_subprocess_kwargs(),
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
        stderr_text = (stderr or "").strip()
        stdout_text = (stdout or "").strip()
        detail = stderr_text or stdout_text or "Unknown OCRmyPDF error"
        if stderr_text and stdout_text and stderr_text != stdout_text:
            detail = f"{stderr_text}\n\n{stdout_text}"
        raise OcrError(
            f"OCRmyPDF failed for {source.name} (exit code {process.returncode}): {detail}"
        )
    if not destination.is_file():
        raise OcrError(f"OCRmyPDF completed without creating: {destination}")

    return OcrResult(
        input_path=source,
        output_path=destination,
        command=tuple(command),
        stdout=stdout,
        stderr=stderr,
    )
