param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationDirectory,
    [string]$SourceDirectory = "",
    [string]$WorkDirectory = ""
)

$ErrorActionPreference = "Stop"
$LockFile = Join-Path $PSScriptRoot "tesseract-bundle.lock.json"
if (-not (Test-Path $LockFile -PathType Leaf)) {
    throw "Missing lock file: $LockFile"
}
$LockData = Get-Content $LockFile -Raw | ConvertFrom-Json
$ExpectedVersion = "$($LockData.version)"
$DownloadUrl = "$($LockData.download_url)"
$ExpectedSha256 = "$($LockData.sha256)".ToLowerInvariant()
$RequiredRuntimeFiles = @($LockData.required_runtime_files)
$BundledLanguages = @($LockData.languages)

if ([string]::IsNullOrWhiteSpace($ExpectedVersion) -or [string]::IsNullOrWhiteSpace($DownloadUrl) -or [string]::IsNullOrWhiteSpace($ExpectedSha256)) {
    throw "Lock file is missing required fields (version, download_url, sha256)."
}
if ($BundledLanguages.Count -eq 0) {
    throw "Lock file must specify at least one required language."
}

$BundleRoot = if ([string]::IsNullOrWhiteSpace($WorkDirectory)) {
    Join-Path ([System.IO.Path]::GetTempPath()) "filing-doc-converter\tesseract-bundle"
} else {
    [System.IO.Path]::GetFullPath($WorkDirectory)
}
$DownloadDirectory = Join-Path $BundleRoot "download"
$ExtractDirectory = Join-Path $BundleRoot "extract"
$ArchivePath = Join-Path $DownloadDirectory "tesseract-ocr-w64-setup-$ExpectedVersion.exe"

$SourceProvided = -not [string]::IsNullOrWhiteSpace($SourceDirectory)
if ($SourceProvided) {
    $SourceDirectory = [System.IO.Path]::GetFullPath($SourceDirectory)
}
$DestinationDirectory = [System.IO.Path]::GetFullPath($DestinationDirectory)

if (-not $SourceProvided) {
    New-Item -ItemType Directory -Path $DownloadDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $ExtractDirectory -Force | Out-Null
    if (Test-Path $ArchivePath -PathType Leaf) {
        Remove-Item $ArchivePath -Force
    }
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ArchivePath
    $ActualHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedSha256) {
        throw "Tesseract archive checksum mismatch. Expected $ExpectedSha256, got $ActualHash."
    }

    if (Test-Path $ExtractDirectory) {
        Remove-Item $ExtractDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ExtractDirectory -Force | Out-Null
    $InstallArgs = @(
        "/SP-",
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOICONS",
        "/DIR=$ExtractDirectory"
    )
    $InstallProcess = Start-Process -FilePath $ArchivePath -ArgumentList $InstallArgs -Wait -PassThru
    if ($InstallProcess.ExitCode -ne 0) {
        throw "Installer extraction failed with exit code $($InstallProcess.ExitCode)."
    }
    $SourceDirectory = $ExtractDirectory
}

$Executable = Join-Path $SourceDirectory "tesseract.exe"
$Tessdata = Join-Path $SourceDirectory "tessdata"
if (-not (Test-Path $Executable -PathType Leaf)) {
    throw "Tesseract executable not found: $Executable"
}
$VersionOutput = (& $Executable --version 2>&1 | Select-Object -First 1).ToString()
if ($VersionOutput -notmatch [regex]::Escape($ExpectedVersion)) {
    throw "Expected Tesseract $ExpectedVersion, but found: $VersionOutput"
}
foreach ($Relative in $RequiredRuntimeFiles) {
    $RuntimePath = Join-Path $SourceDirectory $Relative
    if (-not (Test-Path $RuntimePath -PathType Leaf)) {
        throw "Required Tesseract runtime file missing: $Relative"
    }
}
foreach ($Language in $BundledLanguages) {
    $DataFile = Join-Path $Tessdata "$Language.traineddata"
    if (-not (Test-Path $DataFile -PathType Leaf)) {
        throw "Required Tesseract language data not found: $DataFile"
    }
}

if (Test-Path $DestinationDirectory) {
    Remove-Item $DestinationDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
Copy-Item (Join-Path $SourceDirectory "*") $DestinationDirectory -Force
Get-ChildItem $DestinationDirectory -Filter "unins*.exe" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $DestinationDirectory -Filter "unins*.dat" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

$DestinationTessdata = Join-Path $DestinationDirectory "tessdata"
if (Test-Path $DestinationTessdata) {
    Remove-Item $DestinationTessdata -Recurse -Force
}
New-Item -ItemType Directory -Path $DestinationTessdata -Force | Out-Null
foreach ($Language in $BundledLanguages) {
    Copy-Item (Join-Path $Tessdata "$Language.traineddata") $DestinationTessdata -Force
}

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
    if ($LASTEXITCODE -ne 0) {
        throw "Bundled Tesseract failed to list languages."
    }
    foreach ($Language in $BundledLanguages) {
        if ($Languages -notcontains $Language) {
            throw "Bundled Tesseract missing required language: $Language"
        }
    }
} finally {
    $env:TESSDATA_PREFIX = $PreviousTessdataPrefix
}

@(
    "Distribution: UB-Mannheim.TesseractOCR",
    "Version: $ExpectedVersion",
    "Download URL: $DownloadUrl",
    "SHA-256: $ExpectedSha256",
    "Languages: $($BundledLanguages -join ', ')",
    "Source directory: $SourceDirectory",
    "Runtime language data: tessdata"
) | Set-Content (Join-Path $DestinationDirectory "BUNDLE_INFO.txt") -Encoding utf8
