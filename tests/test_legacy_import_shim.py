import importlib
import runpy
import sys
import types
import warnings


def test_legacy_package_import_warns_and_loads() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        legacy = importlib.import_module("filing_doc_converter")

    assert legacy.__name__ == "source_doc_converter"
    assert any(
        warning.category is DeprecationWarning and "deprecated" in str(warning.message).lower()
        for warning in captured
    )


def test_legacy_submodule_import_remains_available() -> None:
    module = importlib.import_module("filing_doc_converter.model_management")

    assert hasattr(module, "load_model_directory")


def test_legacy_module_entrypoint_warns_and_runs(monkeypatch) -> None:
    fake_app = types.ModuleType("source_doc_converter.app")
    fake_app.main = lambda: 0
    monkeypatch.setitem(sys.modules, "source_doc_converter.app", fake_app)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            runpy.run_module("filing_doc_converter.__main__", run_name="__main__")
        except SystemExit as error:
            assert error.code == 0
