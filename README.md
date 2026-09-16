# Filing Document Converter

> **Work in progress:** This project is under active development and is not ready for production or court use.

Filing Document Converter is a local-first desktop application for converting legal PDF filings into searchable PDFs and AI-readable Markdown or JSON.

## Current features

- Drag-and-drop PDF and folder queue.
- Searchable PDF creation through OCRmyPDF and Tesseract.
- Markdown and structured JSON conversion through Docling.
- Combined OCR-to-Docling processing for scanned documents.
- Background processing with progress, cancellation, and per-file results.
- Original-file and existing-output protection.
- Stable output names and PDF page-break markers.
- System Check dialog with component versions and OCR languages.
- Automatic disabling of unavailable output options.
- Privacy-safe diagnostic reports.
- Native Open Output Folder action.
- Local processing without telemetry or cloud uploads.

## Status

The application is functional but remains pre-alpha. Use copies of documents and verify all generated material against the original PDF.

Planned work includes end-to-end testing with representative legal documents, processing-report improvements, and signed Windows and macOS packages.

## Installation

Python 3.11 or later is required.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m filing_doc_converter
```

Install optional conversion components as needed:

```bash
# OCRmyPDF Python package
python -m pip install -e ".[ocr]"

# Docling for Markdown and JSON
python -m pip install -e ".[docling]"

# Both optional converters
python -m pip install -e ".[full]"
```

OCRmyPDF also requires an OCR engine and supporting system components. Tesseract must be installed and available on `PATH`.

### macOS

Homebrew provides OCRmyPDF and Tesseract:

```bash
brew install ocrmypdf tesseract
python -m pip install -e ".[docling]"
```

### Windows

Install OCRmyPDF and Tesseract according to their official Windows instructions and ensure both executables are available on `PATH`. Then install the application extras:

```powershell
python -m pip install -e ".[full]"
```

### Linux

Install OCRmyPDF and Tesseract using the distribution package manager, then install the Docling extra. Package names vary by distribution.

## Using the application

1. Start the application with `python -m filing_doc_converter`.
2. Open **Help > System Check** and verify the required components.
3. Drop PDF files or a folder into the application.
4. Select Searchable PDF, Markdown for AI, Structured JSON, or a combination.
5. Confirm or change the output folder.
6. Select **Process Documents**.
7. Use **Open Output Folder** after processing completes.

Unavailable output formats are disabled automatically. The System Check provides installation guidance and can save a diagnostic report.

## Output files

For an input named `filing.pdf`, combined processing produces:

```text
Converted/
├── filing.searchable.pdf
├── filing.md
└── filing.json
```

Existing output files are not overwritten. If a later stage fails, files created during that unsuccessful attempt are rolled back when safe to do so.

Markdown output includes this page separator:

```html
<!-- PDF_PAGE_BREAK -->
```

Generated Markdown and JSON are derivative working files. The original PDF remains the authoritative source for page verification and legal citation.

## System Check

The System Check reports:

- Application, operating-system, architecture, Python, and PySide6 versions.
- OCRmyPDF availability and version.
- Tesseract availability, version, and installed OCR languages.
- Docling availability and version.
- Platform-specific installation guidance.

The saved diagnostic report does not intentionally include usernames, hostnames, home-directory paths, queued document paths, output paths, environment variables, or document contents.

## Development

Run the tests with:

```bash
pytest
```

Run lint checks with:

```bash
ruff check .
```

GitHub Actions runs both commands on Ubuntu, Windows, and macOS. Tests mock optional converters and do not download Docling models or require OCRmyPDF.

## Privacy and security

- Documents are processed locally.
- The application does not include telemetry, cloud uploads, or automatic updates.
- Input PDFs are never overwritten.
- Output publication rejects existing destinations.
- Diagnostic reports exclude document and user paths.

## License

The application source code is licensed under the MIT License. Third-party components and models retain their respective licenses. Review `THIRD_PARTY_NOTICES.md` before distributing packaged builds.
