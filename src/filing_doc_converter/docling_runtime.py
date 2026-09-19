import inspect
import os
import time
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
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
DOCLING_PARSER_THREADS_ENV = "FILING_DOC_CONVERTER_DOCLING_PARSER_THREADS"
DOCLING_INFERENCE_THREADS_ENV = "FILING_DOC_CONVERTER_DOCLING_INFERENCE_THREADS"
_CONVERTER_CACHE: dict[tuple[Path, bool, bool, str, int, int], object] = {}


@dataclass(frozen=True)
class ConverterBuildMetrics:
    cache_hit: bool
    init_seconds: float


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


def _safe_thread_count(value: int) -> int:
    return max(1, int(value))


def _cpu_thread_count() -> int:
    return max(1, min(8, os.cpu_count() or 4))


def _device_mode() -> str:
    return "cpu" if _environment_flag(DOCLING_CPU_ONLY_ENV, default=True) else "auto"


def _default_parser_threads() -> int:
    raw = os.environ.get(DOCLING_PARSER_THREADS_ENV)
    if raw is not None and raw.strip():
        return _safe_thread_count(int(raw))
    return max(1, min(4, _cpu_thread_count()))


def _default_inference_threads() -> int:
    raw = os.environ.get(DOCLING_INFERENCE_THREADS_ENV)
    if raw is not None and raw.strip():
        return _safe_thread_count(int(raw))
    return max(1, min(4, _cpu_thread_count()))


def clear_converter_cache() -> None:
    _CONVERTER_CACHE.clear()


def _set_if_supported(target: object, names: tuple[str, ...], value: object) -> bool:
    for name in names:
        if hasattr(target, name):
            setattr(target, name, value)
            return True
    return False


def _configure_accelerator_options(
    pipeline_options: object,
    *,
    device: str,
    inference_threads: int,
) -> bool:
    try:
        from docling.datamodel.pipeline_options import AcceleratorOptions
    except ImportError:
        return _set_if_supported(
            pipeline_options,
            ("inference_num_threads", "model_num_threads", "num_model_threads"),
            inference_threads,
        )

    if not hasattr(pipeline_options, "accelerator_options"):
        return _set_if_supported(
            pipeline_options,
            ("inference_num_threads", "model_num_threads", "num_model_threads"),
            inference_threads,
        )

    signature = inspect.signature(AcceleratorOptions)
    kwargs: dict[str, object] = {}
    for candidate, value in (
        ("num_threads", inference_threads),
        ("inference_num_threads", inference_threads),
        ("num_threads_inference", inference_threads),
        ("device", device),
    ):
        if candidate in signature.parameters:
            kwargs[candidate] = value

    try:
        pipeline_options.accelerator_options = AcceleratorOptions(**kwargs)
        return True
    except (TypeError, ValueError):
        return _set_if_supported(
            pipeline_options,
            ("inference_num_threads", "model_num_threads", "num_model_threads"),
            inference_threads,
        )


def _build_converter(
    model_directory: Path,
    *,
    do_ocr: bool,
    do_tables: bool,
    device: str,
    parser_threads: int,
    inference_threads: int,
) -> object:
    document_converter, pdf_format_option, pipeline_options_class, input_format = (
        _load_docling_components()
    )
    pipeline_options = pipeline_options_class(
        artifacts_path=model_directory,
        enable_remote_services=False,
        allow_external_plugins=False,
    )
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = do_tables
    _set_if_supported(
        pipeline_options,
        ("num_threads", "document_parsing_num_threads", "num_parse_threads", "parse_threads"),
        parser_threads,
    )
    _configure_accelerator_options(
        pipeline_options,
        device=device,
        inference_threads=inference_threads,
    )
    converter = document_converter(
        allowed_formats=[input_format.PDF],
        format_options={
            input_format.PDF: pdf_format_option(pipeline_options=pipeline_options)
        },
    )
    return converter


def create_local_pdf_converter_with_metrics(
    model_directory: Path,
    *,
    do_ocr: bool | None = None,
    do_tables: bool | None = None,
    device: str | None = None,
    parser_threads: int | None = None,
    inference_threads: int | None = None,
) -> tuple[object, ConverterBuildMetrics]:
    directory = model_directory.expanduser().resolve()
    resolved_do_ocr = _environment_flag(DOCLING_OCR_ENV) if do_ocr is None else do_ocr
    resolved_do_tables = (
        _environment_flag(DOCLING_TABLES_ENV) if do_tables is None else do_tables
    )
    resolved_device = _device_mode() if device is None else device
    resolved_parser_threads = (
        _default_parser_threads() if parser_threads is None else _safe_thread_count(parser_threads)
    )
    resolved_inference_threads = (
        _default_inference_threads()
        if inference_threads is None
        else _safe_thread_count(inference_threads)
    )
    cache_key = (
        directory,
        resolved_do_ocr,
        resolved_do_tables,
        resolved_device,
        resolved_parser_threads,
        resolved_inference_threads,
    )
    cached = _CONVERTER_CACHE.get(cache_key)
    if cached is not None:
        return cached, ConverterBuildMetrics(cache_hit=True, init_seconds=0.0)

    started = time.monotonic()
    converter = _build_converter(
        directory,
        do_ocr=resolved_do_ocr,
        do_tables=resolved_do_tables,
        device=resolved_device,
        parser_threads=resolved_parser_threads,
        inference_threads=resolved_inference_threads,
    )
    elapsed = time.monotonic() - started
    _CONVERTER_CACHE[cache_key] = converter
    return converter, ConverterBuildMetrics(cache_hit=False, init_seconds=elapsed)


def create_local_pdf_converter(
    model_directory: Path,
    *,
    do_ocr: bool | None = None,
    do_tables: bool | None = None,
    device: str | None = None,
    parser_threads: int | None = None,
    inference_threads: int | None = None,
):
    converter, _ = create_local_pdf_converter_with_metrics(
        model_directory,
        do_ocr=do_ocr,
        do_tables=do_tables,
        device=device,
        parser_threads=parser_threads,
        inference_threads=inference_threads,
    )
    return converter


@contextmanager
def offline_environment(
    model_directory: Path,
    *,
    environ: MutableMapping[str, str] | None = None,
    device: str | None = None,
    parser_threads: int | None = None,
    inference_threads: int | None = None,
) -> Iterator[None]:
    active_environment = os.environ if environ is None else environ
    resolved_device = _device_mode() if device is None else device
    resolved_parser_threads = (
        _default_parser_threads() if parser_threads is None else _safe_thread_count(parser_threads)
    )
    resolved_inference_threads = (
        _default_inference_threads()
        if inference_threads is None
        else _safe_thread_count(inference_threads)
    )
    values = {
        **OFFLINE_ENVIRONMENT,
        "DOCLING_ARTIFACTS_PATH": str(model_directory),
        "DOCLING_DEVICE": resolved_device,
        "DOCLING_NUM_THREADS": str(resolved_parser_threads),
        DOCLING_PARSER_THREADS_ENV: str(resolved_parser_threads),
        DOCLING_INFERENCE_THREADS_ENV: str(resolved_inference_threads),
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
def local_pdf_converter(
    model_directory: Path | None = None,
    *,
    do_ocr: bool | None = None,
    do_tables: bool | None = None,
    device: str | None = None,
    parser_threads: int | None = None,
    inference_threads: int | None = None,
) -> Iterator[object]:
    directory = require_ready_model_directory(model_directory)
    with offline_environment(
        directory,
        device=device,
        parser_threads=parser_threads,
        inference_threads=inference_threads,
    ):
        yield create_local_pdf_converter(
            directory,
            do_ocr=do_ocr,
            do_tables=do_tables,
            device=device,
            parser_threads=parser_threads,
            inference_threads=inference_threads,
        )
