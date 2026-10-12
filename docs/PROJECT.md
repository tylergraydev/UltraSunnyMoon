# Project overview

## Overall goal

UltraSunnyMoon is a public Pokémon Ultra Sun reverse-engineering and
decompilation project. Its immediate goal is readable C/C++ that reproduces
the behavior of the pinned game revision and participates in a verified build.
Exact matching, behavioral verification, compiled-object selection, and game
runtime observations are recorded separately.

The long-term direction includes running the reconstructed game natively on
PC. That requires recovering the game and implementing host replacements for
3DS graphics, audio, input, storage, and OS services. Current hybrid builds
still contain mostly original game code and assets and require a 3DS runtime.

Ultra Sun is the primary target. Pokémon Moon research can be consulted where
its applicability is demonstrated. REA with Ghidra supplies analysis; the
pinned 3DS Decomp Pipeline supplies splitting/linking machinery. Reconstructed
game source currently uses C. Rust remains an option for supporting tools.

## Phases

The [public roadmap](https://github.com/tylergraydev/UltraSunnyMoon/issues/1)
owns the phase epics and their acceptance conditions:

| Phase | Purpose |
| --- | --- |
| 1 | Prove trustworthy REA analysis. |
| 2 | Pin target inputs, inventory modules, and establish reference behavior. |
| 3 | Verify unchanged builds and investigate compiler matching. |
| 4 | Reconstruct, integrate, and validate one function end to end. |
| 5 | Recover a bounded useful subsystem. |
| 6 | Scale verified reconstruction across the game. |
| 7 | Reproduce the complete build from a fresh checkout and local inputs. |
| 8 | Expand gameplay validation and maintain contributor reproducibility. |

Phases overlap where tasks are independent. A function reconstruction does not
close an epic whose gameplay or integration acceptance conditions remain open.
Native port planning follows sufficient reconstruction and interface evidence.

## Repository structure

| Path | Purpose | Visibility |
| --- | --- | --- |
| `AGENTS.md` | Instructions for agents continuing this project | Public |
| `README.md` | Entry point, project status, roadmap | Public |
| `src/runtime/` | Reconstructed runtime/startup C functions | Public |
| `tools/` | Analysis launchers, compilation, rebuilding, packaging, verification | Public |
| `tests/` | Source-owned regression fixtures and tests | Public |
| `config/` | REA analysis plans, not credentials or emulator settings | Public |
| `docs/` | Goals, evidence summaries, reproduction commands, handoff | Public |
| `roms/` | User-supplied base and update containers | Ignored/private |
| `extracted/` | Extracted executable/header/module resources | Ignored/private |
| `analysis/private/` | Retained evidence, generated builds, receipts, runtime profiles | Ignored/private |
| `.local/` | Virtual environment, pinned external checkouts, tool archives, scratch files | Ignored/private |

Generated retail-derived objects are not reconstructed source. They stay private
even when used to prove an unchanged or hybrid build.

## Tool responsibilities

- `wrap_code.py`, `module_view.py`, and `verify_*analysis/module/function*.py`
  prepare and independently check analysis views.
- `query-native.mjs` and `rea*.sh` execute retained REA analysis plans.
- `compile_helper.py`, `compile_bss.py`, and `verify_*behavior.py` compile
  selected reconstructions and compare isolated execution with the original.
- `rebuild_main.py` and `rebuild_module.py` use the pinned pipeline;
  `verify_main_rebuild.py` and `verify_rebuild.py` independently check results.
- `package_runtime.py` and `verify_runtime_package.py` build and verify private
  original/rebuilt game packages.
- `prepare-runtime.ps1`, `configure-runtime-rpc.ps1`, `probe_runtime_rpc.py`,
  `compare_runtime_rpc.py`, and `collect_runtime.py` prepare isolated emulator
  profiles and collect bounded runtime evidence.

## Documentation map

| Document | Read it for |
| --- | --- |
| [HANDOFF](HANDOFF.md) | First action in the next session and selected local artifacts |
| [STATUS](STATUS.md) | Current milestones, open gates, priorities |
| [TARGET](TARGET.md) | Base/update identity, hashes, memory layout |
| [SETUP](SETUP.md) | Initial WSL/REA preparation and extraction |
| [DECOMP_WORKFLOW](DECOMP_WORKFLOW.md) | Decode → reconstruct → compile → verify → integrate |
| [FULL_ANALYSIS](FULL_ANALYSIS.md) | Main-image REA profile, evidence, coverage limits |
| [MODULES](MODULES.md) | CRS/CRO inventory and load/relocation observations |
| [MAIN_REBUILD](MAIN_REBUILD.md) | Unchanged main baseline and independent verification |
| [REBUILD](REBUILD.md) | Unchanged AnaiTest CRO baseline |
| [FIRST_SOURCE](FIRST_SOURCE.md) | Integrated array-construction helper |
| [STARTUP_BSS](STARTUP_BSS.md) | Integrated second function and four-policy verification |
| [RUNTIME](RUNTIME.md) | Packages, Azahar/RPC, startup checkpoint, remaining gameplay gate |
| [FEASIBILITY](FEASIBILITY.md) | Historical initial pilot; later milestones supersede its open questions |
