# Filing Document Converter

> **Work in progress:** This project is under active development and is not ready for production or court use.

Filing Document Converter is a local-first desktop application for converting legal PDF filings into searchable PDFs and AI-readable Markdown.

## Initial goals

- Provide a simple graphical interface for Windows and macOS.
- Accept individual PDFs or folders through drag and drop.
- Create searchable PDF derivatives with OCRmyPDF.
- Create structured Markdown and optional JSON with Docling.
- Preserve the original document and PDF-page references.
- Process documents locally without telemetry or cloud uploads.

## Status

The repository currently contains the application scaffold only. OCR and document-conversion features will be added incrementally with tests.

## Planned milestones

1. Establish the cross-platform application and test structure.
2. Add drag-and-drop document selection and a processing queue.
3. Integrate OCRmyPDF for searchable-PDF output.
4. Integrate Docling for Markdown and JSON output.
5. Add page-reference preservation and processing reports.
6. Build and test Windows and macOS packages.

## Development

Python 3.11 or later is required.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m filing_doc_converter
```

Run the tests with:

```bash
pytest
```

## License

The application source code is licensed under the MIT License. Third-party components and models retain their respective licenses.
