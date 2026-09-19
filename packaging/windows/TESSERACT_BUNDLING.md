# Bundled Windows Tesseract runtime

Windows packaging uses a pinned UB Mannheim Tesseract release:

- Distribution: `UB-Mannheim/tesseract`
- Version: `5.4.0.20240606`
- Source URL: `https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe`
- SHA-256: `c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9`
- Lock file: `packaging/windows/tesseract-bundle.lock.json`

## What gets bundled

The build places Tesseract under `tools/tesseract` in the PyInstaller distribution and verifies:

- `tesseract.exe`
- Required runtime DLLs listed in `tesseract-bundle.lock.json`
- Minimal language data required by this app:
  - `eng.traineddata`
  - `osd.traineddata`

No runtime download occurs when the packaged app runs.

## Build usage

Default (download pinned release during packaging):

```powershell
./packaging/windows/build.ps1
```

Optional local source override (still validated against pinned runtime expectations):

```powershell
./packaging/windows/build.ps1 -TesseractRoot "D:\apps\Tesseract-OCR"
```

## Checksum refresh procedure

1. Choose the new UB Mannheim release and update `version`, `download_url`, and `required_runtime_files` in `tesseract-bundle.lock.json`.
2. Download the installer and compute SHA-256:

```powershell
$Url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
Invoke-WebRequest -Uri $Url -OutFile tesseract-installer.exe
(Get-FileHash -LiteralPath .\tesseract-installer.exe -Algorithm SHA256).Hash.ToLowerInvariant()
```

3. Copy the digest into `sha256` in the lock file.
4. Re-run the Windows package workflow and confirm bundled smoke tests pass.

## Local verification commands

After `build.ps1` completes:

```powershell
$Dist = Join-Path $PWD "build\windows\dist\SourceDocumentConverter"
$env:TESSDATA_PREFIX = Join-Path $Dist "tools\tesseract\tessdata"
& (Join-Path $Dist "tools\tesseract\tesseract.exe") --version
& (Join-Path $Dist "tools\tesseract\tesseract.exe") --list-langs
```

Expected languages include `eng` and `osd`.

## Licensing obligations

Redistributing this package requires preserving applicable license/notice files for Tesseract and bundled native dependencies (including Leptonica and image libraries) and keeping `THIRD_PARTY_NOTICES.md` aligned with packaged contents.
