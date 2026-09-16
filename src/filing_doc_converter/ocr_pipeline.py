import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from threading import Event


class OcrError(RuntimeError):
    """Base error raised by the OCR pipeline."""


class OcrUnavailableError(OcrError):
    """Raised when OCRmyPDF cannot be found."""


class OcrCancelledError(OcrError):
    """Raised when an OCR job is cancelled."""


@dataclass(frozen=True)
class OcrResult:
    input_path: Path
    output_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str


def find_ocrmypdf() -> str | None:
    return shutil.which("ocrmypdf")


def searchable_output_path(input_path: Path, output_directory: Path) -> Path:
    return output_directory / f"{input_path.stem}.searchable.pdf"


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
