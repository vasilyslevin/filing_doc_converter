from pathlib import Path

import pytest

from filing_doc_converter import docling_runtime
from filing_doc_converter.docling_runtime import (
    LocalModelsUnavailableError,
    create_local_pdf_converter,
    local_pdf_converter,
    offline_environment,
    require_ready_model_directory,
)
from filing_doc_converter.model_management import mark_models_ready


def ready_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "models"
    directory.mkdir()
    (directory / "model.bin").write_bytes(b"model")
    mark_models_ready(directory)
    return directory


def test_missing_models_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(LocalModelsUnavailableError, match="Download Models"):
        require_ready_model_directory(tmp_path / "missing")


def test_ready_model_directory_is_accepted(tmp_path: Path) -> None:
    directory = ready_directory(tmp_path)

    assert require_ready_model_directory(directory) == directory.resolve()


def test_converter_disables_remote_services_and_plugins(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class FakeInputFormat:
        PDF = "pdf"

    class FakePipelineOptions:
        def __init__(self, **kwargs):
            captured["pipeline_options"] = kwargs

    class FakePdfFormatOption:
        def __init__(self, **kwargs):
            captured["format_option"] = kwargs

    class FakeDocumentConverter:
        def __init__(self, **kwargs):
            captured["converter"] = kwargs

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
    directory = tmp_path / "models"

    create_local_pdf_converter(directory)

    assert captured["pipeline_options"] == {
        "artifacts_path": directory,
        "enable_remote_services": False,
        "allow_external_plugins": False,
    }
    assert captured["converter"]["allowed_formats"] == ["pdf"]
    assert list(captured["converter"]["format_options"]) == ["pdf"]


def test_offline_environment_is_scoped_and_restored(tmp_path: Path) -> None:
    environment = {
        "HF_HUB_OFFLINE": "previous",
        "UNRELATED": "preserved",
    }
    directory = tmp_path / "models"

    with offline_environment(directory, environ=environment):
        assert environment["HF_HUB_OFFLINE"] == "1"
        assert environment["TRANSFORMERS_OFFLINE"] == "1"
        assert environment["HF_DATASETS_OFFLINE"] == "1"
        assert environment["DOCLING_ARTIFACTS_PATH"] == str(directory)
        assert environment["UNRELATED"] == "preserved"

    assert environment == {
        "HF_HUB_OFFLINE": "previous",
        "UNRELATED": "preserved",
    }


def test_local_converter_applies_offline_environment(monkeypatch, tmp_path: Path) -> None:
    directory = ready_directory(tmp_path)
    captured = {}
    fake_converter = object()

    def fake_create(model_directory: Path, **kwargs):
        captured["directory"] = model_directory
        captured["offline"] = {
            key: docling_runtime.os.environ.get(key)
            for key in docling_runtime.OFFLINE_ENVIRONMENT
        }
        return fake_converter

    monkeypatch.setattr(docling_runtime, "create_local_pdf_converter", fake_create)

    with local_pdf_converter(directory) as converter:
        assert converter is fake_converter

    assert captured["directory"] == directory.resolve()
    assert captured["offline"] == {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
    }
