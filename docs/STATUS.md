# Working checkpoint

Updated 2026-10-12. The [roadmap](https://github.com/tylergraydev/UltraSunnyMoon/issues/1)
tracks the project phases; this note records where to resume focused work.

## Proven so far

- Ultra Sun base inputs and analysis tools are pinned. The update remains separate.
- An unchanged main executable and one CRO rebuild byte for byte.
- One C runtime helper has been reconstructed, compiled, behavior-tested, and
  integrated into the main executable. It fits its original space but is **not
  byte matching**. Reconstruction is limited to that helper; the rest is retained
  original code.
- Original and rebuilt CXIs pass packaging and preservation checks.
- Both games boot to language selection in isolated Azahar 2126.2 profiles.
  Live RPC reads verify the respective helper bytes; private game frames confirm
  the startup screen. This proves loading, not a count of helper executions.
- The startup BSS clearer is now explicitly selectable in the main builder,
  alone or alongside the constructor. Both GCC profiles produce a nonmatching
  36-byte payload. Integrated BSS passes four ARM11 cases; integrated constructor
  passes eight. All four build policies preserve every byte outside selected
  ranges; 15 negative probes reject invalid selection/proof. See
  [integration evidence](STARTUP_BSS.md) and [#21](https://github.com/tylergraydev/UltraSunnyMoon/issues/21).
  The tooling suite now passes 27 tests.
- The combined BSS/constructor CXI now passes independent packaging checks and
  reaches language selection alongside the original. RPC readbacks verify both
  compiled routines and the preserved startup literals. The current suite passes
  31 tests. This proves loading and startup, not execution counts or gameplay.
- A fixed input movie now advances original and combined builds to the same
  Kukui/Rockruff introduction dialogue in fresh profiles. Retained logs show no
  input-type desynchronization through capture; live bytes and eight settings
  match their expected inputs. The suite now passes 40 tests. This is progression
  beyond language selection, not first controllable gameplay.
- The bounded first gameplay gate is now complete: original and combined builds
  reproduce the same bedroom movement after the same avatar/name/wake-up movie.
  Thirty-one paired captures verify movie/log/frame/live-byte identities; root
  and an independent reviewer confirm rightward and forward avatar movement.
  Eight logged settings and the 400% speed limit match (CPU clock stays 100%).
  All 60 source-owned tests pass. #21 is closed; #19's bounded acceptance is met.

## Immediate work

Resume bounded source reconstruction with the following startup initializer's
retained evidence, while compiler matching and module loading continue on their
separate tracks. The [session handoff](HANDOFF.md) records the completed runtime
artifacts and the next source evidence selection.

## Completed bounded runtime gate and limits

[Runtime validation #19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19)
now has the same reproducible first controllable gameplay path in both builds.
See [RUNTIME](RUNTIME.md) for exact plan hashes, settings, captures, reproduction,
and independent review. Both profiles start with empty saves and use the same
input movie. Both logs remain synchronized through the observed movement path.

The earlier empty-log movie trial supplies no replay evidence. The supported
short option `-p` now loads successfully; source inspection suggests the long
option collided with the compression dispatcher. The selected longer replay
has matching movie/log/RPC receipts for both variants. It is stopped after
checkpoint capture; full-movie completion and exact timing remain unproven.

This is a bounded startup/setup/bedroom comparison, not complete game
compatibility. Routine execution counts, exceptions, battles/overworld coverage,
full-movie completion, and exact timing determinism remain unverified. They are
outside #19's completed first-path acceptance; no later phase is automatically
closed by this result.

## Next decompilation priorities

1. Review the retained following-startup initializer evidence for the next
   bounded C reconstruction; preserve the completed runtime proof.
2. Continue [compiler matching #15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15).
   A behavior-compatible GCC build does not identify the retail compiler.
3. Continue [module loading #16](https://github.com/tylergraydev/UltraSunnyMoon/issues/16).
   Static named-import resolution is complete for all 132 base CROs: 19,525 names
   resolve against `static.crs` with independent parser agreement (see
   [MODULES](MODULES.md)). Indexed/anonymous imports, runtime BSS/registration,
   load order, and loaded-byte comparison remain open.

Native PC execution remains a later porting phase. The current rebuilt game
still requires a 3DS environment.

## Resume references

- [Runtime packages, RPC setup, and checkpoint evidence](RUNTIME.md)
- [First reconstructed source and its proof limits](FIRST_SOURCE.md)
- [Main executable build and verification](MAIN_REBUILD.md)
- [REA workflow](DECOMP_WORKFLOW.md)

Retail inputs, raw analysis, runtime profiles, and game frames stay in ignored
local directories. Public commits contain source, tools, and proof summaries.
