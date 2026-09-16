import subprocess
from pathlib import Path

from filing_doc_converter import model_downloader
from filing_doc_converter.model_downloader import ModelDownloadWorker


class SuccessfulProcess:
    returncode = 0

    def communicate(self, timeout=None):
        return ("download complete", None)

    def poll(self):
        return self.returncode


class FailedProcess(SuccessfulProcess):
    returncode = 1

    def communicate(self, timeout=None):
        return ("safe failure detail", None)


def test_worker_uses_safe_subprocess_arguments(monkeypatch, qtbot, tmp_path: Path) -> None:
    captured = {}
    marked = []

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SuccessfulProcess()

    monkeypatch.setattr(model_downloader.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(model_downloader, "mark_models_ready", marked.append)
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")
    completed = []
    worker.completed.connect(lambda: completed.append(True))

    worker.run()

    assert captured["command"] == [
        "docling-tools",
        "models",
        "download",
        "-o",
        str((tmp_path / "models").resolve()),
    ]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["encoding"] == "utf-8"
    assert marked == [(tmp_path / "models").resolve()]
    assert completed == [True]


def test_worker_reports_downloader_failure(monkeypatch, qtbot, tmp_path: Path) -> None:
    monkeypatch.setattr(
        model_downloader.subprocess,
        "Popen",
        lambda *args, **kwargs: FailedProcess(),
    )
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")
    failures = []
    worker.failed.connect(failures.append)

    worker.run()

    assert failures == ["The model download did not complete. safe failure detail"]


def test_worker_can_be_cancelled_before_start(qtbot, tmp_path: Path) -> None:
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")
    cancellations = []
    worker.cancelled.connect(lambda: cancellations.append(True))

    worker.cancel()
    worker.run()

    assert cancellations == [True]


def test_worker_terminates_a_cancelled_process(monkeypatch, qtbot, tmp_path: Path) -> None:
    class HangingProcess:
        returncode = None

        def __init__(self):
            self.terminated = False
            self.communications = 0

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.returncode = -9

        def communicate(self, timeout=None):
            self.communications += 1
            if self.communications == 1:
                worker.cancel()
                raise subprocess.TimeoutExpired("docling-tools", timeout)
            return ("", None)

    process = HangingProcess()
    monkeypatch.setattr(
        model_downloader.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )
    worker = ModelDownloadWorker(tmp_path / "models", executable="docling-tools")

    worker.run()

    assert process.terminated
