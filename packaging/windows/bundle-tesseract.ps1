param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDirectory,
    [Parameter(Mandatory = $true)]
    [string]$DestinationDirectory
)

$ErrorActionPreference = "Stop"
$ExpectedVersion = "5.4.0.20240606"
$SourceDirectory = [System.IO.Path]::GetFullPath($SourceDirectory)
$DestinationDirectory = [System.IO.Path]::GetFullPath($DestinationDirectory)
$Executable = Join-Path $SourceDirectory "tesseract.exe"
$Tessdata = Join-Path $SourceDirectory "tessdata"
$EnglishData = Join-Path $Tessdata "eng.traineddata"

if (-not (Test-Path $Executable -PathType Leaf)) {
    throw "Tesseract executable not found: $Executable"
}
if (-not (Test-Path $EnglishData -PathType Leaf)) {
    throw "English Tesseract language data not found: $EnglishData"
}

$VersionOutput = (& $Executable --version 2>&1 | Select-Object -First 1).ToString()
if ($VersionOutput -notmatch [regex]::Escape($ExpectedVersion)) {
    throw "Expected Tesseract $ExpectedVersion, but found: $VersionOutput"
}

if (Test-Path $DestinationDirectory) {
    Remove-Item $DestinationDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
Copy-Item $Executable $DestinationDirectory -Force
Get-ChildItem $SourceDirectory -Filter "*.dll" -File |
    Copy-Item -Destination $DestinationDirectory -Force
Copy-Item $Tessdata (Join-Path $DestinationDirectory "tessdata") -Recurse -Force

foreach ($Pattern in @("LICENSE*", "README*", "AUTHORS*")) {
    Get-ChildItem $SourceDirectory -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Copy-Item -Destination $DestinationDirectory -Force
}

$BundledExecutable = Join-Path $DestinationDirectory "tesseract.exe"
$BundledTessdata = Join-Path $DestinationDirectory "tessdata"
$PreviousTessdataPrefix = $env:TESSDATA_PREFIX
try {
    $env:TESSDATA_PREFIX = $BundledTessdata
    $Languages = & $BundledExecutable --list-langs 2>&1
    if ($LASTEXITCODE -ne 0 -or $Languages -notcontains "eng") {
        throw "Bundled Tesseract could not load English language data."
    }
} finally {
    $env:TESSDATA_PREFIX = $PreviousTessdataPrefix
}

@(
    "Distribution: UB-Mannheim.TesseractOCR",
    "Version: $ExpectedVersion",
    "Source directory: supplied at package build time",
    "Runtime language data: tessdata"
) | Set-Content (Join-Path $DestinationDirectory "BUNDLE_INFO.txt") -Encoding utf8
