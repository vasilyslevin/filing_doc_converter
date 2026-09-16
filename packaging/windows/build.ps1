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

$SourceRoot = Join-Path $RepositoryRoot "src"
$GuiEntry = Join-Path $PSScriptRoot "FilingDocumentConverter.py"
$ToolsEntry = Join-Path $PSScriptRoot "docling-tools.py"
$StagingDirectory = Join-Path $OutputDirectory "dist"
$WorkDirectory = Join-Path $OutputDirectory "work"
$SpecDirectory = Join-Path $OutputDirectory "spec"

if (Test-Path $OutputDirectory) {
    Remove-Item $OutputDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $WorkDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $SpecDirectory -Force | Out-Null

$CommonArguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--paths=$SourceRoot",
    "--distpath=$StagingDirectory",
    "--specpath=$SpecDirectory",
    "--collect-all=docling",
    "--collect-all=docling_core",
    "--collect-all=docling_parse",
    "--hidden-import=docling.cli.tools",
    "--hidden-import=docling.document_converter"
)

function Invoke-PackageBuild {
    param(
        [string]$Name,
        [string]$EntryPoint,
        [string]$ConsoleMode
    )

    $Arguments = $CommonArguments + @(
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
    Invoke-PackageBuild -Name "FilingDocumentConverter" -EntryPoint $GuiEntry -ConsoleMode "--windowed"
    Invoke-PackageBuild -Name "docling-tools" -EntryPoint $ToolsEntry -ConsoleMode "--console"

    $Distribution = Join-Path $StagingDirectory "FilingDocumentConverter"
    $ToolsDistribution = Join-Path $StagingDirectory "docling-tools"
    $GuiExecutable = Join-Path $Distribution "FilingDocumentConverter.exe"
    $ToolsExecutable = Join-Path $ToolsDistribution "docling-tools.exe"

    if (-not (Test-Path $GuiExecutable -PathType Leaf)) {
        throw "FilingDocumentConverter.exe was not produced."
    }
    if (-not (Test-Path $ToolsExecutable -PathType Leaf)) {
        throw "docling-tools.exe was not produced."
    }

    Copy-Item (Join-Path $ToolsDistribution "*") $Distribution -Recurse -Force
    Remove-Item $ToolsDistribution -Recurse -Force
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
