# Prepare two fresh portable profiles; launch/observation is a separate step.
param([string]$Destination = 'analysis/private/azahar-runtime')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path "$PSScriptRoot/..").Path
$runtimeRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot $Destination))
$privateRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'analysis/private')) + [IO.Path]::DirectorySeparatorChar
if (-not $runtimeRoot.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Runtime destination must stay inside analysis/private.'
}
if (Test-Path -LiteralPath $runtimeRoot) { throw 'Use a new runtime directory.' }
$archivePath = Join-Path $projectRoot '.local/azahar-2126.2.zip'
$archiveHash = 'aa6d4c631c883355e50f5f62fd26a0e053d63e4cc29b8ded6b3b7d175ec3864e'
$downloadUrl = 'https://github.com/azahar-emu/azahar/releases/download/2126.2/azahar-windows-msys2-2126.2.zip'
if (-not (Test-Path -LiteralPath $archivePath)) {
    New-Item -ItemType Directory -Force (Split-Path $archivePath) | Out-Null
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -UseBasicParsing $downloadUrl -OutFile $archivePath
}
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $archiveHash) {
    throw 'Azahar archive hash differs from the pinned official release.'
}
New-Item -ItemType Directory $runtimeRoot | Out-Null
$profiles = @()
foreach ($profileName in 'original', 'rebuilt') {
    $profileRoot = Join-Path $runtimeRoot $profileName
    Expand-Archive -LiteralPath $archivePath -DestinationPath $profileRoot
    $executables = @(Get-ChildItem -LiteralPath $profileRoot -Recurse -File -Filter azahar.exe)
    if ($executables.Count -ne 1) { throw 'Expected one Azahar executable per profile.' }
    $exe = $executables[0]
    New-Item -ItemType Directory (Join-Path $exe.DirectoryName 'user') | Out-Null
    $profiles += [ordered]@{ name=$profileName; executable=$exe.FullName;
        executable_sha256=(Get-FileHash -LiteralPath $exe.FullName -Algorithm SHA256).Hash.ToLowerInvariant();
        user_directory=(Join-Path $exe.DirectoryName 'user') }
}
$receipt = [ordered]@{ version='2126.2'; archive_url=$downloadUrl; archive_sha256=$archiveHash;
    profiles=$profiles; launched=$false; settings='fresh default portable profiles; runtime observations pending' }
$encoding = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $runtimeRoot 'runtime.json'), ($receipt | ConvertTo-Json -Depth 5), $encoding)
Write-Output 'Pinned Azahar 2126.2 profiles prepared. Neither profile has been launched.'
