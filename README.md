# UltraSunnyMoon

A public reverse-engineering and decompilation project for Pokémon Ultra Sun. The goal is a readable, rebuildable codebase with independently verified replacements for original game code.

**Status: original and rebuilt games boot to language selection.** RPC verifies that the rebuilt game's live 34-byte Thumb helper contains the compiled C replacement. It is behavior-tested but nonmatching; all bytes outside its slot remain original in the rebuilt image. Exact matching, retail compiler identification, and gameplay beyond the startup menu remain future work. No reconstruction completion percentage is claimed.

See [runtime preparation](docs/RUNTIME.md), [first source evidence](docs/FIRST_SOURCE.md), [main rebuild evidence](docs/MAIN_REBUILD.md), [module rebuild evidence](docs/REBUILD.md), [the decompilation workflow](docs/DECOMP_WORKFLOW.md), [module findings](docs/MODULES.md), [full-analysis findings](docs/FULL_ANALYSIS.md), [setup](docs/SETUP.md), and [target identity](docs/TARGET.md).

Starting a new session? Read [AGENTS.md](AGENTS.md), the
[session handoff](docs/HANDOFF.md), and the [project overview](docs/PROJECT.md).

## Public roadmap

The [startup BSS clearer](docs/STARTUP_BSS.md) is now a second compiled,
behavior-tested C reconstruction. It remains nonmatching and awaits integration.

[Current checkpoint and next priorities](docs/STATUS.md)

[Roadmap and progress tracker](https://github.com/tylergraydev/UltraSunnyMoon/issues/1)

The roadmap owns eight phase epics through GitHub sub-issue relationships. Phase one owns the initial actionable tasks. Later phases will be expanded as evidence clarifies their scope.

| Phase | Epic | Completion condition |
| --- | --- | --- |
| 1 | [Prove REA analysis](https://github.com/tylergraydev/UltraSunnyMoon/issues/2) | Trustworthy instructions, pseudocode, and references through REA. |
| 2 | [Establish the reference game](https://github.com/tylergraydev/UltraSunnyMoon/issues/3) | Pinned target identity, hashes, extraction, and baseline. |
| 3 | [Build the reconstruction foundation](https://github.com/tylergraydev/UltraSunnyMoon/issues/4) | Verified untouched binary reconstruction and compiler investigation. |
| 4 | [Complete one function end to end](https://github.com/tylergraydev/UltraSunnyMoon/issues/5) | Verified compiled replacement and working rebuilt game. |
| 5 | [Recover one small subsystem](https://github.com/tylergraydev/UltraSunnyMoon/issues/6) | Readable subsystem source with behavior verification. |
| 6 | [Scale across the game](https://github.com/tylergraydev/UltraSunnyMoon/issues/7) | Growing verified coverage and an inventory of remaining work. |
| 7 | [Reconstruct the complete build](https://github.com/tylergraydev/UltraSunnyMoon/issues/8) | Reproducible build from a fresh checkout and local inputs. |
| 8 | [Validate and maintain](https://github.com/tylergraydev/UltraSunnyMoon/issues/9) | Documented gameplay validation and contributor reproducibility. |

## Start here

- [Select a working REA environment](https://github.com/tylergraydev/UltraSunnyMoon/issues/10).
- [Establish correct executable loading](https://github.com/tylergraydev/UltraSunnyMoon/issues/11).
- [Verify analysis of one small function](https://github.com/tylergraydev/UltraSunnyMoon/issues/12).

## Technical direction

Use a pinned [REA](https://github.com/morluto/rea) source revision with Ghidra through Ubuntu WSL for agent-accessible analysis. Main-executable imports and reusable MCP queries are verified; dynamic-module loading remains open. Reconstructed game code will use C/C++ according to binary evidence; Rust remains an option for supporting tools. Evaluate [3DS Decomp Pipeline](https://github.com/AlgebraManiacABC/3DS-Decomp-Pipeline) for splitting, comparison, linking, and module recreation. Reference [Pokémon Moon](https://github.com/gradenGnostic/pokemoon) selectively after checking applicability to Ultra Sun. A PC port is a later scope decision.

## Verification and contributions

Track exact matches, tested nonmatching implementations, and unverified reconstructions separately. Record function addresses, target hashes, inferred types, dependencies, and verification evidence. A bootable hybrid build is insufficient: prove compiled replacements were selected. AI-assisted reconstructions require review against binary evidence and meaningful verification.

Use the relevant phase epic for proposals and discoveries. New tasks should include scope, dependencies, acceptance criteria, and unknowns. Keep future phases high level until discoveries justify detailed work.

## Local game inputs

Supply your own game inputs locally under `roms/`. Keep the base CIA and update separate until target selection and extraction are documented. `roms/`, common retail container formats, extracted resources, and generated outputs are excluded by `.gitignore`. Verify exclusions before local commits; ignore rules do not remove already tracked files. Do not attach retail binaries or assets to public issues or commits.

This is an independent fan research project, unaffiliated with Nintendo, Game Freak, or The Pokémon Company.
