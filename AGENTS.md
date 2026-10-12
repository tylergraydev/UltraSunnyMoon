# Agent guide

## Goal and reading order

Build a readable, reproducible Pokémon Ultra Sun decompilation from the user's
local game dump. Reconstruct C/C++ from verified binary evidence, compile it,
prove selected source objects are used, and validate behavior. A native PC port
is a later objective requiring replacement console services; a 3DS rebuild does
not itself provide that port. Rust may be used for tools, but current game
reconstructions use C.

Start a new session by reading:

1. [Session handoff](docs/HANDOFF.md): next task, exact local artifacts, commands.
2. [Current status](docs/STATUS.md): proven milestones and open gates.
3. [Project overview](docs/PROJECT.md): structure, phases, documentation index.
4. The evidence document for the function or subsystem being changed.

The public [roadmap issue #1](https://github.com/tylergraydev/UltraSunnyMoon/issues/1)
and its phase sub-issues track work. Keep findings, acceptance conditions, and
remaining gaps current. Do not close an issue merely because a partial milestone
works. Completed BSS reconstruction is #20; integration remains the next task.

## Target and evidence rules

- Target the pinned **Ultra Sun base version 0**, title `00040000001b5000`.
  Keep the update separate. See [target hashes](docs/TARGET.md).
- Reuse matching retained REA evidence instead of repeating large imports.
  `tools/query-native.mjs` runs plans in one session; `tools/rea-arm-full.sh`
  selects the ARMv6 analysis profile. Preserve its analyzer limitations.
- Independently check function boundaries, ARM/Thumb mode, instruction decoding,
  literal pools, addresses, and dependencies. Pseudocode and inferred types
  require review; they are not recovered original source.
- Distinguish **byte matching**, **behavior-tested nonmatching**, and
  **unverified**. Equal code size does not establish matching. Loading replacement
  bytes does not prove they executed. Startup does not establish full gameplay.
- Preserve source, compiler, object, target, and evidence identities in receipts.
  Do not silently retain original code when a requested source replacement fails.
- Keep unchanged reconstruction the default. Nonmatching integration must remain
  explicitly selected and behavior-verified. Prove linker object selection and
  all bytes outside approved replacement ranges independently.

## Workspace and execution

- Main checkout: `C:\code\UltraSunnyMoon`; WSL path:
  `/mnt/c/code/UltraSunnyMoon`. Run PowerShell commands from the repository root.
- Use `.local/venv/Scripts/python.exe` for Windows analysis and Unicorn tests.
  Use `wsl -d Ubuntu -- python3 ...` for ARM compilation and pipeline builds.
- Existing tools are prepared. Do not reinstall or upgrade them as a routine
  first step. Read [setup](docs/SETUP.md) only when preparation or repair is needed.
- New generated runs must use new directories under `analysis/private/`.
  Do not overwrite retained proof. Prefer file-based scripts/plans to complex
  nested PowerShell/Bash quoting.
- Keep edits focused on the selected reconstruction or verification gate.
  Run relevant behavior checks and `python -m unittest discover -s tests -v`
  when changing verification tooling. Tests use source-owned fixtures, never
  committed retail instruction bytes.

## Public/private boundary

Public files: reconstructed source, tools, source-owned tests, configuration
plans, and sanitized findings. Private/ignored files: `roms/`, `extracted/`,
`analysis/private/`, and `.local/`, including retail bytes, wrapped ELF images,
raw REA dossiers, runtime game frames, emulator logs/configuration, and keys.

Before a commit, inspect `git status --short`, staged paths, and
`git diff --cached --check`. Never attach private artifacts to GitHub issues.
Do not publish raw disassembly, decompiler dossiers, or game assets.

## Runtime work

- Prepared Azahar profiles and packages are documented in [runtime](docs/RUNTIME.md).
  Its supported CLI and shipped RPC client have been used successfully.
- Only one RPC-enabled Azahar instance may run at a time: UDP port 45987 is fixed.
  Check process identity by executable path before stopping a test process.
  Never assume a saved PID is still valid or terminate unrelated instances.
- Native desktop control previously received an app-access rejection. Do not
  repeat that route without a real access-state change or edit access policies
  to bypass it. CLI/RPC work has separate authorization and remains usable.
- The first synthetic movie trial failed before RPC became available. Do not
  treat it as a valid replay. Keep emulator automation bounded; source
  reconstruction can continue while gameplay validation #19 remains open.

## Finish and hand off

Record what changed, why, verification results, and material proof limits.
Update `docs/STATUS.md` and `docs/HANDOFF.md` when the next task or local artifact
selection changes. Link public work to its issue/epic. Leave a clean, reviewable
checkout and preserve private evidence for the next session.
