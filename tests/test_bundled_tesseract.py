import os
from pathlib import Path

from filing_doc_converter import app as application_entry


def test_packaged_app_prefers_bundled_tesseract(monkeypatch, tmp_path: Path) -> None:
    application_directory = tmp_path / "package"
    executable = application_directory / "FilingDocumentConverter.exe"
    tesseract_directory = application_directory / "tools" / "tesseract"
    tessdata_directory = tesseract_directory / "tessdata"
    tessdata_directory.mkdir(parents=True)
    (tesseract_directory / "tesseract.exe").touch()
    monkeypatch.setattr(application_entry, "is_packaged_application", lambda: True)
    monkeypatch.setattr(application_entry.sys, "executable", str(executable))
    monkeypatch.setenv("PATH", str(tmp_path / "system-tools"))
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)

    application_entry.prepare_packaged_path()

    path_entries = os.environ["PATH"].split(os.pathsep)
    assert path_entries[0] == str(tesseract_directory)
    assert path_entries[1] == str(application_directory)
    assert os.environ["TESSDATA_PREFIX"] == str(tessdata_directory)
