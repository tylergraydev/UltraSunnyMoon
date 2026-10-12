# Runtime comparison preparation

The original and rebuilt Ultra Sun base applications are packaged locally
as decrypted standalone CXIs. Both pass container and payload verification.
**Both original and rebuilt games now reach the language-selection screen,
with live helper bytes and RPC frames verified.** Gameplay beyond this
startup checkpoint remains unverified. The runtime comparison remains open in
[#19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19).

## Packages

Each CXI contains the original main NCCH partition from the pinned base
NCSD image, with a size of 3,693,465,600 bytes. The original CXI is verified
byte for byte against that source partition. The base input is unchanged.
The update is not applied or installed.

The rebuilt CXI uses the [verified compiled-helper image](FIRST_SOURCE.md).
The original code entry is replaced at its existing offset and size. The
ExeFS `.code` SHA-256 and the NCCH ExeFS-superblock SHA-256 are updated.
The code compression flag, extended header, RomFS, modules, banner, icon,
and all other bytes remain original.

| Artifact | SHA-256 |
| --- | --- |
| Original CXI | `147877e6ac1d85c8d43240a800c91dc12d9ae1310a649469688cb1f3813bca0c` |
| Rebuilt CXI | `402e27eab7ad01274f6cc85734ad285fa2783565c6b1290aad8cd65d9acd3be1` |
| Packaged rebuilt code | `c557617562525a2959a8fc3763b1398825b861ed69960646022dd34dd7ce2736` |

Exactly 90 container bytes differ: 27 helper instruction bytes and 63 bytes
across the two updated hashes. No repacking or regeneration of assets is
performed. These are emulator test containers. The retail RSA signature is
retained rather than regenerated; no hardware signature-validity claim is
made.

The format fields were checked against the pinned
[Azahar NCCH/ExeFS definitions](https://github.com/azahar-emu/azahar/blob/2126.2/src/core/file_sys/ncch_container.h)
and the installed PyCTR ExeFS reader. The standalone verifier independently
reads fields and checks input identity, partition extraction, code payload,
ExeFS entry hashes, header-region hashes, bounds, and complete preservation
outside code and required hash updates. It does not validate the RSA
signature or claim to recheck every internal RomFS hash-tree node.

Four private corruption probes reject altered code, an altered ExeFS hash,
a RomFS change, and an unrelated signature byte. Four synthetic package
regression tests are source-owned; all 17 repository tests pass.

## Pinned runtime preparation

[Azahar 2126.2](https://github.com/azahar-emu/azahar/releases/tag/2126.2)
is prepared from the official Windows MSYS2 archive. Its SHA-256 matches
the release asset digest:
`aa6d4c631c883355e50f5f62fd26a0e053d63e4cc29b8ded6b3b7d175ec3864e`.
The extracted executable hash is
`3589bbe789ffc8d4becc84fe34c1eea7358735454d9d25f4a043a0db42cf0cf8`.

Two separate portable directories, `original` and `rebuilt`, each contain a
fresh `user` directory beside the executable. Azahar's
[user-path handling](https://github.com/azahar-emu/azahar/blob/2126.2/src/common/file_util.cpp)
selects that directory when present. Existing installed-game saves and
settings are not copied or modified. The preparation tool does not launch
either runtime. Actual runtime settings are recorded in the observations below.

## Reproduce preparation

From the repository root in PowerShell, after the verified helper build:

```powershell
.\.local\venv\Scripts\python.exe tools/package_runtime.py 'roms/your-pinned-base.3ds' analysis/private/helper-integrated-final analysis/private/runtime-my-packages
.\.local\venv\Scripts\python.exe tools/verify_runtime_package.py analysis/private/runtime-my-packages analysis/private/helper-integrated-final --base 'roms/your-pinned-base.3ds'
.\tools\prepare-runtime.ps1 -Destination analysis/private/runtime-my-profiles
```

Substitute the actual input and main-build directory. New package/profile
directories must stay inside `analysis/private`. The two packages require
about 7.4 GB together. Runtime executables, configurations, generated games,
logs, and proof artifacts remain local and ignored.

## Original-game startup baseline

The user manually launched the original portable profile and `original.cxi`.
The running process title identifies Pokémon Ultra Sun; the profile's
recent-file record names the prepared original package. Its independently
measured package digest matches the verified original CXI above. This binds
the selected input through profile records rather than process-memory
attestation.

The retained log reports Azahar `2126.2 | HEAD-219d743` and program ID
`00040000001b5000`. Recorded settings are CPU JIT enabled, CPU clock 100%,
OpenGL, hardware shaders and shader JIT enabled, resolution factor 1, New
3DS mode enabled, and automatic region (`-1`). Raw configuration and log
snapshots are retained privately with hashes.

The game's `LangSelect` CRO loaded at `0x006DD000`, with fixed end
`0x006E8000`. The loader reports anonymous exports to the static module.
This is observed module-loading evidence; loaded instruction bytes and
resolved imports have not been read back from runtime memory.

Fresh-profile logs also include missing save-data/cache files and stubbed
services. Their presence alone is not a crash result. Both visible startup
screens are now confirmed through RPC frames; the first gameplay path
remains open.

Collect a manually launched run without controlling its window:

```powershell
.\.local\venv\Scripts\python.exe tools/collect_runtime.py analysis/private/azahar-runtime/original/azahar-windows-msys2-2126.2/user analysis/private/runtime-packages/original.cxi analysis/private/my-original-observation
```

Use `--screen` with an explicit `--screen-source` to distinguish user
reports from agent inspection of captured RPC frames.

## Live original/rebuilt checkpoint

The original and rebuilt packages were launched sequentially through
Azahar's game-file command-line interface in their separate prepared
profiles. Both use the eight runtime settings recorded above. RPC selected
the Ultra Sun process `momiji`, read the 34-byte helper at `0x00100050`,
and captured a 400×480 rendered game frame for each run.

| Live evidence | Original | Rebuilt |
| --- | --- | --- |
| Helper SHA-256 | `897f0c9729d5648e56c58ce2cf310343b4b95613959e2d8b054b574b38601474` | `e13c194dbabfc40d5885f2956701b5e6264c55cf818e202c4dc4cd6538ced920` |
| Observed screen | Language selection, English highlighted | Language selection, English highlighted |

The original live helper exactly matches the pinned original image. The
rebuilt live helper exactly matches the compiled source replacement, and
differs from the original. This is runtime-memory attestation for that
selected function; it is not just a package or log observation.

Both RPC PNGs were visually inspected. They show the same startup screen
and selection. Frames were captured at different times and their hashes differ;
no pixel-identical or deterministic-timing claim is made. Raw screenshots,
loaded bytes, logs, configurations, and comparison receipts remain private.
The evidence comparator rejects original-helper substitution and frame
corruption. Eighteen source-owned tests pass, including a regression check
for Qt's actual one-backslash default marker and the earlier malformed
marker's repair.

Compare retained RPC evidence:

```powershell
.\.local\venv\Scripts\python.exe tools/compare_runtime_rpc.py analysis/private/rpc-original-verified analysis/private/rpc-rebuilt-verified extracted/base/exefs/code.bin analysis/private/helper-integrated-final/out/code.bin
```

The selected compiled helper remains **behavior-tested, nonmatching**. A
language-menu boot does not prove exception compatibility, execution counts
for this helper, or gameplay/title/overworld compatibility. Those remain
separate gates.

## Remaining execution gate

### Azahar's own RPC interface

The prepared 2126.2 build includes the official `scripting/AzaharRPC.py`
client. It supports process selection, memory reads/writes, game-frame
capture, and performance statistics. Our `probe_runtime_rpc.py` exposes
only process selection, a bounded helper-byte read, performance queries,
and optional rendered-frame capture. It binds the client hash, Ultra Sun
title ID, and expected original/rebuilt helper bytes to private evidence.
No writes to game memory or controller-input injection are exposed.

RPC is now enabled and tested in both isolated profiles. The first restart
exposed a configuration-helper bug: Qt's default marker was not updated,
so Azahar reset RPC to disabled. The tool now emits the actual one-backslash
QSettings key and normalizes the earlier malformed marker. A second restart
confirmed the active RPC listener and enabled setting.

Azahar's [debug configuration](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_qt/configuration/configure_debug.cpp)
only allows RPC to change while emulation is stopped. To prevent the app
from overwriting an external configuration edit on exit, close the prepared
Azahar before running:

```powershell
.\tools\configure-runtime-rpc.ps1
```

The tool rejects active prepared profiles, verifies executable receipts,
backs up existing configurations, and sets both the RPC value and its
QSettings default marker. A source-owned configuration fixture verifies
setting preservation and the backup. Only isolated profiles are touched.

After reopening the original profile and its game through the GUI or its
supported command-line game path:

```powershell
.\.local\venv\Scripts\python.exe tools/probe_runtime_rpc.py analysis/private/azahar-runtime/original/azahar-windows-msys2-2126.2 extracted/base/exefs/code.bin analysis/private/my-original-rpc-proof
```

Use a new private output directory. The client connects to localhost UDP
45987 with bounded request timeouts. Azahar's [server](https://github.com/azahar-emu/azahar/blob/2126.2/src/core/rpc/udp_server.cpp)
binds UDP 45987 on all IPv4 interfaces; the wrapper's localhost destination
does not change that server binding. No firewall changes are performed.
Only run one RPC-enabled test instance at a time because the port is fixed.

For the rebuilt profile, substitute its runtime directory and
`analysis/private/helper-integrated-final/out/code.bin`. The probe refuses
to accept original helper bytes as proof of the rebuilt image. Native
window automation remains a separate permission mechanism.

Automatic approval review rejected the attempted Azahar window launch:
“Computer Use was not approved to use azahar.” The user explicitly approved
the original/rebuilt comparison, but the subsequent launch received the
same rejection and Azahar was absent from the Computer Use app inventory.
Native window-control access remains unavailable. Subsequent work uses the
separately authorized Azahar scripting and game-file CLI interfaces, without
desktop screenshot capture or injected Windows input.

Azahar's API now supplies live-byte proof and rendered-frame observation.
Next extend the comparison beyond language selection into a reproducible
gameplay path. Controller input is not exposed by the shipped RPC client;
supported input-movie replay or manual game input must provide that part.
The original/rebuilt startup checkpoint does not establish complete game
compatibility.

Phase four remains open until a working rebuilt-game comparison is
observed. Exact compiler matching remains separate in #15.
