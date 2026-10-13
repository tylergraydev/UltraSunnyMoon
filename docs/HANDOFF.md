# Session handoff

Updated 2026-10-12 after paired input-movie progression to the introduction (#19).
Read [AGENTS.md](../AGENTS.md), [STATUS](STATUS.md), and [PROJECT](PROJECT.md).
This file records local resume details; it is not a claim of full decompilation.

## Next task: extend the replay through player setup toward gameplay

The main builder now selects the BSS clearer with `--bss-object`, alone or
alongside `--helper-object`. Nonmatching remains explicitly selected with
`--allow-nonmatching`. Unchanged, constructor-only, BSS-only, and combined
policies pass independent image verification. The BSS payload extracted from
both selected builds passes four cases; the constructor extracted from its
two selected builds passes eight. Fifteen negative probes and 27 unit tests pass.

The combined build is now packaged in `analysis/private/runtime-both-packages-1`.
Independent verification passes with 109 changed container bytes (45 replacement
bytes and 64 required hash bytes). Both original and combined games reach
language selection with English highlighted. RPC reads verify both routines
and the unchanged startup literals. Eight recorded runtime settings agree;
four runtime-evidence negative probes and 31 source-owned tests pass.

Both variants now replay the same movie in fresh profiles and reach the same
Professor Kukui/Rockruff Pokémon Trainers dialogue. Movie/log/RPC receipts pass;
eight settings match and no input-type desynchronization is logged through
capture. Current suite: 40 tests passing. Both test processes were stopped.

Next extend the sequence through avatar/name selection toward first controllable
gameplay. Read [RUNTIME](RUNTIME.md) and `tools/startup_movie.py` first. Use fresh
profiles, the same movie in both variants, and supported short option `-p`.
The long option appears to collide with the compression dispatcher. Capture
while replay is still active: completion pauses emulation and opens a dialog,
after which RPC may stop responding. The selected movie has a 180-second horizon,
A pulses only from 15 to 75 seconds, and neutral inputs thereafter; capture
around 95 seconds. No complete-movie or exact-timing claim is made. Keep #19 open.

Start with:

- `src/runtime/clear_bss.c`
- `tools/compile_bss.py` and `tools/verify_bss_behavior.py`
- `tools/rebuild_main.py` and `tools/verify_main_rebuild.py`
- [STARTUP_BSS](STARTUP_BSS.md) and [FIRST_SOURCE](FIRST_SOURCE.md)

Completed acceptance for integration:

1. Bind selection to the actual compiled object, source, compilation receipt,
   and behavior receipt. Keep nonmatching selection explicit.
2. Cover `0x00100024..0x00100047`: the original 28-byte ARM body and its two
   four-byte address literals. The compiled payload is 36 bytes.
3. Preserve startup literals at `0x00100048` and `0x0010004c`. The default
   splitter retains all 16 literal bytes in `original_startup_literals`; BSS
   selection moves the first eight bytes into the compiled object.
4. Prove selection in linker inputs/map and independently verify sections,
   load mappings, replacement bytes, and every byte outside selected ranges.
   No post-link original-byte fallback.
5. Execute the integrated BSS routine through its existing harness. Cover
   unchanged, constructor-only, BSS-only, and both-function build policies.
6. Reject tampered/missing receipts, wrong objects, unexpected changes,
   overlapping ranges, and silent original-object substitution. Recheck the
   unchanged baseline and first-helper behavior after builder changes.

[Integration #21](https://github.com/tylergraydev/UltraSunnyMoon/issues/21) is linked
under foundation epic #4. [#20](https://github.com/tylergraydev/UltraSunnyMoon/issues/20)
remains closed for reconstruction and isolated behavior only.

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
| `analysis/private/bss-integration-source-1/` | Fresh selected BSS compilation and current-harness receipts |
| `analysis/private/bss-integrated-2/` | Verified BSS-only image and integrated behavior receipt |
| `analysis/private/startup-both-integrated-1/` | Verified combined image, `bss-behavior.json`, `helper-behavior.json` |
| `analysis/private/bss-gate-baseline-1/` | Rechecked unchanged build |
| `analysis/private/bss-gate-constructor-1/` | Rechecked constructor-only build and integrated behavior |
| `analysis/private/bss-negative-probes-1/` | Disposable negative-probe copies and `probes.json` |
| `analysis/private/helper-source-final/` | First helper's selected `Os.o` and receipts |
| `analysis/private/helper-integrated-final/` | Verified constructor-only main build |
| `analysis/private/rebuild-main-final/` | Unchanged main build |
| `analysis/private/rebuild-module-final/` | Unchanged AnaiTest module build |
| `analysis/private/runtime-packages/` | Verified original and constructor-only rebuilt CXIs |
| `analysis/private/runtime-both-packages-1/` | Verified original and combined CXIs, package/verification receipts |
| `analysis/private/rpc-both-original-2/` | Settled original startup bytes and inspected RPC frame |
| `analysis/private/rpc-both-rebuilt-1/` | Combined startup bytes and inspected RPC frame |
| `analysis/private/runtime-both-original-2/` | Original log/config/package observation |
| `analysis/private/runtime-both-rebuilt-1/` | Combined log/config/package observation |
| `analysis/private/runtime-both-comparison-1/` | Paired comparison receipt and four disposable negative trials |
| `analysis/private/startup-replay-plan-2/` | Selected 180-second movie and generator/format receipt |
| `analysis/private/movie-runtime-2/` | Fresh original/rebuilt replay profiles; now stopped |
| `analysis/private/replay-original-checkpoint-4/` | Selected original RPC frame/bytes and byte-preserved movie/log receipt |
| `analysis/private/replay-rebuilt-checkpoint-4/` | Selected combined RPC frame/bytes and byte-preserved movie/log receipt |
| `analysis/private/replay-original-runtime-2/` | Original introduction log/config/package observation |
| `analysis/private/replay-rebuilt-runtime-2/` | Combined introduction log/config/package observation |
| `analysis/private/replay-comparison-3/` | Verified paired introduction checkpoint/settings receipt using public log writer |
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

Run from the repository root. Current suite: 40 tests passing.

```powershell
git status --short
.local/venv/Scripts/python.exe -m unittest discover -s tests -v
.local/venv/Scripts/python.exe tools/verify_function.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/full-base-final/1-analyze_function.json --mode arm
.local/venv/Scripts/python.exe tools/verify_bss_behavior.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-source-1/Os.o
.local/venv/Scripts/python.exe tools/verify_main_rebuild.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/helper-integrated-final
.local/venv/Scripts/python.exe tools/verify_main_rebuild.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/startup-both-integrated-1
.local/venv/Scripts/python.exe tools/compare_runtime_rpc.py analysis/private/rpc-both-original-2 analysis/private/rpc-both-rebuilt-1 extracted/base/exefs/code.bin analysis/private/startup-both-integrated-1/out/code.bin
.local/venv/Scripts/python.exe tools/verify_startup_replay.py analysis/private/replay-original-checkpoint-4 analysis/private/replay-rebuilt-checkpoint-4 extracted/base/exefs/code.bin analysis/private/startup-both-integrated-1/out/code.bin analysis/private/startup-replay-plan-2/startup.ctm
```

To produce a new BSS compilation receipt, use a new output directory:

```powershell
wsl -d Ubuntu -- python3 tools/compile_bss.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-next-run
```

To reproduce integration, follow [STARTUP_BSS](STARTUP_BSS.md). Use the fresh
`bss-integration-source-1` object/receipts for the current harness. Old standalone
receipts predate the harness change and are deliberately rejected by the new
BSS selection gate; retained proof has not been overwritten.

## Runtime boundary and open work

Constructor-only and combined rebuilt packages reach language selection.
The combined package contains both compiled replacements. Live replacement-byte
reads prove loading, not execution counts. Early original frame
`rpc-both-original-1` shows the opening animation; its prematurely recorded
menu description in `runtime-both-original-1` has a `CORRECTION.txt` note.
Use the selected `*-original-2` evidence for the actual menu checkpoint.
Gameplay beyond language selection remains open in
[#19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19).

Both test processes were stopped after collection. Check current process
identity/state rather than assuming it persists. Only one RPC-enabled
instance may run at a time. Native desktop control was unavailable; supported
CLI and RPC work. The earlier movie trial remains invalid; the short-option
replay now supplies a paired introduction checkpoint. The 90-second experiment
lost RPC response near completion and is not the selected proof. Checkpoint-2
receipts had a newline conversion mismatch; checkpoint-3 contains corrected
copies matching the original text hashes, with correction notes. Checkpoint-4
uses the public log writer against the retained profile logs, preserving actual
log bytes and validating the loaded movie ID. Retained earlier evidence was not
overwritten. The public `--movie` path has a CRLF regression test.

Other open tracks: [compiler matching #15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15)
and [module imports/loading #16](https://github.com/tylergraydev/UltraSunnyMoon/issues/16).
The project has two small C reconstructions and mostly retained original code.
No full-game reconstruction percentage or native-PC readiness is established.
