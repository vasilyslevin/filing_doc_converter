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
DOCLING_OCR_ENV = "FILING_DOC_CONVERTER_DO_OCR"
DOCLING_TABLES_ENV = "FILING_DOC_CONVERTER_DO_TABLES"
DOCLING_CPU_ONLY_ENV = "FILING_DOC_CONVERTER_CPU_ONLY"
_CONVERTER_CACHE: dict[tuple[Path, bool, bool, int, str], object] = {}


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


def _environment_flag(name: str, *, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _cpu_thread_count() -> int:
    return max(1, min(8, os.cpu_count() or 4))


def _device_mode() -> str:
    return "cpu" if _environment_flag(DOCLING_CPU_ONLY_ENV, default=True) else "auto"


def clear_converter_cache() -> None:
    _CONVERTER_CACHE.clear()


def create_local_pdf_converter(model_directory: Path):
    directory = model_directory.expanduser().resolve()
    do_ocr = _environment_flag(DOCLING_OCR_ENV)
    do_tables = _environment_flag(DOCLING_TABLES_ENV)
    num_threads = _cpu_thread_count()
    device = _device_mode()
    cache_key = (directory, do_ocr, do_tables, num_threads, device)
    cached = _CONVERTER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    document_converter, pdf_format_option, pipeline_options_class, input_format = (
        _load_docling_components()
    )
    pipeline_options = pipeline_options_class(
        artifacts_path=directory,
        enable_remote_services=False,
        allow_external_plugins=False,
    )
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = do_tables
    converter = document_converter(
        allowed_formats=[input_format.PDF],
        format_options={
            input_format.PDF: pdf_format_option(pipeline_options=pipeline_options)
        },
    )
    _CONVERTER_CACHE[cache_key] = converter
    return converter


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
        "DOCLING_DEVICE": _device_mode(),
        "DOCLING_NUM_THREADS": str(_cpu_thread_count()),
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
