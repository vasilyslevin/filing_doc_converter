from pathlib import Path

from source_doc_converter import docling_runtime


def test_converter_reuse_for_compatible_options(monkeypatch, tmp_path: Path) -> None:
    created = []

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            self.do_ocr = False
            self.do_table_structure = False

    class FakePdfFormatOption:
        def __init__(self, **kwargs):
            pass

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
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
    docling_runtime.clear_converter_cache()

    first, first_metrics = docling_runtime.create_local_pdf_converter_with_metrics(
        tmp_path / "models",
        do_ocr=False,
        do_tables=False,
        device="cpu",
        parser_threads=2,
        inference_threads=2,
    )
    second, second_metrics = docling_runtime.create_local_pdf_converter_with_metrics(
        tmp_path / "models",
        do_ocr=False,
        do_tables=False,
        device="cpu",
        parser_threads=2,
        inference_threads=2,
    )

    assert first is second
    assert len(created) == 1
    assert not first_metrics.cache_hit
    assert second_metrics.cache_hit


def test_converter_cache_invalidation_on_option_change(monkeypatch, tmp_path: Path) -> None:
    created = []

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            self.do_ocr = False
            self.do_table_structure = False

    class FakePdfFormatOption:
        def __init__(self, **kwargs):
            pass

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
            created.append(kwargs)

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
    docling_runtime.clear_converter_cache()

    one = docling_runtime.create_local_pdf_converter(
        tmp_path / "models",
        do_ocr=False,
        do_tables=False,
        device="cpu",
        parser_threads=2,
        inference_threads=2,
    )
    two = docling_runtime.create_local_pdf_converter(
        tmp_path / "models",
        do_ocr=False,
        do_tables=True,
        device="cpu",
        parser_threads=2,
        inference_threads=2,
    )

    assert one is not two
    assert len(created) == 2


def test_parser_and_inference_threads_are_applied(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            self.do_ocr = False
            self.do_table_structure = False
            self.document_parsing_num_threads = None
            self.inference_num_threads = None

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
    docling_runtime.clear_converter_cache()

    docling_runtime.create_local_pdf_converter(
        tmp_path / "models",
        parser_threads=3,
        inference_threads=2,
    )
    pipeline_options = captured["pipeline_options"]

    assert pipeline_options.document_parsing_num_threads == 3
    assert pipeline_options.inference_num_threads == 2
