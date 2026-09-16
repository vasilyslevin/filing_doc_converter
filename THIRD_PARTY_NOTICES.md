# Third-Party Notices

Filing Document Converter is licensed under the MIT License. It uses or can integrate with third-party software distributed under separate licenses.

This file is an initial development-stage notice. Before publishing packaged executables, the release process must generate and review a complete software bill of materials covering all direct and transitive packages, native libraries, OCR engines, and model files included in each installer.

## Runtime components

### PySide6 and Qt for Python

- Purpose: Desktop graphical interface.
- License options: LGPL-3.0, GPL-2.0, GPL-3.0, or commercial terms, depending on the distribution used.
- Project: https://doc.qt.io/qtforpython-6/
- Distribution review: Confirm LGPL compliance, dynamic-linking arrangements, replacement rights, notices, and any applicable Qt module licenses.

### OCRmyPDF

- Purpose: Creation of searchable PDF derivatives.
- License: Mozilla Public License 2.0.
- Project: https://github.com/ocrmypdf/OCRmyPDF
- Distribution review: Preserve required notices and make source-level modifications to covered OCRmyPDF files available as required by the MPL.

### Tesseract OCR

- Purpose: Optical character recognition engine used by OCRmyPDF.
- License: Apache License 2.0.
- Project: https://github.com/tesseract-ocr/tesseract
- Distribution review: Include required copyright, license, and notice materials when bundled.

### Docling

- Purpose: Structured PDF conversion to Markdown and JSON.
- License: MIT License for the Docling codebase.
- Project: https://github.com/docling-project/docling
- Distribution review: Docling models, OCR engines, and transitive packages may use separate licenses. Review every model and optional component included in a build.

## Development components

The project also uses development and build tools including setuptools, pytest, pytest-qt, Ruff, and GitHub Actions. These tools and their dependencies retain their respective licenses.

## Packaging rule

A Windows or macOS release must not be published until the release-specific dependency inventory has been reviewed. The inventory should identify:

- Package and component name.
- Exact version.
- License identifier.
- Source location.
- Whether the component is bundled or externally installed.
- Required attribution or license text.
- Model files and model-specific terms.
- Native libraries included in the application package.

No statement in this file is legal advice or a substitute for reviewing the applicable license text.
