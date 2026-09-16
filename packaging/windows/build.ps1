param(
    [string]$Python = "python",
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $RepositoryRoot "build\windows"
} else {
    $OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
}

$GuiEntry = Join-Path $PSScriptRoot "FilingDocumentConverter.py"
$ToolsEntry = Join-Path $PSScriptRoot "docling-tools.py"

if (Test-Path $OutputDirectory) {
    Remove-Item $OutputDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null

$NuitkaArguments = @(
    "-m", "nuitka",
    "--mode=standalone",
    "--enable-plugin=pyside6",
    "--windows-console-mode=attach",
    "--assume-yes-for-downloads",
    "--remove-output",
    "--output-dir=$OutputDirectory",
    "--company-name=Filing Document Converter",
    "--product-name=Filing Document Converter",
    "--file-description=Local-first filing document conversion",
    "--file-version=0.1.0.0",
    "--product-version=0.1.0.0",
    "--include-package=filing_doc_converter",
    "--include-package=docling",
    "--include-package-data=docling",
    "--include-package-data=docling_core",
    "--include-package-data=docling_parse",
    "--main=$GuiEntry",
    "--main=$ToolsEntry"
)

Push-Location $RepositoryRoot
try {
    & $Python @NuitkaArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka failed with exit code $LASTEXITCODE."
    }

    $Distribution = Join-Path $OutputDirectory "FilingDocumentConverter.dist"
    if (-not (Test-Path $Distribution -PathType Container)) {
        $Candidates = @(Get-ChildItem $OutputDirectory -Directory -Filter "*.dist")
        if ($Candidates.Count -ne 1) {
            throw "Could not identify the Nuitka distribution directory."
        }
        $Distribution = $Candidates[0].FullName
    }

    $GuiExecutable = Join-Path $Distribution "FilingDocumentConverter.exe"
    if (-not (Test-Path $GuiExecutable -PathType Leaf)) {
        throw "FilingDocumentConverter.exe was not produced."
    }

    $ToolsExecutable = Join-Path $Distribution "docling-tools.exe"
    Copy-Item $GuiExecutable $ToolsExecutable -Force
    Copy-Item (Join-Path $RepositoryRoot "LICENSE") $Distribution -Force
    Copy-Item (Join-Path $RepositoryRoot "THIRD_PARTY_NOTICES.md") $Distribution -Force
    Copy-Item (Join-Path $PSScriptRoot "PACKAGING_NOTES.txt") $Distribution -Force

    $HashFile = Join-Path $Distribution "SHA256SUMS.txt"
    $Hashes = Get-ChildItem $Distribution -File -Recurse |
        Where-Object { $_.FullName -ne $HashFile } |
        Sort-Object FullName |
        ForEach-Object {
            $RelativePath = [System.IO.Path]::GetRelativePath(
                $Distribution,
                $_.FullName
            ).Replace("\", "/")
            $Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$Hash  $RelativePath"
        }
    $Hashes | Set-Content $HashFile -Encoding utf8

    Write-Host "Windows development package created at: $Distribution"
} finally {
    Pop-Location
}
