#!/usr/bin/env bash
set -euo pipefail
export REA_GHIDRA_LANGUAGE_ID=ARM:LE:32:v6
export REA_GHIDRA_COMPILER_SPEC_ID=default
# Full-image inventory: defer expensive global inference, retaining function
# analysis on demand. These omissions must accompany all coverage reports.
export REA_GHIDRA_DISABLED_ANALYZERS='Decompiler Parameter ID,Stack,Decompiler Switch Analysis'
exec bash "$(dirname "$0")/rea.sh" "$@"
