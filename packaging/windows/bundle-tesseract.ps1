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
$InstallerTimeoutSeconds = 600

function Write-Stage {
    param([string]$Message)
    Write-Host "[bundle-tesseract] $Message"
}

function Download-Installer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    $CurlCommand = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($null -ne $CurlCommand) {
        & $CurlCommand.Source `
            --fail `
            --location `
            --retry 3 `
            --retry-all-errors `
            --connect-timeout 30 `
            --max-time 300 `
            --output $Destination `
            $Url
        if ($LASTEXITCODE -eq 0) {
            return
        }
        throw "curl.exe download failed with exit code $LASTEXITCODE."
    }

    $LastError = $null
    foreach ($Attempt in 1..3) {
        try {
            Invoke-WebRequest -Uri $Url -OutFile $Destination -TimeoutSec 300
            return
        } catch {
            $LastError = $_
            if ($Attempt -lt 3) {
                Start-Sleep -Seconds 2
            }
        }
    }
    throw "Fallback download failed after 3 attempts: $LastError"
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
    Write-Stage "Preparing download and extraction directories."
    New-Item -ItemType Directory -Path $DownloadDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $ExtractDirectory -Force | Out-Null

    $HaveValidArchive = $false
    if (Test-Path $ArchivePath -PathType Leaf) {
        Write-Stage "Found cached installer archive at $ArchivePath. Verifying checksum."
        $CachedHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($CachedHash -eq $ExpectedSha256) {
            $HaveValidArchive = $true
            Write-Stage "Cached installer checksum verified."
        } else {
            Write-Stage "Cached installer checksum mismatch; deleting cached archive."
            Remove-Item $ArchivePath -Force
        }
    }

    if (-not $HaveValidArchive) {
        Write-Stage "Downloading pinned Tesseract installer."
        Download-Installer -Url $DownloadUrl -Destination $ArchivePath
        Write-Stage "Installer download completed."
    }

    Write-Stage "Verifying installer checksum."
    $ActualHash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedSha256) {
        throw "Tesseract archive checksum mismatch. Expected $ExpectedSha256, got $ActualHash."
    }
    Write-Stage "Installer checksum verified."

    if (Test-Path $ExtractDirectory) {
        Remove-Item $ExtractDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ExtractDirectory -Force | Out-Null
    $InstallerLogPath = Join-Path $BundleRoot "installer.log"
    $InstallArgs = @(
        "/SP-",
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOICONS",
        "/CURRENTUSER",
        "/LOG=`"$InstallerLogPath`"",
        "/DIR=$ExtractDirectory"
    )
    Write-Stage "Launching installer extraction process."
    $InstallProcess = Start-Process -FilePath $ArchivePath -ArgumentList $InstallArgs -PassThru
    $InstallerFinished = $true
    try {
        Wait-Process -Id $InstallProcess.Id -Timeout $InstallerTimeoutSeconds -ErrorAction Stop
    } catch {
        $InstallerFinished = $false
    }
    if (-not $InstallerFinished) {
        Write-Stage "Installer timed out after $InstallerTimeoutSeconds seconds. Terminating process tree."
        & taskkill.exe /PID $InstallProcess.Id /T /F | Out-Null
        throw "Installer extraction timed out after $InstallerTimeoutSeconds seconds (PID $($InstallProcess.Id))."
    }
    Write-Stage "Installer extraction process completed."
    if ($InstallProcess.ExitCode -ne 0) {
        throw "Installer extraction failed with exit code $($InstallProcess.ExitCode)."
    }
    $SourceDirectory = $ExtractDirectory
    Write-Stage "Installer extraction succeeded."
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
Write-Stage "Copying Tesseract runtime files into package directory."
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
    Write-Stage "Verifying bundled language data with tesseract --list-langs."
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
Write-Stage "Bundled language verification succeeded."

@(
    "Distribution: UB-Mannheim.TesseractOCR",
    "Version: $ExpectedVersion",
    "Download URL: $DownloadUrl",
    "SHA-256: $ExpectedSha256",
    "Languages: $($BundledLanguages -join ', ')",
    "Source directory: $SourceDirectory",
    "Runtime language data: tessdata"
) | Set-Content (Join-Path $DestinationDirectory "BUNDLE_INFO.txt") -Encoding utf8
Write-Stage "Tesseract bundle metadata written."
