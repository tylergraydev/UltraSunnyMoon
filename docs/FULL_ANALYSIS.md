# Full base-executable analysis

The full extracted base `code.bin` can be imported through REA/Ghidra without the pilot's text limit. This covers the main executable image, not every dynamically loaded game module.

## Configuration

Use the pinned toolchain in [SETUP.md](SETUP.md). `tools/rea-arm-full.sh` selects `ARM:LE:32:v6`, the default analysis compiler convention, and disables:

- `Stack`
- `Decompiler Parameter ID`
- `Decompiler Switch Analysis`

Earlier thread dumps located work in global stack and switch analysis. Deferring those analyzers allows whole-image imports while keeping function pseudocode available on demand. Switch tables, local-variable recovery, and parameter inference consequently have limited automatic coverage. Do not interpret unresolved indirect calls or undiscovered functions as absent game behavior.

The REA source revision is `7ae3c50a9d49c480035855de9fcc4484befacd92`, with Ghidra 12.1.4, Temurin JDK 21.0.12.1+1, Node 22.22.1, and Capstone 5.0.7. This is the tested Ubuntu 22.04 WSL host; upstream's general documented Ubuntu support starts at 24.04.

## Reproduce

From PowerShell:

```powershell
py -3 tools/wrap_code.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/base-analysis.elf
wsl -d Ubuntu -- node /mnt/c/code/UltraSunnyMoon/tools/query-native.mjs /mnt/c/code/UltraSunnyMoon/config/full-analysis.json
```

The runner prints its private output directory. Each run gets a timestamped name unless a unique name is supplied as the third argument. Existing run directories are never overwritten. Update the WSL project path if needed.

The plan opens one target, analyzes three samples, inventories procedures and segments, collects load-image observations, and explicitly closes the target. Calls reuse the same imported Ghidra program. The client request timeout is 600 seconds; the provider startup deadline is 330 seconds. A former 60-second SDK client timeout was too short and is corrected in the runner. Ghidra uses its 2 GiB Java heap limit; this is not a total process-RSS limit. Observed process RSS was about 1.2 GiB during the successful import, not a measured peak.

For the selected private run directory, verify:

```powershell
.\.local\venv\Scripts\python.exe tools/verify_analysis.py extracted/base/exefs/code.bin analysis/private/YOUR_RUN/1-analyze_function.json --elf analysis/private/base-analysis.elf
.\.local\venv\Scripts\python.exe tools/verify_function.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/YOUR_RUN/2-analyze_function.json --mode thumb
.\.local\venv\Scripts\python.exe tools/verify_function.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/YOUR_RUN/3-analyze_function.json --mode arm
.\.local\venv\Scripts\python.exe tools/verify_load_image.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/YOUR_RUN/6-inspect_native_load_image.json
```

Verification binds each Evidence target digest to the ELF and checks the entire original code payload. Independent Capstone decoding must cover every byte in each selected function body and match instruction addresses, opcodes, and operands. Canonicalization handles documented branch-condition aliases, `cpy`/`mov`, push/pop aliases, and PC-relative literal addresses. Choosing ARM for the Thumb sample is rejected.

REA's ELF inspection exposes measured mappings without an ELF-specific verified attestation. The independent load-image checker compared all three original file-backed mappings, addresses, offsets, extents, and mapped-byte hashes: all **5,914,624 original bytes** match. The conservative synthetic BSS extension is excluded from this original-byte coverage claim.

## Measured first successful session

| Operation | Duration |
| --- | ---: |
| Target selection | 2.54 seconds |
| First function, including complete-image import | 81.95 seconds |
| Thumb function in the same session | 0.49 seconds |
| Additional ARM function | 0.02 seconds |
| Entire selection/query/inventory/close session | 87.96 seconds |

The final reproducibility run returned the first function in 80.81 seconds and passed load-image comparison and all three function checks. Six source-owned structural/envelope regression tests pass; wrong ISA mode and a tampered operand are rejected.

The procedure inventory reports **17,464 Ghidra-detected procedures** and **12,318 defined strings** for this profile. These are analyzer observations, not recovered source functions, complete function coverage, or decompilation percentages.

| Sample | Mode | Body bytes | Verified instructions |
| --- | --- | ---: | ---: |
| Startup zeroing helper, `0x00100024` | ARM | 28 | 7 |
| Callback iteration helper, `0x00100050` | Thumb | 34 | 17 |
| Startup routine, `0x001045b4` | ARM | 76 | 19 |

The callback-helper name is inferred from its instructions. Ghidra reports 381 callers for that small Thumb function, making its dossier large despite a correct body boundary. Its indirect callback target remains unresolved.

Private sample Evidence IDs for this session:

- ARM zeroing: `ev_4a8f692bb164ad41343f64e0b0450a98f23fcead8f0e11f75c85e649e73d3c47`
- Thumb helper: `ev_8f1625f9e6d6d0fcab0f026570bfeb3d90a59ade7866950cf12df877313a39c6`
- ARM startup: `ev_7bba9fa2cfc32b9494d88f48c68f1723cc4d493600f755db86d6185c84a1335a`

These identify local records under ignored `analysis/private/`. Raw retail instructions, pseudocode dossiers, and ELF images are not published.

## Module and compiler leads

CTRTool's base RomFS inventory lists **132 CRO files** and **one `static.crs`**, with a `.crr/static.crr` registration file. They remain separate from this main-executable import. Their relocation, load-address, and cross-module symbol relationships require investigation.

The base plain region identifies Nintendo SDK `11_4_1_200_none`. This is metadata observed in the supplied game, not a recovered SDK or identification of the retail compiler. Compiler family/version/flags and a verified unchanged-binary rebuild remain open. No game execution or compiled source replacement is claimed.
