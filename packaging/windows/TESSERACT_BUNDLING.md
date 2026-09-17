# Optional Tesseract runtime bundle

The Windows packaging script can include a local Tesseract runtime without downloading software during the build.

## Supported source

The prepared bundle is pinned to `UB-Mannheim.TesseractOCR` version `5.4.0.20240606`. The source directory must contain:

- `tesseract.exe`
- Runtime DLL files
- `tessdata/eng.traineddata`

For the currently tested installation, the source is `D:\apps\Tesseract-OCR`.

## Build command

```powershell
./packaging/windows/build.ps1 -TesseractRoot "D:\apps\Tesseract-OCR"
```

The runtime is copied into `tools/tesseract` in the application distribution. At startup, the packaged application prepends that directory to `PATH` and sets `TESSDATA_PREFIX` to its bundled `tessdata` directory. A system Tesseract installation remains the fallback when no runtime is bundled.

The bundling script validates the pinned version and confirms that English language data can be loaded. The generated SHA-256 manifest includes `tesseract.exe` and `eng.traineddata` when bundling is enabled.

## Distribution review

This switch is intentionally optional. CI does not yet download or redistribute the UB Mannheim installer. Before enabling it for published artifacts, verify the installer checksum and include all required Tesseract, Leptonica, image-library, and trained-data license notices.
