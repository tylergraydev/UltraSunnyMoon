#!/usr/bin/env bash
# Project-local prerequisites. Run inside Ubuntu WSL with a compatible Node/npm.
set -euo pipefail
tool_root="${ULTRASUN_TOOL_ROOT:-$HOME/.local/share/ultrasunnymoon}"
mkdir -p "$tool_root"
command -v node >/dev/null
command -v npm >/dev/null
command -v curl >/dev/null
command -v python3 >/dev/null
rea_revision=7ae3c50a9d49c480035855de9fcc4484befacd92
if [[ ! -d "$tool_root/rea-source" ]]; then
    git clone https://github.com/morluto/rea.git "$tool_root/rea-source"
    git -C "$tool_root/rea-source" checkout --detach "$rea_revision"
fi
if [[ "$(git -C "$tool_root/rea-source" rev-parse HEAD)" != "$rea_revision" ]]; then
    echo 'Existing REA source has a different revision; inspect it before rebuilding.' >&2
    exit 1
fi
if [[ ! -f "$tool_root/rea-source/dist/cli-runtime/cli.js" || ! -f "$tool_root/rea-source/dist/mcp/main.js" ]]; then
    (cd "$tool_root/rea-source"; npm ci; npm run build)
fi
if [[ ! -x "$tool_root/jdk/bin/java" ]]; then
    curl -fL 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_x64_linux_hotspot_21.0.12.1_1.tar.gz' -o "$tool_root/jdk.tar.gz"
    printf '%s  %s\n' 'ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94' "$tool_root/jdk.tar.gz" | sha256sum -c -
    mkdir -p "$tool_root/jdk"
    tar -xzf "$tool_root/jdk.tar.gz" -C "$tool_root/jdk" --strip-components=1
fi
if [[ ! -f "$tool_root/ghidra_12.1.4_PUBLIC/Ghidra/application.properties" ]]; then
    curl -fL 'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip' -o "$tool_root/ghidra.zip"
    printf '%s  %s\n' 'ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db' "$tool_root/ghidra.zip" | sha256sum -c -
    python3 -m zipfile -e "$tool_root/ghidra.zip" "$tool_root"
fi
# Python's zipfile extractor does not restore executable mode bits.
python3 - "$tool_root" <<'PY'
from pathlib import Path
import sys
import zipfile
root = Path(sys.argv[1]).resolve()
with zipfile.ZipFile(root / 'ghidra.zip') as archive:
    for item in archive.infolist():
        mode = item.external_attr >> 16
        if not item.is_dir() and mode & 0o111:
            target = (root / item.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Archive path leaves tool directory')
            target.chmod(mode & 0o777)
PY
bash "$(dirname "$0")/rea.sh" doctor --provider ghidra --format json --filter-output healthy,scope_checks
