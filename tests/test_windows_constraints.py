from pathlib import Path

ROOT = Path(__file__).parents[1]
CONSTRAINTS = ROOT / "packaging" / "windows" / "constraints-windows.txt"
BUILD_REQUIREMENTS = ROOT / "packaging" / "windows" / "requirements-build.txt"
WINDOWS_WORKFLOW = ROOT / ".github" / "workflows" / "windows-package.yml"


def test_windows_constraints_pin_critical_packages() -> None:
    pins = {
        line.split("==", 1)[0].lower(): line.split("==", 1)[1]
        for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }

    assert {
        "docling",
        "transformers",
        "torch",
        "torchvision",
        "pyside6",
        "rapidocr",
        "onnxruntime",
        "pyinstaller",
        "pyinstaller-hooks-contrib",
    } <= pins.keys()
    assert pins["transformers"] == "4.51.3"


def test_windows_package_install_uses_constraints() -> None:
    requirements = BUILD_REQUIREMENTS.read_text(encoding="utf-8")
    workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")

    assert "-c constraints-windows.txt" in requirements
    assert ".[full,dev]" in workflow
    assert "pip install -r packaging/windows/requirements-build.txt" in workflow


def test_windows_workflow_builds_single_external_ocr_artifact() -> None:
    workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")

    assert "Build standalone folder" in workflow
    assert "SourceDocumentConverter-Windows-x64.zip" in workflow
    assert "SourceDocumentConverter-Windows-x64" in workflow
    assert "-PackageFlavor Lite" not in workflow
    assert "SourceDocumentConverter-Windows-x64-Full" not in workflow
    assert "SourceDocumentConverter-Windows-x64-Lite" not in workflow


def test_windows_workflow_does_not_bundle_ocr_companions() -> None:
    workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")

    assert "Package unexpectedly contains ocrmypdf.exe" in workflow
    assert "Package unexpectedly contains bundled Tesseract" in workflow
    assert "ocrmypdf.exe\") --version" not in workflow
