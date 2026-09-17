# Third-Party Notices

Filing Document Converter is licensed under the MIT License. It uses or can integrate with third-party software and model artifacts distributed under separate licenses.

This file is a development-stage notice. Before publishing packaged executables, the release process must generate and review a complete software bill of materials covering all direct and transitive packages, native libraries, OCR engines, model files, dictionaries, and other artifacts included in or downloaded by each release.

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
- Windows bundle source: https://github.com/UB-Mannheim/tesseract/releases/tag/v5.4.0.20240606 (`tesseract-ocr-w64-setup-5.4.0.20240606.exe`, SHA-256 `c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9`).
- Bundled language data: `eng.traineddata`, `osd.traineddata`.
- Distribution review: Include required copyright, license, and notice materials for Tesseract and bundled native dependencies (for example Leptonica/image libraries).

### Docling

- Purpose: Structured PDF conversion to Markdown and JSON.
- License: MIT License for the Docling codebase.
- Project: https://github.com/docling-project/docling
- Distribution review: Docling models, OCR engines, and transitive packages may use separate licenses. Review every model and optional component included in or downloaded for a build.

### RapidOCR and PaddleOCR-derived artifacts

- Purpose: Text detection, orientation classification, recognition, and character dictionaries used during document conversion.
- Projects: https://github.com/RapidAI/RapidOCR and https://github.com/PaddlePaddle/PaddleOCR
- Distribution review: Model weights and dictionaries may have terms distinct from the Python packages. Record the exact artifact name, version, source, copyright notice, and license before redistribution.

## Model delivery

The source application does not bundle model artifacts. Model setup is a separate user-approved operation that may retrieve generic artifacts from hosting services used by Docling or its dependencies, including Hugging Face or ModelScope.

The model downloader is not supplied with queued document paths, filenames, document content, extracted text, or generated outputs. Hosting services may still receive ordinary network metadata associated with downloading files.

A release must not describe model files as covered by the application's MIT License unless that conclusion has been verified for each artifact.

## Development components

The project also uses development and build tools including setuptools, pytest, pytest-qt, Ruff, and GitHub Actions. These tools and their dependencies retain their respective licenses.

Future Windows packaging may use Qt deployment tooling, Nuitka, an installer generator, signing tools, and additional native libraries. Their licenses and redistribution terms must be added before release.

## Packaging rule

A Windows or macOS release must not be published until the release-specific dependency and model inventory has been reviewed. The inventory should identify:

- Package, native component, or model name.
- Exact version or artifact revision.
- License identifier and license text.
- Copyright and attribution requirements.
- Source or download location.
- Whether the component is bundled, downloaded during explicit setup, or externally installed.
- Whether source-code availability or relinking rights must be provided.
- Native libraries included in the application package.
- Model files, dictionaries, and model-specific terms.

The release should include an SBOM, this notice, all required license texts, and any upstream NOTICE files.

No statement in this file is legal advice or a substitute for reviewing the applicable license text.
