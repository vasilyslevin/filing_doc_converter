import json
import os
import re
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
    effective_mode: str = "skip"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DoclingResult:
    input_path: Path
    markdown_path: Path | None
    json_path: Path | None


@dataclass(frozen=True)
class OcrCommandPlan:
    requested_mode: str
    effective_mode: str
    command: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class OcrPageAnalysis:
    page_number: int
    text: str
    has_raster_content: bool


@dataclass(frozen=True)
class OcrValidationReport:
    meaningful_pages: tuple[int, ...]
    weak_pages: tuple[int, ...]
    blank_pages: tuple[int, ...]
    warnings: tuple[str, ...]


def find_ocrmypdf() -> str | None:
    return resolve_ocrmypdf_executable()


def normalize_ocr_mode(value: str) -> str:
    mode = value.strip().lower().replace("_", "-")
    aliases = {
        "smart": "smart",
        "smart legal document (recommended)": "smart",
        "skip": "skip",
        "skip existing text": "skip",
        "redo": "redo",
        "redo ocr": "redo",
        "redo-ocr": "redo",
        "force": "force",
        "force ocr": "force",
        "force-ocr": "force",
    }
    return aliases.get(mode, "smart")


def ocr_mode_label(mode: str) -> str:
    labels = {
        "smart": "Smart legal document (recommended)",
        "skip": "Skip existing text",
        "redo": "Redo OCR",
        "force": "Force OCR",
    }
    return labels.get(normalize_ocr_mode(mode), labels["smart"])


def ocr_mode_warning(mode: str) -> str:
    warnings = {
        "skip": "Skip is fastest but can miss scanned bodies under digital headers.",
        "redo": "Redo is intended for mixed pages or unreliable old OCR.",
        "force": "Force rasterizes everything and is the last-resort repair mode.",
    }
    return warnings.get(normalize_ocr_mode(mode), "")


def searchable_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.searchable.pdf"


def markdown_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.md"


def json_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.json"


def plan_ocr_command(
    input_path: Path,
    output_path: Path,
    *,
    executable: str = "ocrmypdf",
    language: str = "eng",
    mode: str = "skip",
    rotate_pages: bool = True,
    deskew: bool = True,
) -> OcrCommandPlan:
    requested_mode = normalize_ocr_mode(mode)
    effective_mode = "skip" if requested_mode == "smart" else requested_mode
    warnings: list[str] = []
    command = [
        executable,
        "--output-type",
        "pdf",
    ]
    if effective_mode == "skip":
        command.append("--skip-text")
    elif effective_mode == "redo":
        command.append("--redo-ocr")
    elif effective_mode == "force":
        command.append("--force-ocr")

    if effective_mode == "redo":
        if rotate_pages:
            warnings.append("Redo OCR is incompatible with --rotate-pages; rotation is disabled.")
        if deskew:
            warnings.append("Redo OCR is incompatible with --deskew; deskew is disabled.")
    else:
        if rotate_pages:
            command.append("--rotate-pages")
        if deskew:
            command.append("--deskew")

    command.extend([
        "--language",
        language,
        str(input_path),
        str(output_path),
    ])
    return OcrCommandPlan(
        requested_mode=requested_mode,
        effective_mode=effective_mode,
        command=tuple(command),
        warnings=tuple(warnings),
    )


def build_ocr_command(
    input_path: Path,
    output_path: Path,
    *,
    executable: str = "ocrmypdf",
    language: str = "eng",
    mode: str = "skip",
) -> list[str]:
    return list(
        plan_ocr_command(
            input_path,
            output_path,
            executable=executable,
            language=language,
            mode=mode,
        ).command
    )


def _header_line(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return (
        "case" in normalized
        and "doc" in normalized
        and "filed" in normalized
        and "page" in normalized
        and " of " in normalized
    )


def _meaningful_body_text(page_text: str) -> bool:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    body_lines = [line for index, line in enumerate(lines) if not (index < 3 and _header_line(line))]
    body = " ".join(body_lines)
    tokens = re.findall(r"[A-Za-z0-9]{3,}", body)
    return len(tokens) >= 8


def _analyze_pdf_pages(pdf_path: Path) -> tuple[OcrPageAnalysis, ...]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ()

    reader = PdfReader(str(pdf_path))
    pages: list[OcrPageAnalysis] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        has_raster = False
        try:
            resources = page.get("/Resources")
            if resources:
                xobject = resources.get("/XObject")
                if xobject:
                    for candidate in xobject.values():
                        obj = candidate.get_object()
                        if str(obj.get("/Subtype")) == "/Image":
                            has_raster = True
                            break
        except (AttributeError, KeyError, TypeError, ValueError):
            has_raster = False
        pages.append(
            OcrPageAnalysis(
                page_number=index,
                text=text,
                has_raster_content=has_raster,
            )
        )
    return tuple(pages)


def _validate_pdf_text(pdf_path: Path) -> OcrValidationReport | None:
    analyses = _analyze_pdf_pages(pdf_path)
    if not analyses:
        return None

    meaningful: list[int] = []
    weak: list[int] = []
    blank: list[int] = []

    for page in analyses:
        stripped = page.text.strip()
        if not stripped and not page.has_raster_content:
            blank.append(page.page_number)
            continue
        if _meaningful_body_text(page.text):
            meaningful.append(page.page_number)
            continue
        header_only = any(_header_line(line.strip()) for line in page.text.splitlines() if line.strip())
        if page.has_raster_content or header_only:
            weak.append(page.page_number)

    warnings: list[str] = []
    if weak:
        page_list = ", ".join(str(page) for page in weak)
        warnings.append(
            f"Post-OCR validation: pages {page_list} still appear to lack meaningful body text."
        )
    return OcrValidationReport(
        meaningful_pages=tuple(meaningful),
        weak_pages=tuple(weak),
        blank_pages=tuple(blank),
        warnings=tuple(warnings),
    )


def _execute_ocr_command(
    command: tuple[str, ...],
    source: Path,
    destination: Path,
    *,
    profile: TesseractRuntimeProfile | None,
    cancel_event: Event | None,
) -> tuple[str, str]:
    process = subprocess.Popen(
        list(command),
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
    return stdout, stderr


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
    mode: str = "smart",
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

    requested_mode = normalize_ocr_mode(mode)
    profile = tesseract_profile or resolve_tesseract_profile()
    plan = plan_ocr_command(
        source,
        destination,
        executable=resolved_executable,
        language=language,
        mode=requested_mode,
    )
    warnings: list[str] = list(plan.warnings)
    mode_tip = ocr_mode_warning(plan.effective_mode)
    if mode_tip:
        warnings.append(mode_tip)

    stdout, stderr = _execute_ocr_command(
        plan.command,
        source,
        destination,
        profile=profile,
        cancel_event=cancel_event,
    )
    effective_mode = plan.effective_mode
    report = _validate_pdf_text(destination)
    if requested_mode == "smart" and report is not None and report.weak_pages:
        weak_pages = ", ".join(str(page) for page in report.weak_pages)
        warnings.append(
            "Smart mode detected mixed/header-only text on pages "
            + weak_pages
            + "; retrying with Redo OCR."
        )
        destination.unlink(missing_ok=True)
        redo_plan = plan_ocr_command(
            source,
            destination,
            executable=resolved_executable,
            language=language,
            mode="redo",
        )
        warnings.extend(redo_plan.warnings)
        redo_stdout, redo_stderr = _execute_ocr_command(
            redo_plan.command,
            source,
            destination,
            profile=profile,
            cancel_event=cancel_event,
        )
        stdout = f"{stdout}\n\n{redo_stdout}".strip()
        stderr = f"{stderr}\n\n{redo_stderr}".strip()
        plan = redo_plan
        effective_mode = "redo"
        report = _validate_pdf_text(destination)

    if report is not None:
        warnings.extend(report.warnings)
        if report.weak_pages:
            recommended = "Force OCR" if effective_mode == "redo" else "Redo OCR or Force OCR"
            warnings.append(
                f"Consider retrying with {recommended} for pages lacking meaningful body text."
            )
    elif requested_mode == "smart":
        warnings.append(
            "Smart OCR validation could not run (install pypdf for per-page validation support)."
        )

    return OcrResult(
        input_path=source,
        output_path=destination,
        command=tuple(plan.command),
        stdout=stdout,
        stderr=stderr,
        effective_mode=effective_mode,
        warnings=tuple(dict.fromkeys(item for item in warnings if item.strip())),
    )
