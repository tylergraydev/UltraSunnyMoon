# Startup BSS clearing reconstruction

`src/runtime/clear_bss.c` reconstructs the Ultra Sun base routine at
`0x00100024`. Status: **compiled and behavior-tested, nonmatching; not yet
integrated into a game image**. `ultrasun_clear_bss` is an inferred descriptive
name, not a recovered export name.

## Evidence and interface

The existing REA dossier records seven ARM instructions in a 28-byte body.
Evidence ID:
`ev_4a8f692bb164ad41343f64e0b0450a98f23fcead8f0e11f75c85e649e73d3c47`.
Independent Capstone verification binds the dossier to the pinned full analysis
ELF and checks every instruction address, opcode, and operand. The two address
literals are outside that body, at `0x00100040` and `0x00100044`; body plus
literals occupies 36 bytes.

Both literals agree with the pinned exheader:

| Bound | Address | Meaning |
| --- | --- | --- |
| Start, inclusive | `0x006a3d48` | Logical end of initialized `.data` |
| End, exclusive | `0x006d3f04` | Logical data end plus BSS size `0x301bc` |

This clears 197,052 bytes, or 49,263 aligned 32-bit words. The start is the
**logical** data end, not the page-rounded allocation end. The routine takes
no observed arguments and writes zero to each word in increasing address
order. The C implementation uses volatile word stores to preserve those writes.
Its fixed addresses deliberately describe this specific base revision.

The entry point calls the routine first, then calls `0x001045b4`. That next
routine overwrites `r0` and `r1` before using them. A `void(void)` interface is
therefore inferred for this startup use. Original and compiled caller-saved
register values and final flags need not be identical; the reconstruction
does not promise their preservation. The original loop checks its upper bound
before storing, whereas GCC's candidate begins with a store. The fixed,
aligned, nonempty interval makes their write sequences equivalent here.

## Compilation and execution checks

The pinned GCC 10.3.1 ARM toolchain compiles in ARM mode for ARM11 MPCore,
with soft-float, freestanding compilation, and builtin substitution, unwind
generation, and stack protection disabled. `-Os` and `-O2` produce the same
36-byte text payload, including literals. Neither matches original bytes.
The object gate checks the ARM entry symbol and extent and rejects undefined
symbols, relocations, and other allocated payloads.

The selected `-Os` object SHA-256 is
`15a497dfcf7e9c14630fd9cd470f25e4513129d272ee039d7ba042a25ad0c37f`.
Its text SHA-256 is
`5153697300f3f226913dc04d4126eb65e3f0543599fd96ba0e89a42b42eeef58`.

Unicorn 2.1.4 with the ARM11 MPCore CPU model executes original and candidate
code in four cases: BSS filled with `0xa5`, `0xff`, already zero, and a varying
byte pattern. The varying-pattern case also checks return to Thumb mode.
Each run validates every store's address, order, size, and zero value, the
complete final memory region, canaries before and after BSS, unchanged stack,
callee-saved registers, and bounded return. The code page is read-only during
execution. All four original/candidate comparisons pass.

Five source-owned negative harness probes reject a no-op even on already-zero
memory, callee-saved register corruption, a nonzero store, a byte store, and
a write at the exclusive end. The repository suite passes 23 tests.

## Reproduce

Run from the repository root with the existing WSL toolchain and local Python
environment. Choose a new private output directory:

```powershell
wsl -d Ubuntu -- python3 tools/compile_bss.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-my-run
.local/venv/Scripts/python.exe tools/verify_function.py extracted/base/exefs/code.bin analysis/private/base-analysis.elf analysis/private/full-base-final/1-analyze_function.json --mode arm
.local/venv/Scripts/python.exe tools/verify_bss_behavior.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/bss-my-run/Os.o --report analysis/private/bss-my-run/behavior.json
.local/venv/Scripts/python.exe -m unittest discover -s tests -v
```

The REA command reuses previously retained private evidence; a fresh checkout
must produce that dossier through the [full-image analysis workflow](FULL_ANALYSIS.md).
Compilation receipts retain source, object, target, and compiler identities.
Raw instructions and generated objects remain private.

## Next gate

The main builder still selects the original startup clearer. Before replacing
it, extend the existing compiled-object selection and independent preservation
checks to cover both its body and literal pool. The remaining startup literals
at `0x00100048` and `0x0010004c` must remain intact. Current runtime packages
still contain only the earlier constructor-helper replacement. No startup
execution, gameplay result, or additional reconstruction coverage in those
packages is claimed for this new function.
