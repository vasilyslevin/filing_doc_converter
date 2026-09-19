import runpy
import sys
import types

from source_doc_converter import __version__


def test_version() -> None:
    assert __version__ == "0.1.0a0"


def test_module_entrypoint_uses_app_main(monkeypatch) -> None:
    fake_app = types.ModuleType("source_doc_converter.app")
    fake_app.main = lambda: 0
    monkeypatch.setitem(sys.modules, "source_doc_converter.app", fake_app)

    try:
        runpy.run_module("source_doc_converter.__main__", run_name="__main__")
    except SystemExit as error:
        assert error.code == 0
