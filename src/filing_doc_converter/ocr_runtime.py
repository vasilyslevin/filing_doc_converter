import os
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from filing_doc_converter.model_management import is_packaged_application


@dataclass(frozen=True)
class BundledTesseract:
    root: Path
    executable: Path
    tessdata: Path


def _candidate_bundle_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    executable_root = Path(sys.executable).resolve().parent / "tools" / "tesseract"
    roots.append(executable_root)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass).resolve() / "tools" / "tesseract")
    return tuple(roots)


def find_bundled_tesseract() -> BundledTesseract | None:
    if not is_packaged_application():
        return None
    for root in _candidate_bundle_roots():
        tessdata = root / "tessdata"
        for executable_name in ("tesseract.exe", "tesseract"):
            executable = root / executable_name
            if executable.is_file() and tessdata.is_dir():
                return BundledTesseract(root=root, executable=executable, tessdata=tessdata)
    return None


def resolve_ocrmypdf_executable() -> str | None:
    if is_packaged_application():
        executable = Path(sys.executable).resolve().with_name("ocrmypdf.exe")
        if executable.is_file():
            return str(executable)
    return shutil.which("ocrmypdf")


def resolve_tesseract_executable() -> tuple[str | None, str]:
    bundled = find_bundled_tesseract()
    if bundled is not None:
        return str(bundled.executable), "bundled"
    executable = shutil.which("tesseract")
    if executable:
        return executable, "system"
    return None, "missing"


def build_ocr_environment(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    base = dict(os.environ if environ is None else environ)
    bundled = find_bundled_tesseract()
    if bundled is None:
        return base

    path_entries = base.get("PATH", "").split(os.pathsep) if base.get("PATH") else []
    normalized = {entry.casefold() for entry in path_entries}
    bundle_root = str(bundled.root)
    if bundle_root.casefold() not in normalized:
        path_entries = [bundle_root, *path_entries]
    base["PATH"] = os.pathsep.join(path_entries)
    base["TESSDATA_PREFIX"] = str(bundled.tessdata)
    return base
