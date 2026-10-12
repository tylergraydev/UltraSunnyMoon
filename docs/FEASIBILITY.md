# REA / Ultra Sun feasibility result

Date: October 12, 2026.

**Verdict: REA with Ghidra can analyze a verified bounded view of the supplied Ultra Sun base executable. Full-game import performance is not yet established.**

## Observed evidence

- Provider checks pass with Ghidra 12.1.4, Temurin JDK 21.0.12.1+1, and Node 22.22.1 in Ubuntu WSL.
- A source-owned fixture produces assembly, pseudocode, and its caller through REA.
- Complete base and update code images have separate extended-header mappings and SHA-256 identities. The ELF wrapper preserves original initialized bytes; `readelf` independently confirms declared segment addresses and offsets.
- The bounded pilot maps the first `0x48` bytes of base text, with original data/read-only mappings and conservative BSS provision. It analyzes the helper at `0x00100024` without publishing executable bytes or raw dossiers.
- REA reports a 28-byte function containing seven ARM instructions, a caller at `0x00100000`, and literal references at `0x00100040` and `0x00100044`.
- Capstone 5.0.7 independently agrees on all seven instruction addresses, opcodes, operands, branch destination, and resolved PC-relative literal loads. Verification also checks the reported caller and literal references.

Private pilot Evidence ID: `ev_de476077c34bebc6437a4a3c19726cb4f213db9cfb9ffdbebc54b86d3e56e360`. Retained artifacts are under ignored `analysis/private/`; this report contains sanitized conclusions. Evidence IDs identify local REA records, not publicly hosted files.

## Supported inference

The helper writes zero in four-byte steps over `[0x006a3d48, 0x006d3f04)`, a 197,052-byte range. Its start equals the base data address plus logical data size. Its length equals the extended header's BSS size. This supports identifying it as the startup BSS-clearing helper.

The name is inferred, not a recovered original symbol. This is static evidence, with no claim of execution, compiler matching, or replacement in a rebuilt game.

## Decisions and limits

- REA npm 6.4.0 lacks the current branch's raw-binary controls and analysis-option support. We use source revision `7ae3c50a9d49c480035855de9fcc4484befacd92`, distinguished from the older registry artifact with the same version.
- Ghidra defaults to ARMv8 for the synthetic ELF. The pilot explicitly uses `ARM:LE:32:v6` and the default analysis compiler convention. Retail compiler/ABI identity remains open.
- Global `Stack` and `Decompiler Parameter ID` analyzers are disabled and recorded in REA's analysis profile.
- Full-image imports spent several minutes in global stack/switch recovery and were stopped. Bounded imports completed in seconds. This does not establish whole-game coverage or throughput.
- Ubuntu 22.04 is outside REA's general documented Ubuntu 24.04+ support list, despite passing provider checks and the local pilot.
- No game resources, binaries, cryptographic metadata, or raw retail disassembly are committed. CLI use is verified; persistent Codex MCP integration is not configured.

## Next work

Tune a complete-image import with explicit analyzer choices. Confirm ARM/Thumb boundaries and module loading, identify the retail compiler, and establish an unchanged-binary rebuild before attempting a compiled replacement. Phase 2 still needs its gameplay baseline and module/resource inventory.

See [SETUP.md](SETUP.md) for commands and [TARGET.md](TARGET.md) for target identity.
