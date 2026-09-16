# Filing Document Converter Project Plan

## Purpose

Filing Document Converter is a local-first desktop application that helps judges, law clerks, lawyers, and other users convert long legal PDF filings into searchable PDFs and structured files suitable for AI-assisted review.

The application does not determine legal conclusions. Generated Markdown and JSON are working derivatives. The original PDF remains the authoritative source.

## Primary users

- Judges and chambers staff who should not need a terminal.
- Lawyers and legal-support professionals processing long records.
- Researchers preparing local document collections for language-model analysis.

## Core workflow

```text
Original PDF
    |
    +-- OCRmyPDF and Tesseract --> searchable PDF
    |
    +-- Docling ----------------> Markdown and/or JSON
    |
    +-- Combined ---------------> searchable PDF, then Markdown/JSON
```

When OCR and Docling are selected together, Docling reads the newly created searchable PDF while Markdown and JSON retain the original input stem. When only Markdown or JSON is selected, Docling reads the original PDF directly.

## Current scope

- Add individual PDFs or recursively scan a folder.
- Prevent duplicate queue entries.
- Choose an output directory.
- Create searchable PDFs.
- Create Markdown with page-break markers.
- Create structured JSON.
- Process files without freezing the GUI.
- Cancel OCR and stop between later processing stages.
- Display per-file success and failure information.
- Protect original and existing output files.
- Roll back files created by an unsuccessful combined attempt.
- Open the output directory in the native file manager.
- Check local dependency availability and versions.
- Save privacy-safe diagnostic reports.
- Select and persist a local model directory.
- Download generic model artifacts only after explicit consent.
- Refuse Docling conversion when local model setup is incomplete.
- Configure Docling for local artifacts with remote services disabled.

## Design principles

1. Local document processing by default.
2. No telemetry, cloud uploads, or automatic document transmission.
3. Separate model setup network activity from document processing.
4. Never modify an original filing.
5. Never silently overwrite an existing output.
6. Preserve PDF-page boundaries for source verification.
7. Keep the interface understandable without technical knowledge.
8. Keep processing logic separate from the graphical interface.
9. Test Windows, macOS, and Linux behavior.
10. Treat optional dependencies and model licenses explicitly.
11. Prefer a small reliable application over a broad document-management suite.
12. Describe privacy controls accurately without claiming that application code replaces an operating-system firewall.

## Architecture

```text
src/filing_doc_converter/
├── app.py                    Application entry point and application identity
├── application_window.py     Environment-aware window features
├── main_window.py            Document queue and processing interface
├── model_management.py       Model directory settings and readiness
├── model_downloader.py       Background model setup and cancellation
├── docling_runtime.py        Local-only Docling configuration
├── ocr_pipeline.py           OCRmyPDF and Docling processing functions
├── ocr_worker.py             Background routing and cancellation
├── privacy_notice.py         Versioned first-run privacy explanation
├── system_diagnostics.py     Local dependency and version checks
└── system_check_dialog.py    Diagnostics and model setup interface
```

The current module name `ocr_pipeline.py` predates Docling integration. A later maintenance refactor may separate OCR and Docling code if the module becomes difficult to maintain.

## Completed milestones

### Foundation

- Public MIT-licensed repository.
- Python package structure.
- PySide6 application entry point.
- Ruff and pytest configuration.
- Cross-platform GitHub Actions workflow.

### Document queue

- PDF and folder drag and drop.
- Recursive PDF discovery.
- Duplicate prevention.
- Queue removal and clearing.
- Output-folder selection.

### OCR and extraction

- OCRmyPDF command construction without shell execution.
- Rotation correction, deskewing, and existing-text preservation.
- Background OCR execution and cancellation.
- Optional Docling Markdown and JSON conversion.
- Combined OCR-to-Docling routing.
- Stable output naming, including multi-dot filenames.
- Atomic non-overwrite publication and rollback protection.

### Diagnostics

- Lightweight startup availability checks.
- Detailed System Check dialog.
- OCRmyPDF, Tesseract, Docling, Python, and PySide6 reporting.
- Tesseract-language reporting.
- Privacy-safe diagnostic report export.
- Automatic output-option availability.
- Native output-folder opening.

### Privacy and model setup

- Versioned first-run privacy explanation.
- User-selected model directory persisted through QSettings.
- Managed model-directory environment override.
- Explicit consent before model downloads.
- Background download with cancellation.
- Successful-download readiness marker.
- Incomplete model directories rejected.
- Local Docling artifacts path.
- Remote Docling services explicitly disabled.
- External Docling plugins disabled.
- Supported offline-library controls scoped to conversion.
- Markdown and JSON disabled when models are not ready.
- Saved diagnostic reports omit model and document paths.

### Validation completed

- Automated tests on Windows, macOS, and Ubuntu.
- Native Windows dependency and GUI launch test.
- Successful processing of a badly scanned 50 MB, 38-page PDF.
- Searchable PDF, Markdown, and JSON validation.
- Combined-output filename regression testing.

## Immediate validation

Before merging the privacy and model-management milestone:

- Verify `docling-tools models download -o` with the installed Docling version.
- Select a dedicated model directory through System Check.
- Confirm the consent dialog appears before downloading.
- Confirm cancellation leaves the directory not ready.
- Confirm a successful download marks the directory ready.
- Disconnect networking or apply an outbound firewall rule.
- Convert a digital PDF into Markdown and JSON.
- Convert a scanned PDF into searchable PDF, Markdown, and JSON.
- Confirm no model download or remote service is attempted during conversion.
- Confirm expected output names, page markers, and content.

## Next milestones

### Processing reports

Generate a local manifest containing:

- Input filename and SHA-256 hash.
- Output filenames and hashes.
- Processing start and completion times.
- Application and converter versions.
- Selected options.
- Success, warning, cancellation, or failure status.
- No document content or remote transmission.

### Windows packaging

- Produce a folder-based Windows application build first.
- Evaluate Qt's supported deployment tooling and the project's native dependencies.
- Decide whether OCRmyPDF and Tesseract are bundled or prerequisites.
- Decide whether model artifacts are bundled, downloaded during explicit setup, or supplied separately.
- Create a Windows installer after the folder build passes.
- Test installation, launch, conversion, cancellation, repair, and uninstall on a clean Windows account or virtual machine.
- Sign the installer when a suitable code-signing process is available.
- Generate an SBOM and release-specific third-party notices.

### macOS packaging

- Produce a signed and notarized macOS application.
- Test Intel and Apple Silicon behavior as available.
- Verify local model storage and offline conversion.
- Provide an uninstall procedure.

### Initial release

Publish a clearly marked pre-release only after:

- Real-document smoke tests pass.
- Cross-platform automated tests pass.
- Installer behavior is verified on clean systems.
- Licensing and bundled dependencies are reviewed.
- Known limitations are documented.

## Deliberate non-goals

The initial application will not include:

- Legal analysis or legal conclusions.
- Citation validation.
- LLM chat.
- Retrieval-augmented generation or vector databases.
- Cloud OCR or cloud storage.
- User accounts.
- Docket management.
- PDF editing or Bates stamping.
- Automatic updates.
- Telemetry.

These features should be considered only after the conversion workflow is stable and there is a demonstrated need.

## Success criteria

The project succeeds when a nontechnical user can install the application, complete model setup with informed consent, disconnect networking, convert a legal PDF locally, open the results, and verify an AI-generated statement against the correct PDF page without using a terminal.
