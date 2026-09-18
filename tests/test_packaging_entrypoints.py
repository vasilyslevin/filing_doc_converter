import sys
from pathlib import Path
from types import ModuleType

from filing_doc_converter import app as application_entry
from filing_doc_converter import docling_tools_entry, ocrmypdf_entry


def test_package_smoke_test_checks_window_and_companion(monkeypatch) -> None:
    events = []

    class FakeWindow:
        def __init__(self) -> None:
            events.append("window")

        def close(self) -> None:
            events.append("closed")

    monkeypatch.setattr(application_entry, "ApplicationWindow", FakeWindow)
    monkeypatch.setattr(
        application_entry,
        "resolve_model_downloader",
        lambda: events.append("companion") or "docling-tools.exe",
    )

    assert application_entry.run_package_smoke_test() == 0
    assert events == ["window", "closed", "companion"]


def test_prepare_packaged_path_is_noop(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / "FilingDocumentConverter.exe"
    monkeypatch.setattr(application_entry.sys, "executable", str(executable))
    monkeypatch.setenv("PATH", str(tmp_path / "existing"))

    application_entry.prepare_packaged_path()

    assert application_entry.sys.executable == str(executable)


def test_docling_tools_entry_invokes_upstream_cli(monkeypatch) -> None:
    calls = []
    docling_module = ModuleType("docling")
    cli_module = ModuleType("docling.cli")
    tools_module = ModuleType("docling.cli.tools")
    tools_module.app = lambda **kwargs: calls.append(kwargs)
    monkeypatch.setitem(sys.modules, "docling", docling_module)
    monkeypatch.setitem(sys.modules, "docling.cli", cli_module)
    monkeypatch.setitem(sys.modules, "docling.cli.tools", tools_module)

    assert docling_tools_entry.main() == 0
    assert calls == [{"prog_name": "docling-tools"}]


def test_ocrmypdf_entry_invokes_upstream_cli(monkeypatch) -> None:
    calls = []
    ocrmypdf_module = ModuleType("ocrmypdf")
    main_module = ModuleType("ocrmypdf.__main__")
    main_module.run = lambda: calls.append("run") or 0
    monkeypatch.setitem(sys.modules, "ocrmypdf", ocrmypdf_module)
    monkeypatch.setitem(sys.modules, "ocrmypdf.__main__", main_module)

    assert ocrmypdf_entry.main() == 0
    assert calls == ["run"]
