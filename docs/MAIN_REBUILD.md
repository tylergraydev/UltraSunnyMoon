# Unchanged main-executable reconstruction

The supplied Ultra Sun base `code.bin` now passes a twelve-object split/link
reconstruction with all **5,914,624 bytes** matching the original. The
linked ELF also preserves the initialized text, read-only, and data regions
at their exheader addresses. This completes the unchanged-main-image
baseline in [issue #17](https://github.com/tylergraydev/UltraSunnyMoon/issues/17).

There are zero compiled source replacements in this unchanged baseline.
The separate [constructor-helper build](FIRST_SOURCE.md) contains one;
the [BSS reconstruction](STARTUP_BSS.md) awaits integration. This baseline verifies build
machinery using preserved original bytes; it does not establish compiler
identity, rebuilt container installation, game execution, or source coverage.

## Target and regions

Inputs are pinned to these hashes, and the update is rejected:

| Input | SHA-256 |
| --- | --- |
| Base `code.bin` | `b5388f7500d91be01499a99ca007c98212068608ed7c83c43952e1d5148e9e09` |
| Base `exheader.bin` | `e4682ebab1bef10bdede38589b18c98f6976b1ebdc6a3b2540757aedcfe141e2` |

| Linked section | Address | Logical bytes | Retained file bytes | Padding bytes |
| --- | --- | ---: | ---: | ---: |
| `.text` | `0x00100000` | 4,954,608 | 4,956,160 | 1,552 |
| `.rodata` | `0x005ba000` | 706,888 | 708,608 | 1,720 |
| `.data` | `0x00667000` | 249,160 | 249,856 | 696 |

The three file-backed allocations are contiguous for this target. The
adapter rejects a different input or a layout requiring virtual gaps.
Existing page padding is retained byte for byte rather than regenerated.

The exheader separately records 197,052 BSS bytes. They are not present as
original file bytes and are not added to this rebuild's ELF mappings. In
particular, the logical data end and the allocated data-page end differ;
this baseline does not implement the game's BSS-zeroing or loader behavior.
The original exheader is copied locally, not recreated from source.

## Splitting and linking

The adapter uses the same [pinned pipeline revision](https://github.com/AlgebraManiacABC/3DS-Decomp-Pipeline/tree/621bbce909ad2f9c551563c7443ed80c0123fe77)
as the [CRO baseline](REBUILD.md). It calls the original splitter, ELF
object writer, linker invocation, and raw-image recreation functions.
The external checkout remains unchanged.

Eight `.text` objects separate three independently verified instruction
ranges, surrounding original regions, literals, and page padding:

- ARM startup helper at `0x00100024`, 28 bytes.
- Thumb array-construction helper at `0x00100050`, 34 bytes.
- ARM startup sample at `0x001045b4`, 76 bytes.

Two `.rodata` objects and two `.data` objects separate logical contents from
their original padding. Opaque text ranges use `$d` as a conservative
object-writer marker; this does not classify their contents as runtime data.
Names describe analysis ranges rather than recovered original source units.

A generated minimal linker script places the three sections at their
exheader addresses, sets load permissions to read/execute, read-only, and
read/write respectively, and asserts the original allocated sizes. Original
branch encodings, pointers, and literal words are retained. No relocations
are generated and no instruction words are rewritten. GNU `objcopy`
extracts the linked initialized image directly into the rebuilt `code.bin`;
no original-file overlay is applied after linking.

The tested toolchain remains Ubuntu ARM GNU binutils 2.38, with Python
3.10.12 and typing_extensions 4.12.2 under WSL. Tool paths, versions, and
executable hashes are saved locally. Generated EABI flags are pipeline
choices, not a fingerprint of the retail compiler.

## Independent proof

`verify_main_rebuild.py` reads exheader and ELF fields without importing
the external pipeline. It verifies:

- Original input identities and full reconstructed-file equality.
- Each selected object's section and bytes against its original range.
- Complete object coverage exactly once, with no missing or extra objects.
- Ordered object selection in the linker response file and linker map.
- All three linked section addresses, permissions, and payloads.
- All three `PT_LOAD` addresses, extents, permissions, alignment, and bytes.

The private verification report retains a hash and range receipt for each
selected object. Linker response files, maps, commands, logs, originals,
and generated binaries stay under `analysis/private`.

Seven negative probes reject a changed raw RO byte, changed Thumb object
payload, changed linked-section address, changed load address, overlapping
object coverage, a missing linker input, and use of the update executable.
The positive proof passes after restoration. Eight existing source-owned
regression tests and the prior CRO independent verifier also pass.

## Reproduce

Use the pinned checkout and WSL ARM binutils installation from [REBUILD.md](REBUILD.md).
From the project root in PowerShell:

```powershell
wsl -d Ubuntu -- python3 tools/rebuild_main.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/rebuild-main-my-run
.\.local\venv\Scripts\python.exe tools/verify_main_rebuild.py extracted/base/exefs/code.bin extracted/base/exheader.bin analysis/private/rebuild-main-my-run
```

The run directory must be new and inside `analysis/private`. The resulting
ELF is an initialized-image reconstruction artifact, not a host executable
or a complete 3DS loader model.

## Next work

The verified Thumb helper `__aeabi_vec_ctor_nocookie_nodtor` now has a
[compiled C implementation](FIRST_SOURCE.md) with bounded ARM behavior checks
and explicit nonmatching integration proof. The unchanged baseline remains
the default build. Exact compiler matching and complete-game runtime checks
remain open; compiler investigation continues in
[#15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15).
