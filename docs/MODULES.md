# Code-module mapping: first verified sample

The base RomFS contains **132 CRO files and one `static.crs`**. A read-only module inventory records each size, format marker, and SHA-256 under ignored `analysis/private/`. Selective extraction reads only chosen code modules; unrelated RomFS assets are not dumped.

## Static CRS findings

`static.crs` is 389,120 bytes, SHA-256 `b14dc9bc0fdb46ed85d422350048b76d7197ff90e14aa11ae9dc71483c494c91`. It contains linker/export metadata for the main executable, rather than another embedded copy of its main code payload.

Its segment table references absolute main-image addresses matching the extended header:

| Segment | Address | Size |
| --- | --- | ---: |
| Text | `0x00100000` | 4,954,608 |
| Read-only | `0x005ba000` | 706,888 |
| Data including BSS extent | `0x00667000` | 446,212 |

There are **4,916 named exports**, 80 module-import records, and 671 import-relocation records. Names and full symbol maps remain in private artifacts for now. One named export is `__aeabi_vec_ctor_nocookie_nodtor`, encoded at `0x00100051`; clearing its Thumb bit gives the independently verified function at `0x00100050`. This replaces the earlier inferred callback-helper label with a game-supplied export name. It does not recover every original name or establish the compiler version.

The descriptor also contains zero-size/auxiliary segments. Their runtime role is not inferred here. A CRS must not be treated as a dynamically rebased CRO with file-relative code offsets.

## Selected CRO

`AnaiTest.cro` is an 8,192-byte, import-free CRO0 module, SHA-256 `b996787f2bf5ab6182cbd0470ea1801d5bf0ee7e15e96b49c5b53a785dc66034`. Its name does not establish whether the retail game ever loads it.

- File-backed text segment: offset `0x180`, 172 bytes.
- File-backed data segment: offset `0x10ec`, 4 bytes.
- Named exports: one (`nnroControlObject_`, at text-segment offset zero).
- Internal relocation records: ten; cross-module imports: none.

The analysis view uses a **synthetic** module base of `0x00100000`. Internal relocation targets are decoded from segment tags; absolute forms use symbol-segment base plus addend, and relative forms additionally subtract the target address. Only the supported local relocation forms are accepted. Imports and unsupported relocation types are rejected.

The format-reader reference is [3DS Decomp Pipeline](https://github.com/AlgebraManiacABC/3DS-Decomp-Pipeline/tree/621bbce909ad2f9c551563c7443ed80c0123fe77), pinned to that commit. Relocation-field interpretation and address formulas were checked against [Azahar's CRO loader](https://github.com/azahar-emu/azahar/blob/master/src/core/hle/service/ldr_ro/cro_helper.cpp) and [record definitions](https://github.com/azahar-emu/azahar/blob/master/src/core/hle/service/ldr_ro/cro_helper.h). These references do not establish this synthetic view's actual runtime address or loading lifecycle.

## Verification

An independent raw-record reader recomputes the ten relocation words and compares the entire relocated payload; all other bytes remain unchanged. Source and view hashes are bound to retained evidence.

REA/Ghidra recovered the function at synthetic address `0x00100180`, using the module profile with switch analysis enabled. Its body contains 29 ARM instructions and 116 instruction bytes across two ranges. The intervening 20-byte jump table is correctly excluded from instruction decoding. Capstone independently matches every instruction address, opcode, and operand against the selected relocated bytes. Analysis took about 6.17 seconds after target selection.

Private Evidence ID: `ev_a390324740e17d7207a219105873edad904f2e359b47a2fb03bc32e0acff181b`. Raw retail dossiers and binaries remain local. Eight source-owned regression tests pass, including checks that equivalent shift/condition aliases compare equal while distinct memory addressing modes do not.

## Reproduce

From the project root in PowerShell:

```powershell
.\.local\venv\Scripts\python.exe -m pip install -r tools/requirements-analysis.txt
git clone https://github.com/AlgebraManiacABC/3DS-Decomp-Pipeline.git .local/pipeline-reference
git -C .local/pipeline-reference checkout --detach 621bbce909ad2f9c551563c7443ed80c0123fe77
.\.local\venv\Scripts\python.exe tools/inventory_modules.py 'roms\your-base.3ds'
.\.local\venv\Scripts\python.exe tools/describe_modules.py
.\.local\venv\Scripts\python.exe tools/module_view.py extracted/base/modules/AnaiTest.cro analysis/private/AnaiTest.elf
wsl -d Ubuntu -- node /mnt/c/code/UltraSunnyMoon/tools/query-native.mjs /mnt/c/code/UltraSunnyMoon/config/module-analysis.json
.\.local\venv\Scripts\python.exe tools/verify_module_view.py extracted/base/modules/AnaiTest.cro analysis/private/AnaiTest.elf
.\.local\venv\Scripts\python.exe tools/verify_function.py analysis/private/AnaiTest.relocated analysis/private/AnaiTest.elf analysis/private/YOUR_RUN/1-analyze_function.json --mode arm
```

Skip cloning if the pinned reader already exists. Substitute the printed private run directory and the local WSL project path. PyCTR 0.7.6 reads the decrypted RomFS directly; no boot ROM keys are requested. Encrypted input is rejected.

## Rebuild implications and remaining work

- Preserve the distinction between CRS absolute main-image descriptors and CRO file-relative segments.
- Carry segment-tagged imports, exports, and relocation records through splitting/linking.
- Dynamic data/BSS allocation, imported-symbol resolution, registration hashes, runtime load order, and gameplay behavior are not established by this sample.
- The first module proof is intentionally import-free. It does not establish that all 132 CROs can be loaded correctly.
- Next is compiler/runtime fingerprinting and a verified unchanged-binary reconstruction. Decompilation source replacements come after that baseline passes.
