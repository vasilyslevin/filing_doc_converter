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

When OCR and Docling are selected together, Docling reads the newly created searchable PDF. When only Markdown or JSON is selected, Docling reads the original PDF directly.

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

## Design principles

1. Local processing by default.
2. No telemetry, cloud uploads, or automatic document transmission.
3. Never modify an original filing.
4. Never silently overwrite an existing output.
5. Preserve PDF-page boundaries for source verification.
6. Keep the interface understandable without technical knowledge.
7. Keep processing logic separate from the graphical interface.
8. Test Windows, macOS, and Linux behavior.
9. Treat optional dependencies and model licenses explicitly.
10. Prefer a small reliable application over a broad document-management suite.

## Architecture

```text
src/filing_doc_converter/
├── app.py                    Application entry point
├── application_window.py     Environment-aware window features
├── main_window.py            Document queue and processing interface
├── ocr_pipeline.py           OCRmyPDF and Docling processing functions
├── ocr_worker.py             Background routing and cancellation
├── system_diagnostics.py     Local dependency and version checks
└── system_check_dialog.py    Graphical diagnostics interface
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
- Stable output naming.
- Atomic non-overwrite publication and rollback protection.

### Diagnostics

- Lightweight startup availability checks.
- Detailed System Check dialog.
- OCRmyPDF, Tesseract, Docling, Python, and PySide6 reporting.
- Tesseract-language reporting.
- Privacy-safe diagnostic report export.
- Automatic output-option availability.
- Native output-folder opening.

## Next milestones

### End-to-end validation

Test actual conversion rather than mocked integrations using synthetic or public documents:

- Digitally generated judicial opinion.
- Image-only scanned filing.
- Mixed digital and scanned PDF.
- Multicolumn document.
- Document containing tables and footnotes.
- Several-hundred-page record.
- Password-protected and intentionally damaged PDFs.
- Filenames containing spaces and Unicode characters.

Verify output text, page markers, filenames, cancellation, retries, rollback, and memory use.

### Processing reports

Generate a local manifest containing:

- Input filename and SHA-256 hash.
- Output filenames and hashes.
- Processing start and completion times.
- Application and converter versions.
- Selected options.
- Success, warning, cancellation, or failure status.
- No document content or remote transmission.

### Packaging

- Produce a Windows installer.
- Produce a signed and notarized macOS application.
- Test Intel and Apple Silicon behavior as available.
- Decide which dependencies are bundled and which are prerequisites.
- Generate an SBOM and complete third-party notices for each release.
- Provide an uninstall procedure.
- Keep automatic updates disabled unless a secure update process is later designed.

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

The project succeeds when a nontechnical user can drag in a legal PDF, select the desired outputs, process it locally, open the results, and verify an AI-generated statement against the correct PDF page without using a terminal.
