# First compiled source replacement

Ultra Sun's Thumb runtime helper `__aeabi_vec_ctor_nocookie_nodtor` now has a
readable C implementation that is compiled, behavior-tested, and selected
in a rebuilt main image. Its status is **behavior-tested, nonmatching**.
It is not an exact decompilation match or a full-game runtime result.

## Identity and behavior

The pinned base exports the helper at encoded address `0x00100051`, with
canonical Thumb address `0x00100050`. The original function comprises
17 independently verified instructions and 34 bytes. Retained REA Evidence
ID: `ev_8f1625f9e6d6d0fcab0f026570bfeb3d90a59ade7866950cf12df877313a39c6`.
Its subject digest is bound to the verified full analysis image.

The [Arm C++ ABI](https://github.com/ARM-software/abi-aa/blob/main/cppabi32/cppabi32.rst)
defines the helper signature. Combining that identity with observed
instructions establishes the following behavior for normally returning
callbacks:

- Arguments are the array pointer, constructor callback, element byte size,
  and unsigned element count in `r0` through `r3`.
- A null constructor skips the loop. Zero elements also invoke no callback.
- Each callback receives the current element pointer. Its return value is
  ignored, and the element pointer advances by the supplied size.
- The helper returns the original array pointer and restores callee-saved
  registers and its stack.
- The helper's direct writes are to its own stack; array changes come from
  the callback. The indirect callback target remains caller-dependent.

`src/runtime/aeabi_vec_ctor.c` expresses that behavior independently. The
array parameter is volatile to keep the original pointer addressable across
callbacks, consistent with its observed stack storage. This is a code-generation
choice for our reconstruction, not a claim about the original source.

## Compilation and matching

The tested compiler is Ubuntu package `gcc-arm-none-eabi`
`15:10.3-2021.07-4`, reporting GCC 10.3.1 (20210621). Compiler-driver and
`cc1` hashes, source hash, commands, object hashes, and comparisons are
retained in the ignored run report. Architecture options are `-mcpu=mpcore`,
`-mthumb`, and `-mfloat-abi=soft`; compilation is freestanding with builtins,
unwind-table generation, stack protection, and frame-pointer use disabled.

Six profiles were tested for the selected source:

| Profile | Text bytes | Exact match |
| --- | ---: | --- |
| `-Os` | 34 | No |
| `-O1` | 38 | No |
| `-O2` | 40 | No |
| `-O3` | 40 | No |
| `-Os -fno-reorder-blocks` | 34 | No |
| `-O2 -fno-schedule-insns -fno-schedule-insns2` | 40 | No |

An earlier ordinary-pointer implementation produced a 36-byte minimum;
bounded source-shape experiments did not produce an exact match. These
results neither identify the retail compiler nor rule out GCC generally.
The selected `-Os` object has no relocations, undefined symbols, or additional
allocated payload. Its Thumb entry symbol and function extent are checked.

## Isolated ARM execution

[Unicorn](https://www.unicorn-engine.org/docs/tutorial.html) 2.1.4 executes
the original and compiled machine code with its ARM11 MPCore CPU model.
Eight cases cover zero, one, and multiple elements; zero stride; null
constructor; a null array with no calls; and ARM/Thumb callback interworking.

The callback modifies element memory, returns a different pointer, and
clobbers caller-saved registers and condition flags. Tests compare callback
addresses/order/count, return value, array mutations, surrounding canaries,
stack alignment, callee-saved registers, and stack restoration. The helper
extracted from the rebuilt image passes the same eight cases.

Five source-owned harness probes reject missing callbacks, wrong return
values, corrupted callee-saved state, and unexpected memory writes while
accepting a valid no-call return. All thirteen repository tests pass.

These are bounded execution checks. Exception propagation, every possible
input, full-game calling contexts, and 3DS service/runtime behavior remain
unverified. No exception/unwind compatibility is claimed.

## Integration proof

The unchanged rebuild remains the default. A replacement requires a compiled
object plus compilation and behavior receipts bound to the current source
and base image. Nonmatching integration additionally requires the explicit
`--allow-nonmatching` flag. A replacement with a different size is rejected.
There is no silent fallback if a selected object fails a gate.

For the tested build, the linker response file and map select
`build/aeabi_vec_ctor.o`, replacing the original split object at the same
address. The compiled object hash is
`0bb88574f7ce71ce7ff38ecee3c39e49320587cea01e1e77cb345336cdf67416`.
Independent verification checks the selected compiled object, all three
linked sections and load mappings, and the complete reconstructed image.

Exactly 27 bytes differ, all inside the original 34-byte function slot.
All 5,914,590 bytes outside that slot remain original. The resulting image
SHA-256 is `c557617562525a2959a8fc3763b1398825b861ed69960646022dd34dd7ce2736`.
The remaining game code/data and modules are preserved original content;
this result does not establish broader source reconstruction coverage.

Negative probes reject original-object fallback in the response file or
map, compiled-object substitution, reinsertion of original function bytes,
an unrelated image change, and use of this candidate under the default
exact-match policy. The unchanged main and CRO verifiers remain valid.

## Reproduce

With the existing pinned pipeline checkout and ARM binutils installation:

```powershell
wsl -d Ubuntu -u root -- apt-get install -y --no-install-recommends gcc-arm-none-eabi
.\.local\venv\Scripts\python.exe -m pip install -r tools/requirements-analysis.txt
wsl -d Ubuntu -- python3 tools/compile_helper.py extracted/base/exefs/code.bin analysis/private/helper-my-run
.\.local\venv\Scripts\python.exe tools/verify_helper_behavior.py extracted/base/exefs/code.bin analysis/private/helper-my-run/Os.o --report analysis/private/helper-my-run/behavior.json
wsl -d Ubuntu -- python3 tools/rebuild_main.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/helper-image-my-run --helper-object analysis/private/helper-my-run/Os.o --allow-nonmatching
.\.local\venv\Scripts\python.exe tools/verify_main_rebuild.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/helper-image-my-run
.\.local\venv\Scripts\python.exe tools/verify_helper_behavior.py extracted/base/exefs/code.bin analysis/private/helper-my-run/Os.o --image analysis/private/helper-image-my-run/out/code.bin
```

Compilation and build run directories must be new and private. Omitting
`--allow-nonmatching` rejects this object. Omitting the replacement option
retains the unchanged baseline.

## Runtime gate and next work

The source compilation and initialized-image replacement milestone is
tracked in [#18](https://github.com/tylergraydev/UltraSunnyMoon/issues/18).
The rebuilt raw `code.bin` is now [packaged and independently verified](RUNTIME.md)
in a decrypted emulator CXI. It has not been executed in the game.
A pinned original-game runtime baseline and observed original/rebuilt
comparison remain required before claiming a working rebuilt game.
Phase four remains open for that gate. Exact matching and retail toolchain identification remain in
[#15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15).
