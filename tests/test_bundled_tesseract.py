import os
from pathlib import Path

from filing_doc_converter import ocr_runtime


def test_find_bundled_tesseract_prefers_packaged_folder(monkeypatch, tmp_path: Path) -> None:
    package_directory = tmp_path / "package"
    tesseract_directory = package_directory / "tools" / "tesseract"
    (tesseract_directory / "tessdata").mkdir(parents=True)
    (tesseract_directory / "tesseract.exe").touch()
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: True)
    monkeypatch.setattr(ocr_runtime.sys, "executable", str(package_directory / "app.exe"))
    monkeypatch.setattr(ocr_runtime.sys, "_MEIPASS", str(tmp_path / "missing"), raising=False)

    bundled = ocr_runtime.find_bundled_tesseract()

    assert bundled is not None
    assert bundled.root == tesseract_directory
    assert bundled.executable == tesseract_directory / "tesseract.exe"


def test_find_bundled_tesseract_uses_meipass_fallback(monkeypatch, tmp_path: Path) -> None:
    meipass_directory = tmp_path / "meipass"
    tesseract_directory = meipass_directory / "tools" / "tesseract"
    (tesseract_directory / "tessdata").mkdir(parents=True)
    (tesseract_directory / "tesseract.exe").touch()
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: True)
    monkeypatch.setattr(ocr_runtime.sys, "executable", str(tmp_path / "package" / "app.exe"))
    monkeypatch.setattr(ocr_runtime.sys, "_MEIPASS", str(meipass_directory), raising=False)

    bundled = ocr_runtime.find_bundled_tesseract()

    assert bundled is not None
    assert bundled.root == tesseract_directory


def test_build_ocr_environment_only_changes_subprocess_env(monkeypatch, tmp_path: Path) -> None:
    package_directory = tmp_path / "package"
    tesseract_directory = package_directory / "tools" / "tesseract"
    tessdata_directory = tesseract_directory / "tessdata"
    tessdata_directory.mkdir(parents=True)
    (tesseract_directory / "tesseract.exe").touch()
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: True)
    monkeypatch.setattr(ocr_runtime.sys, "executable", str(package_directory / "app.exe"))
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)

    env = ocr_runtime.build_ocr_environment({"PATH": str(tmp_path / "system-tools")})

    assert env["PATH"].split(os.pathsep)[0] == str(tesseract_directory)
    assert env["TESSDATA_PREFIX"] == str(tessdata_directory)
    assert "TESSDATA_PREFIX" not in os.environ


def test_resolve_tesseract_prefers_bundled_over_system(monkeypatch, tmp_path: Path) -> None:
    package_directory = tmp_path / "package"
    tesseract_directory = package_directory / "tools" / "tesseract"
    (tesseract_directory / "tessdata").mkdir(parents=True)
    bundled_executable = tesseract_directory / "tesseract.exe"
    bundled_executable.touch()
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: True)
    monkeypatch.setattr(ocr_runtime.sys, "executable", str(package_directory / "app.exe"))
    monkeypatch.setattr(ocr_runtime.shutil, "which", lambda name: str(tmp_path / "system" / "tesseract.exe"))

    executable, source = ocr_runtime.resolve_tesseract_executable()

    assert executable == str(bundled_executable)
    assert source == "bundled"


def test_resolve_tesseract_uses_system_for_source_install(monkeypatch) -> None:
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: False)
    monkeypatch.setattr(ocr_runtime.shutil, "which", lambda name: "/usr/bin/tesseract")

    executable, source = ocr_runtime.resolve_tesseract_executable()

    assert executable == "/usr/bin/tesseract"
    assert source == "system"


def test_resolve_ocrmypdf_prefers_packaged_companion(monkeypatch, tmp_path: Path) -> None:
    package_directory = tmp_path / "package"
    companion = package_directory / "ocrmypdf.exe"
    companion.parent.mkdir(parents=True, exist_ok=True)
    companion.touch()
    monkeypatch.setattr(ocr_runtime, "is_packaged_application", lambda: True)
    monkeypatch.setattr(ocr_runtime.sys, "executable", str(package_directory / "app.exe"))
    monkeypatch.setattr(ocr_runtime.shutil, "which", lambda name: str(tmp_path / "system" / "ocrmypdf"))

    executable = ocr_runtime.resolve_ocrmypdf_executable()

    assert executable == str(companion)
