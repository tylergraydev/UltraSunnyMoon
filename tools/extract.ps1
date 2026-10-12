param(
    [Parameter(Mandatory=$true)][string]$BaseImage,
    [Parameter(Mandatory=$true)][string]$UpdateImage,
    [string]$Ctrtool = "$PSScriptRoot/../.local/ctrtool/ctrtool.exe"
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$baseInput = (Resolve-Path -LiteralPath $BaseImage).Path
$updateInput = (Resolve-Path -LiteralPath $UpdateImage).Path
$extractor = (Resolve-Path -LiteralPath $Ctrtool).Path
Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force extracted/base, extracted/update, analysis/private | Out-Null
    # Full extractor logs can contain keys and signatures: keep them local.
    & $extractor --exheader=extracted/base/exheader.bin --exefsdir=extracted/base/exefs --plainrgn=extracted/base/plain.bin $baseInput *> analysis/private/base-ctrtool.txt
    if ($LASTEXITCODE -ne 0) { throw 'Base extraction failed; see the private log.' }
    & $extractor --contents=extracted/update/contents --tmd=extracted/update/title.tmd $updateInput *> analysis/private/update-ctrtool.txt
    if ($LASTEXITCODE -ne 0) { throw 'Update container extraction failed; see the private log.' }
    $contents = @(Get-ChildItem -LiteralPath extracted/update -File -Filter 'contents.*')
    if ($contents.Count -ne 1) { throw 'Expected one update content; inspect the container before proceeding.' }
    & $extractor --exheader=extracted/update/exheader.bin --exefsdir=extracted/update/exefs --plainrgn=extracted/update/plain.bin $contents[0].FullName *> analysis/private/update-content-ctrtool.txt
    if ($LASTEXITCODE -ne 0) { throw 'Update executable extraction failed; see the private log.' }
    Write-Output 'Base and update executables extracted separately under extracted/. No RomFS resources extracted.'
} finally {
    Pop-Location
}
