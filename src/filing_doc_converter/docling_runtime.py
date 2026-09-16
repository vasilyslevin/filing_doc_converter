import os
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from pathlib import Path

from filing_doc_converter.model_management import (
    load_model_directory,
    models_ready,
)

OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
}


class LocalModelsUnavailableError(RuntimeError):
    """Raised when offline conversion models have not been prepared."""


class DoclingRuntimeUnavailableError(RuntimeError):
    """Raised when the local Docling runtime cannot be imported."""


def require_ready_model_directory(model_directory: Path | None = None) -> Path:
    if model_directory is None:
        state = load_model_directory()
        directory = state.path
        ready = state.ready
    else:
        directory = model_directory.expanduser().resolve()
        ready = models_ready(directory)

    if not ready:
        raise LocalModelsUnavailableError(
            "Local Docling models are not ready. Open Help > System Check, choose a model "
            "folder, and select Download Models before creating Markdown or JSON."
        )
    return directory


def _load_docling_components():
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as error:
        raise DoclingRuntimeUnavailableError(
            "Docling was not found. Install the Docling optional dependencies and try again."
        ) from error
    return DocumentConverter, PdfFormatOption, PdfPipelineOptions, InputFormat


def create_local_pdf_converter(model_directory: Path):
    document_converter, pdf_format_option, pipeline_options_class, input_format = (
        _load_docling_components()
    )
    pipeline_options = pipeline_options_class(
        artifacts_path=model_directory,
        enable_remote_services=False,
        allow_external_plugins=False,
    )
    return document_converter(
        allowed_formats=[input_format.PDF],
        format_options={
            input_format.PDF: pdf_format_option(pipeline_options=pipeline_options)
        },
    )


@contextmanager
def offline_environment(
    model_directory: Path,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> Iterator[None]:
    active_environment = os.environ if environ is None else environ
    values = {
        **OFFLINE_ENVIRONMENT,
        "DOCLING_ARTIFACTS_PATH": str(model_directory),
    }
    previous = {key: active_environment.get(key) for key in values}
    active_environment.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                active_environment.pop(key, None)
            else:
                active_environment[key] = value


@contextmanager
def local_pdf_converter(model_directory: Path | None = None) -> Iterator[object]:
    directory = require_ready_model_directory(model_directory)
    with offline_environment(directory):
        yield create_local_pdf_converter(directory)
