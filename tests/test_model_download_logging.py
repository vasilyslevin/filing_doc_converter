from pathlib import Path

from filing_doc_converter import model_downloader
from filing_doc_converter.model_downloader import ModelDownloadWorker


class CompletedProcess:
    def __init__(self, output: str, returncode: int) -> None:
        self.output = output
        self.returncode = returncode

    def communicate(self, timeout=None):
        return self.output, None

    def poll(self):
        return self.returncode


def test_multiline_downloader_failure_is_preserved(monkeypatch, qtbot, tmp_path: Path) -> None:
    output = "first warning\nTraceback: useful cause\nfinal exception"
    monkeypatch.setattr(
        model_downloader.subprocess,
        "Popen",
        lambda *args, **kwargs: CompletedProcess(output, 1),
    )
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")
    failures = []
    worker.failed.connect(failures.append)

    worker.run()

    assert len(failures) == 1
    assert output in failures[0]


def test_warning_output_with_zero_exit_is_success(monkeypatch, qtbot, tmp_path: Path) -> None:
    output = "hf_xet is not installed; falling back to regular HTTP"
    monkeypatch.setattr(
        model_downloader.subprocess,
        "Popen",
        lambda *args, **kwargs: CompletedProcess(output, 0),
    )
    monkeypatch.setattr(model_downloader, "mark_models_ready", lambda path: None)
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")
    completed = []
    failures = []
    worker.completed.connect(lambda: completed.append(True))
    worker.failed.connect(failures.append)

    worker.run()

    assert completed == [True]
    assert failures == []
