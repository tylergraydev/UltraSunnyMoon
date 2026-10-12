#!/usr/bin/env bash
set -euo pipefail
# ARM11/ARMv6 with ARM/Thumb interworking. Analysis convention is not a
# determination of the original retail compiler or ABI.
export REA_GHIDRA_LANGUAGE_ID=ARM:LE:32:v6
export REA_GHIDRA_COMPILER_SPEC_ID=default
# Disable costly global parameter inference for this initial static pilot.
# REA commits this choice in its evidence analysis profile.
export REA_GHIDRA_DISABLED_ANALYZERS='Decompiler Parameter ID,Stack'
exec bash "$(dirname "$0")/rea.sh" "$@"
