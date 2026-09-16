# Filing Document Converter

> **Work in progress:** This project is under active development and is not ready for production or court use.

Filing Document Converter is a local-first desktop application for converting legal PDF filings into searchable PDFs and AI-readable Markdown/JSON.

## Initial goals

- Provide a simple graphical interface for Windows and macOS.
- Accept individual PDFs or folders through drag and drop.
- Create searchable PDF derivatives with OCRmyPDF.
- Create structured Markdown and optional JSON with Docling.
- Preserve the original document and PDF-page references.
- Process documents locally without telemetry or cloud uploads.

## Status

Current implementation is still **WIP**. It supports queueing PDFs and processing each file into:

- Searchable PDF (via optional OCRmyPDF dependency)
- Markdown and/or structured JSON (via optional Docling dependency)

## Planned milestones

1. Add page-reference preservation details to generated outputs.
2. Improve processing reports and UX polish.
3. Build and test Windows and macOS packages.

## Development

Python 3.11 or later is required.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m filing_doc_converter
```

Optional conversion extras:

```bash
# OCR output only
python -m pip install -e ".[ocr]"

# Markdown/JSON output only
python -m pip install -e ".[docling]"

# All optional converters
python -m pip install -e ".[full]"
```

If optional extras are missing, the app still launches. Processing will fail only for the selected output types that require unavailable dependencies.

Run the tests with:

```bash
pytest
```

## License

The application source code is licensed under the MIT License. Third-party components and models retain their respective licenses.
