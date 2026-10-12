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
- The startup BSS clearer now has a second C reconstruction. Both GCC profiles
  produce a nonmatching 36-byte payload; four original/candidate ARM11 cases
  pass. It is not yet selected in the main builder. See [its evidence](STARTUP_BSS.md).
  The tooling suite now passes 23 tests.

## Immediate work and stop condition

Extend [runtime validation #19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19)
with the same reproducible input sequence in both builds. First establish a
checkpoint beyond language selection; first controllable gameplay is still the
acceptance target. Azahar supports CLI input-movie playback, but a valid movie
must match the game's actual peripheral polling order. A generated sequence is
an experiment until logs establish that playback stayed synchronized.

The first private synthetic pad/touch movie trial exited before RPC became
available and produced an empty runtime log. Its cause is unresolved; it supplies
no runtime-validation evidence. Resume from the verified ordinary startup before
investigating movie playback further.

Keep emulator integration bounded to this comparison. If input playback needs
substantial new infrastructure, document the remaining gap in #19 and continue
independent reconstruction work. Keep #19 open until its acceptance conditions
are met.

## Next decompilation priorities

1. Extend verified compiled-object selection to the startup BSS clearer and
   its literal pool, preserving the rest of the image.
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
