import importlib.metadata as importlib_metadata
import importlib.util as importlib_util
import platform
import shutil
import subprocess
from dataclasses import dataclass

from filing_doc_converter import __version__


@dataclass(frozen=True)
class ComponentStatus:
    key: str
    label: str
    available: bool
    version: str | None = None
    details: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class SystemDiagnostics:
    application_version: str
    operating_system: str
    operating_system_version: str
    architecture: str
    python_version: str
    pyside_version: str
    components: tuple[ComponentStatus, ...]

    def component(self, key: str) -> ComponentStatus:
        for component in self.components:
            if component.key == key:
                return component
        raise KeyError(key)

    def to_text(self) -> str:
        lines = [
            "Filing Document Converter - System Check",
            f"Application: {self.application_version}",
            f"Operating system: {self.operating_system} {self.operating_system_version}",
            f"Architecture: {self.architecture}",
            f"Python: {self.python_version}",
            f"PySide6: {self.pyside_version}",
            "",
            "Components:",
        ]
        for component in self.components:
            state = "Available" if component.available else "Unavailable"
            version = f" ({component.version})" if component.version else ""
            lines.append(f"- {component.label}: {state}{version}")
            for detail in component.details:
                lines.append(f"  - {detail}")
            if component.error:
                lines.append(f"  - Error: {component.error}")
        return "\n".join(lines) + "\n"


def _run_command(command: list[str], *, timeout: float = 5.0) -> tuple[bool, str, str | None]:
    try:
        completed = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except OSError as error:
        return False, "", str(error)

    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return False, output, f"Command exited with status {completed.returncode}"
    return True, output, None


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def check_ocrmypdf() -> ComponentStatus:
    executable = shutil.which("ocrmypdf")
    if executable is None:
        return ComponentStatus("ocrmypdf", "OCRmyPDF", False, error="Executable not found")

    succeeded, output, error = _run_command([executable, "--version"])
    return ComponentStatus(
        "ocrmypdf",
        "OCRmyPDF",
        succeeded,
        version=_first_line(output),
        error=error,
    )


def check_tesseract() -> ComponentStatus:
    executable = shutil.which("tesseract")
    if executable is None:
        return ComponentStatus("tesseract", "Tesseract OCR", False, error="Executable not found")

    succeeded, output, error = _run_command([executable, "--version"])
    if not succeeded:
        return ComponentStatus(
            "tesseract",
            "Tesseract OCR",
            False,
            version=_first_line(output),
            error=error,
        )

    languages_ok, languages_output, languages_error = _run_command(
        [executable, "--list-langs"]
    )
    languages = ()
    if languages_ok:
        lines = [line.strip() for line in languages_output.splitlines() if line.strip()]
        languages = tuple(lines[1:] if lines and "available languages" in lines[0].lower() else lines)

    details = (f"Languages: {', '.join(languages)}",) if languages else ()
    return ComponentStatus(
        "tesseract",
        "Tesseract OCR",
        True,
        version=_first_line(output),
        details=details,
        error=languages_error,
    )


def check_python_package(distribution: str, label: str) -> ComponentStatus:
    try:
        spec = importlib_util.find_spec(distribution)
    except (ImportError, ValueError) as error:
        return ComponentStatus(distribution, label, False, error=str(error))
    if spec is None:
        return ComponentStatus(distribution, label, False, error="Package not installed")

    try:
        version = importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        version = "Installed; version unavailable"
    return ComponentStatus(distribution, label, True, version=version)


def check_docling() -> ComponentStatus:
    return check_python_package("docling", "Docling")


def installation_guidance(component: str, operating_system: str | None = None) -> str:
    system = operating_system or platform.system()
    if component == "docling":
        return 'Install the Docling extra: python -m pip install ".[docling]"'
    if system == "Darwin":
        return "Install OCR tools with Homebrew: brew install ocrmypdf tesseract"
    if system == "Windows":
        return "Install OCRmyPDF and Tesseract, then ensure both executables are on PATH."
    return "Install OCRmyPDF and Tesseract using your Linux distribution package manager."


def collect_system_diagnostics() -> SystemDiagnostics:
    try:
        pyside_version = importlib_metadata.version("PySide6")
    except importlib_metadata.PackageNotFoundError:
        pyside_version = "Unavailable"

    return SystemDiagnostics(
        application_version=__version__,
        operating_system=platform.system(),
        operating_system_version=platform.release(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        pyside_version=pyside_version,
        components=(check_ocrmypdf(), check_tesseract(), check_docling()),
    )
