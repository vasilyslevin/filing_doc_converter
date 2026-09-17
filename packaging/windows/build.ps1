param(
    [string]$Python = "python",
    [string]$OutputDirectory = "",
    [string]$TesseractRoot = ""
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $RepositoryRoot "build\windows"
} else {
    $OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
}

$SourceRoot = Join-Path $RepositoryRoot "src"
$GuiEntry = Join-Path $PSScriptRoot "FilingDocumentConverter.py"
$ToolsEntry = Join-Path $PSScriptRoot "docling-tools.py"
$OcrEntry = Join-Path $SourceRoot "filing_doc_converter\ocrmypdf_entry.py"
$IconGenerator = Join-Path $PSScriptRoot "create_icon.py"
$IconSource = Join-Path $SourceRoot "filing_doc_converter\assets\app_icon.svg"
$IconPath = Join-Path $OutputDirectory "FilingDocumentConverter.ico"
$TesseractBundler = Join-Path $PSScriptRoot "bundle-tesseract.ps1"
$StagingDirectory = Join-Path $OutputDirectory "dist"
$WorkDirectory = Join-Path $OutputDirectory "work"
$SpecDirectory = Join-Path $OutputDirectory "spec"

if (Test-Path $OutputDirectory) {
    Remove-Item $OutputDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $WorkDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $SpecDirectory -Force | Out-Null

& $Python $IconGenerator $IconPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $IconPath -PathType Leaf)) {
    throw "Could not generate the Windows application icon."
}

$CommonArguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--paths=$SourceRoot",
    "--distpath=$StagingDirectory",
    "--specpath=$SpecDirectory"
)
$DoclingArguments = @(
    "--collect-all=docling",
    "--collect-all=docling_core",
    "--collect-all=docling_parse",
    "--collect-all=rapidocr",
    "--collect-all=transformers",
    "--hidden-import=docling.cli.tools",
    "--hidden-import=docling.document_converter"
)
$GuiArguments = $DoclingArguments + @(
    "--icon=$IconPath",
    "--add-data=$IconSource;filing_doc_converter/assets"
)
$OcrArguments = @(
    "--collect-all=ocrmypdf",
    "--hidden-import=ocrmypdf.__main__"
)

function Invoke-PackageBuild {
    param(
        [string]$Name,
        [string]$EntryPoint,
        [string]$ConsoleMode,
        [string[]]$AdditionalArguments = @()
    )

    $Arguments = $CommonArguments + $AdditionalArguments + @(
        "--workpath=$(Join-Path $WorkDirectory $Name)",
        "--name=$Name",
        $ConsoleMode,
        $EntryPoint
    )
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed for $Name with exit code $LASTEXITCODE."
    }
}

Push-Location $RepositoryRoot
try {
    Invoke-PackageBuild -Name "FilingDocumentConverter" -EntryPoint $GuiEntry -ConsoleMode "--windowed" -AdditionalArguments $GuiArguments
    Invoke-PackageBuild -Name "docling-tools" -EntryPoint $ToolsEntry -ConsoleMode "--console" -AdditionalArguments $DoclingArguments
    Invoke-PackageBuild -Name "ocrmypdf" -EntryPoint $OcrEntry -ConsoleMode "--console" -AdditionalArguments $OcrArguments

    $Distribution = Join-Path $StagingDirectory "FilingDocumentConverter"
    $ToolsDistribution = Join-Path $StagingDirectory "docling-tools"
    $OcrDistribution = Join-Path $StagingDirectory "ocrmypdf"
    $GuiExecutable = Join-Path $Distribution "FilingDocumentConverter.exe"
    $ToolsExecutable = Join-Path $ToolsDistribution "docling-tools.exe"
    $OcrExecutable = Join-Path $OcrDistribution "ocrmypdf.exe"

    if (-not (Test-Path $GuiExecutable -PathType Leaf)) {
        throw "FilingDocumentConverter.exe was not produced."
    }
    if (-not (Test-Path $ToolsExecutable -PathType Leaf)) {
        throw "docling-tools.exe was not produced."
    }
    if (-not (Test-Path $OcrExecutable -PathType Leaf)) {
        throw "ocrmypdf.exe was not produced."
    }

    Copy-Item (Join-Path $ToolsDistribution "*") $Distribution -Recurse -Force
    Copy-Item (Join-Path $OcrDistribution "*") $Distribution -Recurse -Force
    Remove-Item $ToolsDistribution -Recurse -Force
    Remove-Item $OcrDistribution -Recurse -Force

    & (Join-Path $Distribution "docling-tools.exe") --runtime-check
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged Docling runtime check failed with exit code $LASTEXITCODE."
    }

    $TesseractBundled = -not [string]::IsNullOrWhiteSpace($TesseractRoot)
    if ($TesseractBundled) {
        $TesseractDestination = Join-Path $Distribution "tools\tesseract"
        & $TesseractBundler -SourceDirectory $TesseractRoot -DestinationDirectory $TesseractDestination
        if ($LASTEXITCODE -ne 0) {
            throw "Tesseract bundling failed with exit code $LASTEXITCODE."
        }
    }

    Copy-Item (Join-Path $RepositoryRoot "LICENSE") $Distribution -Force
    Copy-Item (Join-Path $RepositoryRoot "THIRD_PARTY_NOTICES.md") $Distribution -Force
    Copy-Item (Join-Path $PSScriptRoot "PACKAGING_NOTES.txt") $Distribution -Force

    $HashTargets = @(
        "FilingDocumentConverter.exe",
        "docling-tools.exe",
        "ocrmypdf.exe",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "PACKAGING_NOTES.txt"
    )
    if ($TesseractBundled) {
        $HashTargets += @(
            "tools\tesseract\tesseract.exe",
            "tools\tesseract\tessdata\eng.traineddata",
            "tools\tesseract\BUNDLE_INFO.txt"
        )
    }
    $Hashes = foreach ($RelativePath in $HashTargets) {
        $Target = Join-Path $Distribution $RelativePath
        if (-not (Test-Path $Target -PathType Leaf)) {
            throw "Cannot hash missing package file: $RelativePath"
        }
        $Digest = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
        if ([string]::IsNullOrWhiteSpace($Digest)) {
            throw "Could not calculate SHA-256 for package file: $RelativePath"
        }
        "$($Digest.ToLowerInvariant())  $RelativePath"
    }
    $Hashes | Set-Content (Join-Path $Distribution "SHA256SUMS.txt") -Encoding utf8

    Write-Host "Windows development package created at: $Distribution"
} finally {
    Pop-Location
}
