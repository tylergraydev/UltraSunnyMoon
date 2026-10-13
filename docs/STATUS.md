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

## Immediate work

Extend the verified movie sequence through avatar/name setup toward first
controllable gameplay. Use fresh profiles and capture while playback is active;
the completion dialog pauses emulation and can block RPC. The
[session handoff](HANDOFF.md) records exact artifacts and commands.

## Separate open runtime gate

Extend [runtime validation #19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19)
with the same reproducible input sequence in both builds. First establish a
checkpoint beyond the introduction; first controllable gameplay is still the
acceptance target. Azahar supports CLI input-movie playback, but a valid movie
must match the game's actual peripheral polling order. A generated sequence is
an experiment until logs establish that playback stayed synchronized.

The earlier empty-log movie trial supplies no replay evidence. The supported
short option `-p` now loads successfully; source inspection suggests the long
option collided with the compression dispatcher. The selected longer replay
has matching movie/log/RPC receipts for both variants. It is stopped after
checkpoint capture; full-movie completion and exact timing remain unproven.

Keep emulator integration bounded to this comparison. If input playback needs
substantial new infrastructure, document the remaining gap in #19 and continue
independent reconstruction work. Keep #19 open until its acceptance conditions
are met.

## Next decompilation priorities

1. Extend the combined/original runtime comparison beyond language selection;
   keep gameplay validation #19 open until its acceptance is met.
2. Continue [compiler matching #15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15).
   A behavior-compatible GCC build does not identify the retail compiler.
3. Continue [module loading #16](https://github.com/tylergraydev/UltraSunnyMoon/issues/16).
   LangSelect appears in the startup loader log; loaded module bytes and resolved
   imports still need verification.

Native PC execution remains a later porting phase. The current rebuilt game
still requires a 3DS environment.

## Resume references

- [Runtime packages, RPC setup, and checkpoint evidence](RUNTIME.md)
- [First reconstructed source and its proof limits](FIRST_SOURCE.md)
- [Main executable build and verification](MAIN_REBUILD.md)
- [REA workflow](DECOMP_WORKFLOW.md)

Retail inputs, raw analysis, runtime profiles, and game frames stay in ignored
local directories. Public commits contain source, tools, and proof summaries.
