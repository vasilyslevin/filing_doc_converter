import sys
from types import ModuleType

from filing_doc_converter import app as application_entry
from filing_doc_converter import docling_tools_entry


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
