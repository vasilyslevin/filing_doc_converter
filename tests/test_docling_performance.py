from pathlib import Path

from filing_doc_converter import docling_runtime


def test_cpu_fast_profile_and_converter_reuse(monkeypatch, tmp_path: Path) -> None:
    captured = {}
    created = []

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            captured["pipeline_options"] = kwargs
            self.do_ocr = True
            self.do_table_structure = True

    class FakePdfFormatOption:
        def __init__(self, **kwargs):
            captured["format_option"] = kwargs

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
            captured["converter"] = kwargs
            created.append(self)

    monkeypatch.setattr(
        docling_runtime,
        "_load_docling_components",
        lambda: (
            FakeDocumentConverter,
            FakePdfFormatOption,
            FakePipelineOptions,
            FakeInputFormat,
        ),
    )
    monkeypatch.delenv(docling_runtime.DOCLING_OCR_ENV, raising=False)
    monkeypatch.delenv(docling_runtime.DOCLING_TABLES_ENV, raising=False)
    docling_runtime.clear_converter_cache()

    first = docling_runtime.create_local_pdf_converter(tmp_path / "models")
    second = docling_runtime.create_local_pdf_converter(tmp_path / "models")

    pipeline_options = captured["format_option"]["pipeline_options"]
    assert not pipeline_options.do_ocr
    assert not pipeline_options.do_table_structure
    assert first is second
    assert len(created) == 1


def test_detailed_options_are_selectable(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            self.do_ocr = False
            self.do_table_structure = False

    class FakePdfFormatOption:
        def __init__(self, **kwargs):
            captured["pipeline_options"] = kwargs["pipeline_options"]

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(
        docling_runtime,
        "_load_docling_components",
        lambda: (
            FakeDocumentConverter,
            FakePdfFormatOption,
            FakePipelineOptions,
            FakeInputFormat,
        ),
    )
    monkeypatch.setenv(docling_runtime.DOCLING_OCR_ENV, "1")
    monkeypatch.setenv(docling_runtime.DOCLING_TABLES_ENV, "1")
    docling_runtime.clear_converter_cache()

    docling_runtime.create_local_pdf_converter(tmp_path / "models")

    assert captured["pipeline_options"].do_ocr
    assert captured["pipeline_options"].do_table_structure
