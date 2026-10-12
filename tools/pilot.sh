#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local analysis/private
gcc -O1 -fno-inline tests/fixtures/analysis_fixture.c -o .local/fixture.elf
bash tools/rea.sh function "$PWD/.local/fixture.elf" rotate_mix --format json > analysis/private/fixture-rea.json
python3 tools/wrap_code.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/base-pilot.elf --text-limit 0x48 > analysis/private/base-pilot-layout.json
readelf -l analysis/private/base-pilot.elf > analysis/private/base-pilot-readelf.txt
bash tools/rea-arm.sh function "$PWD/analysis/private/base-pilot.elf" 0x100024 --format json > analysis/private/base-pilot-rea.json
echo 'REA evidence saved under analysis/private/. Run tools/verify_analysis.py with Capstone and review operands before accepting the pilot.'
