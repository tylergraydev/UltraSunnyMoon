#!/usr/bin/env bash
# Run the pinned project-local REA installation inside Ubuntu WSL.
set -euo pipefail
tool_root="${ULTRASUN_TOOL_ROOT:-$HOME/.local/share/ultrasunnymoon}"
export JAVA_HOME="$tool_root/jdk"
export GHIDRA_INSTALL_DIR="$tool_root/ghidra_12.1.4_PUBLIC"
export PATH="$JAVA_HOME/bin:$PATH"
export REA_ANALYSIS_PROVIDER=ghidra
export REA_GHIDRA_STARTUP_TIMEOUT_MS=330000
exec node "$tool_root/rea-source/scripts/rea.mjs" "$@"
