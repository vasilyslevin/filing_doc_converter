from source_doc_converter import dependency_setup
from source_doc_converter.dependency_setup import DependencyInstallStep, DependencySetupWorker
from source_doc_converter.system_diagnostics import ComponentStatus, SystemDiagnostics


def diagnostics(missing: tuple[str, ...]) -> SystemDiagnostics:
    return SystemDiagnostics(
        application_version="0.1.0a0",
        operating_system="Windows",
        operating_system_version="11",
        architecture="x64",
        python_version="3.12",
        pyside_version="6.9",
        components=tuple(
            ComponentStatus(key, key, key not in missing)
            for key in ("ocrmypdf", "tesseract", "docling")
        ),
    )


class FakeStdout:
    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)

    def readline(self) -> str:
        if self._lines:
            return self._lines.pop(0)
        return ""


class FakeProcess:
    def __init__(self, lines: list[str], returncode: int = 0) -> None:
        self.stdout = FakeStdout(lines)
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.returncode = -9

    def communicate(self, timeout=None):
        return ("", "")


def test_dependency_setup_status_transitions(monkeypatch, qtbot) -> None:
    checks = iter((diagnostics(("ocrmypdf",)), diagnostics(())))
    monkeypatch.setattr(
        dependency_setup.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(["installing OCRmyPDF\n"], 0),
    )
    worker = DependencySetupWorker(
        diagnostics_provider=lambda: next(checks),
        steps_builder=lambda _: [
            DependencyInstallStep("ocrmypdf", "OCRmyPDF", ("winget", "install")),
        ],
    )
    statuses = []
    worker.status_changed.connect(statuses.append)

    worker.run()

    assert statuses[0] == "Checking dependencies…"
    assert "Installing OCRmyPDF…" in statuses
    assert "Rechecking dependencies…" in statuses
    assert statuses[-1] == "Completed"


def test_dependency_setup_cancellation_reports_target(monkeypatch, qtbot) -> None:
    process = FakeProcess([], 0)
    worker = DependencySetupWorker(
        diagnostics_provider=lambda: diagnostics(("tesseract",)),
        steps_builder=lambda _: [
            DependencyInstallStep("tesseract", "Tesseract OCR", ("winget", "install")),
        ],
    )

    def fake_popen(*args, **kwargs):
        worker.cancel()
        return process

    monkeypatch.setattr(dependency_setup.subprocess, "Popen", fake_popen)
    cancelled = []
    worker.cancelled.connect(cancelled.append)

    worker.run()

    assert cancelled
    assert "Tesseract OCR" in cancelled[0]


def test_dependency_setup_failure_preserves_full_details(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        dependency_setup.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(["line one\n", "line two\n"], 1),
    )
    worker = DependencySetupWorker(
        diagnostics_provider=lambda: diagnostics(("ocrmypdf",)),
        steps_builder=lambda _: [
            DependencyInstallStep("ocrmypdf", "OCRmyPDF", ("winget", "install")),
        ],
    )
    failures = []
    worker.failed.connect(failures.append)

    worker.run()

    assert failures
    assert "line one" in failures[0]
    assert "line two" in failures[0]
