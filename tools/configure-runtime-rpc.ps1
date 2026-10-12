# Enable Azahar's own scripting interface only in the isolated test profiles.
param([string]$RuntimeDirectory = 'analysis/private/azahar-runtime')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path "$PSScriptRoot/..").Path
$privateRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'analysis/private')) + [IO.Path]::DirectorySeparatorChar
$runtimeRoot = (Resolve-Path (Join-Path $projectRoot $RuntimeDirectory)).Path
if (-not $runtimeRoot.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Use an isolated private runtime directory.'
}
$runtime = Get-Content -Raw -LiteralPath (Join-Path $runtimeRoot 'runtime.json') | ConvertFrom-Json
$running = @(Get-Process azahar -ErrorAction SilentlyContinue)
$targets = @()
foreach ($profile in $runtime.profiles) {
    $exe = [IO.Path]::GetFullPath($profile.executable)
    if (-not $exe.StartsWith($runtimeRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Runtime executable leaves the intended directory.'
    }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $profile.executable_sha256) {
        throw 'Runtime executable differs from its preparation receipt.'
    }
    if (@($running | Where-Object { $_.Path -ieq $exe }).Count) {
        throw "Close the $($profile.name) prepared Azahar before updating its RPC setting."
    }
    $targets += Join-Path (Split-Path $exe) 'user/config/qt-config.ini'
}
$encoding = New-Object System.Text.UTF8Encoding($false)
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fffffff'
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) {
        Copy-Item -LiteralPath $target -Destination ($target + '.before-rpc-' + $stamp)
        $text = [IO.File]::ReadAllText($target)
        if ($text -notmatch '(?m)^enable_rpc_server=') {
            throw 'Existing profile has no RPC key; inspect its configuration before editing.'
        }
        $text = [regex]::Replace($text, '(?m)^enable_rpc_server\\\\default=[^\r\n]*', 'enable_rpc_server\\default=false')
        $text = [regex]::Replace($text, '(?m)^enable_rpc_server=[^\r\n]*', 'enable_rpc_server=true')
    } else {
        New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
        $text = "[Debugging]`r`nenable_rpc_server\\default=false`r`nenable_rpc_server=true`r`n"
    }
    [IO.File]::WriteAllText($target, $text, $encoding)
}
Write-Output 'RPC enabled in isolated profiles with backups. Neither runtime has been launched.'
