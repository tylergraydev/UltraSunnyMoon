# REA analysis environment

This setup analyzes local Ultra Sun inputs. It does not compile or execute the game.

This document covers initial preparation and the historical bounded pilot.
The existing workspace is already prepared. Full-image analysis, reconstruction,
and startup runtime milestones are recorded in [STATUS.md](STATUS.md); use
[HANDOFF.md](HANDOFF.md) to resume without repeating setup.

## Toolchain

Use Ubuntu WSL on Windows, with Node.js 22.19+ in the 22.x series (or another REA-supported major), npm, Python 3, curl, git, GCC, and readelf. The initial host is Ubuntu 22.04.5 with Node 22.22.1. REA's general host diagnostic lists Ubuntu 24.04+ as supported; Ubuntu 22.04 is an explicitly tested local environment, not an upstream support claim.

Tools install under `$HOME/.local/share/ultrasunnymoon`, independently of system Java. `ULTRASUN_TOOL_ROOT` can select another location.

- REA source revision: `7ae3c50a9d49c480035855de9fcc4484befacd92` from [morluto/rea](https://github.com/morluto/rea/tree/7ae3c50a9d49c480035855de9fcc4484befacd92). Its package version remains 6.4.0; the source revision distinguishes it from the older npm 6.4.0 release.
- Ghidra: 12.1.4, official NSA archive.
- Java: Temurin JDK 21.0.12.1+1, official Adoptium archive.
- Extraction: CTRTool 1.3.0, official [Project_CTR release](https://github.com/3DSGuy/Project_CTR/releases/tag/ctrtool-v1.3.0).
- Independent decoder: Capstone 5.0.7.

The bootstrap verifies the downloaded Java and Ghidra archive hashes and restores executable permissions from Ghidra's ZIP metadata. It builds REA from the pinned source with its lockfile.

From PowerShell in this repository:

```powershell
wsl -d Ubuntu -- bash /mnt/c/code/UltraSunnyMoon/tools/bootstrap-wsl.sh
```

Substitute your WSL project path if it differs. Launch scripts use Bash explicitly, so executable permission on the Windows-mounted scripts is unnecessary.

## Extract local inputs

Place your game containers under `roms/`. Keep base and update separate. Download and extract `ctrtool.exe` into `.local/ctrtool/` from the official Windows x64 release. The archive used initially has SHA-256 `8031dff3be72d0adb250fae1f969f27627e12a89ebc6dd074a15a75f87ddc949`.

```powershell
.\tools\extract.ps1 -BaseImage 'roms\your-base.3ds' -UpdateImage 'roms\your-update.cia'
```

This extracts ExeFS, extended headers, and the plain region without dumping RomFS. CTRTool's full logs stay under `analysis/private/`: they can include sensitive cryptographic metadata and must not be published.

The supplied code is uncompressed. `wrap_code.py` rejects compressed input and incorrect page allocations rather than guessing. It emits an analysis-only ELF32 ARM container whose mapped initialized bytes equal the local original code. Segment addresses and page allocations come from the extended header. BSS memory is provisioned conservatively after the allocated data pages; exact runtime allocation is outside this pilot. EABI5 in the synthetic ELF is an analysis container choice, not identification of the retail ABI or compiler.

## Run the pilot

```powershell
wsl -d Ubuntu -- bash /mnt/c/code/UltraSunnyMoon/tools/pilot.sh
py -3 -m venv .local/venv
.\.local\venv\Scripts\python.exe -m pip install capstone==5.0.7
.\.local\venv\Scripts\python.exe tools/verify_analysis.py extracted/base/exefs/code.bin analysis/private/base-pilot-rea.json
```

The pilot first checks a source-owned fixture, then analyzes a bounded startup view at `0x00100024`. Only the initial `0x48` bytes of executable text are mapped, together with the original read-only and data mappings and a conservative BSS provision. The entire code payload is preserved in the private ELF file, but text beyond this window is deliberately not analyzed. Initial full-image imports reached costly global stack/switch recovery and were stopped. A later tuned profile successfully imports the full main image; see [FULL_ANALYSIS.md](FULL_ANALYSIS.md).

`rea-arm.sh` selects `ARM:LE:32:v6` and the default Ghidra compiler convention. ARM/Thumb interworking still requires review when expanding to other functions. It disables global `Stack` and `Decompiler Parameter ID` analysis for this focused pilot; the evidence records those choices. Type recovery and calling conventions remain hypotheses.

The independent check verifies instruction address coverage, opcodes, operands (including branch aliases and resolved PC-relative literal loads), the startup caller, and literal references. It reports the literal zeroing range. Preserve the full private REA evidence, including its limitations and analysis profile.

CLI queries are immediately usable. Each CLI invocation imports an ephemeral analysis database and closes it afterward. A reusable standalone REA MCP-session runner is now verified; see [FULL_ANALYSIS.md](FULL_ANALYSIS.md). Registering the server in the Codex app remains a separate convenience step.

## Check tooling and public-file boundaries

```powershell
.\.local\venv\Scripts\python.exe -m unittest discover -s tests -v
git check-ignore roms extracted/base/exefs/code.bin analysis/private/base-analysis.elf
git status --short
```

Commit only scripts, source-owned fixtures, sanitized findings, and documentation. Original containers, executable bytes, wrapped ELF images, and raw analysis reports remain ignored. This analysis proof does not establish a matching build, game boot, or source replacement.
