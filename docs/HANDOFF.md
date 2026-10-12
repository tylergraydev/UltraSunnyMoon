# Session handoff

Updated 2026-10-12 after the startup BSS reconstruction in commit `32ccb76`.
Read [AGENTS.md](../AGENTS.md), [STATUS](STATUS.md), and [PROJECT](PROJECT.md).
This file records local resume details; it is not a claim of full decompilation.

## Next task: integrate the BSS clearer

The user chose to return to function reconstruction after bounded emulator
automation. The second C function is compiled and behavior-tested. Next extend
the verified main build to select it, while retaining support for the first
helper and the unchanged baseline.

Start with:

- `src/runtime/clear_bss.c`
- `tools/compile_bss.py` and `tools/verify_bss_behavior.py`
- `tools/rebuild_main.py` and `tools/verify_main_rebuild.py`
- [STARTUP_BSS](STARTUP_BSS.md) and [FIRST_SOURCE](FIRST_SOURCE.md)

Acceptance for integration:

1. Bind selection to the actual compiled object, source, compilation receipt,
   and behavior receipt. Keep nonmatching selection explicit.
2. Cover `0x00100024..0x00100047`: the original 28-byte ARM body and its two
   four-byte address literals. The compiled payload is 36 bytes.
3. Preserve startup literals at `0x00100048` and `0x0010004c`. The current
   splitter places all 16 literal bytes in `original_startup_literals`; it must
   account for the first eight bytes moving into the compiled object.
4. Prove selection in linker inputs/map and independently verify sections,
   load mappings, replacement bytes, and every byte outside selected ranges.
   No post-link original-byte fallback.
5. Execute the integrated BSS routine through its existing harness. Cover
   unchanged, constructor-only, BSS-only, and both-function build policies.
6. Reject tampered/missing receipts, wrong objects, unexpected changes,
   overlapping ranges, and silent original-object substitution. Recheck the
   unchanged baseline and first-helper behavior after builder changes.

Create/link an integration issue under the relevant foundation epic before
publishing the result. [#20](https://github.com/tylergraydev/UltraSunnyMoon/issues/20)
is closed for reconstruction and isolated behavior only. Do not reopen it merely
to expand its completed scope.

## Selected local evidence and artifacts

All paths below are relative to the repository root and ignored by Git:

| Path | Role |
| --- | --- |
| `extracted/base/exefs/code.bin` | Pinned original main executable |
| `extracted/base/exheader.bin` | Pinned original extended header |
| `analysis/private/base-analysis.elf` | Complete initialized-image REA view |
| `analysis/private/full-base-final/1-analyze_function.json` | BSS clearer dossier |
| `analysis/private/full-base-final/2-analyze_function.json` | Constructor-helper dossier |
| `analysis/private/full-base-final/3-analyze_function.json` | Following startup routine dossier |
| `analysis/private/bss-source-1/` | BSS `Os.o`, `O2.o`, compilation and behavior receipts |
| `analysis/private/helper-source-final/` | First helper's selected `Os.o` and receipts |
| `analysis/private/helper-integrated-final/` | Verified constructor-only main build |
| `analysis/private/rebuild-main-final/` | Unchanged main build |
| `analysis/private/rebuild-module-final/` | Unchanged AnaiTest module build |
| `analysis/private/runtime-packages/` | Verified original and constructor-only rebuilt CXIs |
| `analysis/private/rpc-original-verified/` | Original startup live bytes and game frame |
| `analysis/private/rpc-rebuilt-verified/` | Rebuilt startup live bytes and game frame |
| `analysis/private/movie-trial/` | Failed synthetic movie trial and restored startup proof |
| `.local/pipeline-reference/` | Pinned, unmodified 3DS Decomp Pipeline checkout |
| `.local/rea-reference/` | REA reference source/skill files |

REA evidence envelopes can contain a very large dossier twice, as text and
structured content. Use `verify_analysis.read_json` and select needed fields;
do not dump entire files into context. Prefer these retained dossiers over
reimporting the executable.

## Environment and pinned dependencies

- Host: Windows PowerShell, `C:\code\UltraSunnyMoon`.
- WSL: Ubuntu 22.04; project `/mnt/c/code/UltraSunnyMoon`.
- Windows Python: `.local/venv/Scripts/python.exe`, Python 3.12;
  packages pinned in `tools/requirements-analysis.txt`.
- ARM GCC: Ubuntu package `15:10.3-2021.07-4`, reports 10.3.1 (20210621).
  ARM binutils: 2.38. These do not identify the retail compiler.
- REA revision: `7ae3c50a9d49c480035855de9fcc4484befacd92`;
  Ghidra 12.1.4; Temurin 21. Tools installed in the WSL user's
  `$HOME/.local/share/ultrasunnymoon`.
- Pipeline revision: `621bbce909ad2f9c551563c7443ed80c0123fe77`.
- Azahar: isolated 2126.2 profiles under
  `analysis/private/azahar-runtime/{original,rebuilt}/azahar-windows-msys2-2126.2/`.

Do not bootstrap again unless a concrete dependency is missing or broken.

## Quick checks

Run from the repository root. Current suite: 23 tests passing.

```powershell
git status --short
.local/venv/Scripts/python.exe -m unittest discover -s tests -v
.local/venv/Scripts/python.exe tools/verify_function.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/full-base-final/1-analyze_function.json --mode arm
.local/venv/Scripts/python.exe tools/verify_bss_behavior.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-source-1/Os.o
.local/venv/Scripts/python.exe tools/verify_main_rebuild.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/helper-integrated-final
```

To produce a new BSS compilation receipt, use a new output directory:

```powershell
wsl -d Ubuntu -- python3 tools/compile_bss.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-next-run
```

These commands verify existing work or compile the standalone function. There
is no BSS integration option yet; implement and document it next.

## Runtime boundary and open work

Both existing runtime packages reach language selection. The rebuilt package
contains the compiled constructor helper; it still retains the original BSS
clearer. Live replacement-byte reads prove loading, not execution counts.
Gameplay beyond language selection remains open in
[#19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19).

An ordinary rebuilt Azahar test instance was running at handoff. Check current
process identity/state rather than assuming it persists. Only one RPC-enabled
instance may run at a time. Native desktop control was unavailable; supported
CLI and RPC work. The synthetic movie trial exited before RPC became available
with an empty log; its cause remains unknown. Do not resume that detour as the
default next task.

Other open tracks: [compiler matching #15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15)
and [module imports/loading #16](https://github.com/tylergraydev/UltraSunnyMoon/issues/16).
The project has two small C reconstructions and mostly retained original code.
No full-game reconstruction percentage or native-PC readiness is established.
