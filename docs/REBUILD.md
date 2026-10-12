# Unchanged module reconstruction

The base Ultra Sun `AnaiTest.cro` has been split into six ARM ELF objects,
linked, and recreated with an exact match to all 8,192 original bytes.
This establishes a small unchanged-binary baseline for phase three.
There are zero compiled source replacements and no runtime execution claim.

## What was reconstructed

The pinned [3DS Decomp Pipeline](https://github.com/AlgebraManiacABC/3DS-Decomp-Pipeline/tree/621bbce909ad2f9c551563c7443ed80c0123fe77)
supplies the splitter, ELF writer, linker invocation, and CRO serializer.
Our adapter splits the original payload at previously verified boundaries:
two instruction ranges, the intervening switch table, literal pool, text
padding, and original data. These names describe analysis ranges; they are
not recovered source function names.

The pipeline payload is a concatenation of 3,712 header-declared text bytes
and four data bytes. Only 172 text bytes belong to the nonempty TEXT segment;
the remaining text extent includes original padding. All six objects use
`.text` for byte-preserving concatenation, including the data object. This
pilot does not model separate runtime sections or generate new relocations.

The linked 3,716-byte payload matches that original concatenation. The CRO
serializer uses the linked text and retains original data, metadata,
import/export tables, segment descriptors, and relocation records. The
four original data bytes therefore pass through the linker for verification,
but container recreation still obtains them from the original CRO object.
Region hashes are recomputed. This is a split/link/container rebuild with
preserved original sections, not a source decompilation.

An independent verifier reads ELF sections and CRO fields directly without
importing the pipeline reader. It checks each split object, the linked ELF,
the extracted linked payload, all four CRO region hashes, and full-file
equality. Altering a rebuilt CRO byte, a split-object payload byte, or a
linked-payload byte must each fail verification.

Original and rebuilt SHA-256:
`b996787f2bf5ab6182cbd0470ea1801d5bf0ee7e15e96b49c5b53a785dc66034`.

## Toolchain and compatibility

The tested host is Ubuntu 22.04 under WSL with Python 3.10.12,
typing_extensions 4.12.2, and Ubuntu `binutils-arm-none-eabi`
`2.38-3ubuntu1+15build1`. GNU `ld` and `objcopy` report version 2.38.
Their executable hashes and paths are retained in the private run report.
These are reconstruction tools, not identified retail build tools.

The upstream CLI's linker script fails on this binutils version because
`LINKER_VERSION` is treated as an input filename. Our adapter calls the
pinned pipeline operations with a minimal ARM little-endian linker script
that concatenates `.text` at zero. No files in the external checkout are
modified. The pipeline's generated EABI flags describe its ELF objects;
they do not prove the retail compiler's ABI options.

## Compiler investigation

| Evidence | Conclusion | Still unknown |
| --- | --- | --- |
| Plain-region tag `CTR_SDK-11_4_1_200_none` | SDK tag observed in the supplied base | Compiler executable, version, flags |
| ARM and Thumb instruction samples independently verified | Both instruction modes occur | Per-file CPU/optimization options |
| CRS exports `__aeabi_vec_ctor_nocookie_nodtor` at encoded `0x100051` | Named Arm C++ runtime helper; canonical Thumb address `0x100050` | Which vendor supplied that implementation |
| Exports include `__c89vsnprintf` and `__2sprintf` | Additional runtime fingerprint candidates | Vendor/version attribution needs independent comparison |

The [Arm runtime ABI specification](https://github.com/ARM-software/abi-aa/blob/main/rtabi32/rtabi32.rst)
defines the array-construction helper and requires compliant runtimes to
supply it. Its presence cannot uniquely identify a compiler. Arm's legacy
compiler/runtime family is an investigation candidate; GCC and other
ABI-compatible toolchains remain possible sources or reconstruction tools.
No candidate version or optimization configuration is established yet.
Game code and bundled runtime libraries may come from different toolchains.

The [Moon build documentation](https://github.com/gradenGnostic/pokemoon/blob/main/docs/BUILD.md)
and [Makefile](https://github.com/gradenGnostic/pokemoon/blob/main/Makefile)
provide a reference for GCC-based reconstructed builds and replacement
verification. That project's tool choices are not evidence of Ultra Sun's
original compiler, and its target differs from ours.

## Reproduce

Use the pinned external checkout already described in [module setup](MODULES.md).
Install the ARM binutils package in Ubuntu, then run from the project root:

```powershell
wsl -d Ubuntu -u root -- apt-get install -y binutils-arm-none-eabi
wsl -d Ubuntu -- python3 tools/rebuild_module.py extracted/base/modules/AnaiTest.cro analysis/private/rebuild-my-run
.\.local\venv\Scripts\python.exe tools/verify_rebuild.py extracted/base/modules/AnaiTest.cro analysis/private/rebuild-my-run
```

WSL Python needs `typing_extensions` with `deprecated` support (tested 4.12.2).
The run directory must be new and inside `analysis/private`. The tool rejects
any module whose name or hash differs from the verified pilot. Generated
retail bytes, object files, symbol CSVs, logs, and evidence stay ignored.

## Next gate

Issue [#15](https://github.com/tylergraydev/UltraSunnyMoon/issues/15) remains
open for compiler fingerprinting and first-replacement selection. The
verified Thumb array-construction helper is a promising source candidate
because its ABI signature has a public definition. Before replacing it,
prove unchanged reconstruction of the main executable, recover its exact
calling behavior, and compile candidate implementations with explicit
toolchain versions/options. Larger imported modules also depend on
[runtime loading work](https://github.com/tylergraydev/UltraSunnyMoon/issues/16).
