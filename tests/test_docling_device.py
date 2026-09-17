import os
from pathlib import Path

from filing_doc_converter import docling_runtime


def test_cpu_device_is_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(docling_runtime.DOCLING_CPU_ONLY_ENV, raising=False)

    with docling_runtime.offline_environment(tmp_path):
        assert os.environ["DOCLING_DEVICE"] == "cpu"


def test_auto_device_can_be_selected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(docling_runtime.DOCLING_CPU_ONLY_ENV, "0")

    with docling_runtime.offline_environment(tmp_path):
        assert os.environ["DOCLING_DEVICE"] == "auto"
