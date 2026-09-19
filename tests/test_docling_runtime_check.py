import sys
from types import ModuleType

from source_doc_converter import docling_tools_entry


def test_runtime_check_resolves_auto_image_processor(monkeypatch, capsys) -> None:
    class FakeAutoImageProcessor:
        pass

    class FakeDocumentConverter:
        pass

    docling_module = ModuleType("docling")
    converter_module = ModuleType("docling.document_converter")
    converter_module.DocumentConverter = FakeDocumentConverter
    transformers_module = ModuleType("transformers")
    transformers_module.AutoImageProcessor = FakeAutoImageProcessor
    monkeypatch.setitem(sys.modules, "docling", docling_module)
    monkeypatch.setitem(sys.modules, "docling.document_converter", converter_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    assert docling_tools_entry.run_runtime_check() == 0
    output = capsys.readouterr().out
    assert "AutoImageProcessor: FakeAutoImageProcessor" in output
    assert "DocumentConverter: FakeDocumentConverter" in output
