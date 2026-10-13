# Runtime comparison preparation

The original and rebuilt Ultra Sun base applications are packaged locally
as decrypted standalone CXIs. Both pass container and payload verification.
**Original and combined rebuilt games now reproduce controllable bedroom
gameplay with the same movie, live code readbacks, and inspected RPC frames.**
The bounded startup/first-gameplay acceptance is complete in
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
screens are confirmed through RPC frames. The newer paired gameplay checkpoint
below supersedes the earlier startup-only limit.

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

## Bounded gameplay acceptance and earlier checkpoints

### First controllable gameplay comparison (2026-10-12)

[Runtime validation #19](https://github.com/tylergraydev/UltraSunnyMoon/issues/19)
now meets its first reproducible gameplay acceptance. Original and combined
BSS/constructor builds replay the same public
[input plan](../config/runtime-gameplay-replay.json) in separate fresh profiles.
The sequence selects the default avatar, enters a fixed test name using touch,
continues the introduction, wakes the player, and supplies directional input in
the starting bedroom. Both variants show the same bounded movement path:

| Capture at approximately host seconds | Observed state, both variants |
| --- | --- |
| 160 | Avatar stands on the left side near the TV |
| 171 | Avatar has crossed right toward the bed |
| 177 | Avatar has moved forward and faces the camera |

The corresponding circle-pad holds are right at movie seconds 670..673 and
down at 690..693, following wake-up and a leftward hold. Scene landmarks,
different avatar positions, facing direction, and camera tracking corroborate
player control; the result is not based on merely loading the bedroom scene.
Both root and an independent reviewing agent inspected the six key frames.
Animation phases differ, so no pixel-identical or exact-timing claim is made.

The selected movie SHA-256 is
`4eb05f47ed3b807709138ab8b4eb914dedbf7a6af16f70994f4ad52b40ea6481`;
the plan SHA-256 is
`c02cf85d90f14f857030f46e27fcb4d786b65ffe942745a95c181c8e20618bad`.
The 1,200-second horizon is a guard against premature playback completion;
both runs are stopped after capture rather than allowed to reach that horizon.
There are 280,800 pad samples, paired with touch records. Movie ID 5 and the
pinned runtime revision are bound in the evidence.

The emulator speed limit is explicitly **400% in both profiles**, while game
CPU clock remains **100%**. Eight logged runtime settings agree, as do the
selected speed-limit settings and module load sequences. This shortens wall
time without changing the plan's emulated input samples. New profiles start
with empty game saves; only global configuration is copied. Existing gameplay
profiles and the original dump are preserved.

Thirty-one paired RPC captures pass frame integrity, movie/log identity,
independently checked loaded movie ID, live constructor/BSS/literal readback,
and exact regeneration of the selected plan. The final log/config and package
hashes agree with their receipts. Neither retained log reports input-type
desynchronization or a movie revision warning. The compiled main image still
passes full object/section/load/range preservation checks. An independent agent
reran the key paired verifier and confirmed the movement and settings.

The suite passes 60 source-owned tests, including wrong loaded movie ID even
with a rehashed log, altered plan, poll boundaries, conflicting coordinates,
and preservation of the older default movie identity. Retail frames, live
bytes, logs, configurations, and packages remain private.

This completes the issue's bounded first controllable gameplay comparison.
It does not establish full-game compatibility, battles/overworld coverage,
exception behavior, routine execution counts, exact timing determinism, or
completion of the entire movie. Both replacements remain nonmatching.

#### Reproduce the paired gameplay path

Run the following from the repository root, reusing the verified combined
package and existing pinned preparation. Use new private directories. First
generate the exact selected plan and prepare two fresh profiles:

```powershell
.local/venv/Scripts/python.exe tools/startup_movie.py analysis/private/my-gameplay-plan --plan config/runtime-gameplay-replay.json
.\tools\prepare-runtime.ps1 -Destination analysis/private/my-gameplay-profiles
```

Copy the same reference `qt-config.ini` into each fresh profile's `user/config`
directory, without copying any saves or NAND data. Before either profile runs,
set `frame_limit=400` and `frame_limit\default=false` in both configurations,
then enable RPC with `configure-runtime-rpc.ps1 -RuntimeDirectory
analysis/private/my-gameplay-profiles`. Preserve the reference settings listed
above (CPU JIT, 100% CPU clock, OpenGL, hardware/shader JIT, resolution 1, New
3DS, automatic region). Configuration snapshots bind the settings actually used.

For each variant sequentially, set `$variant` to `original` or `rebuilt` and
run this capture sequence. No other RPC-enabled instance may be active:

```powershell
$variant = 'original' # Repeat as rebuilt after stopping this process.
$runtime = (Resolve-Path "analysis/private/my-gameplay-profiles/$variant/azahar-windows-msys2-2126.2").Path
$exe = Join-Path $runtime 'azahar.exe'
$movie = (Resolve-Path 'analysis/private/my-gameplay-plan/startup.ctm').Path
$package = (Resolve-Path "analysis/private/runtime-both-packages-1/$variant.cxi").Path
$code = if ($variant -eq 'original') { 'extracted/base/exefs/code.bin' } else { 'analysis/private/startup-both-integrated-1/out/code.bin' }
$run = "analysis/private/my-gameplay-$variant"
$process = Start-Process -FilePath $exe -ArgumentList @('-p', ('"'+$movie+'"'), ('"'+$package+'"')) -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
foreach ($checkpoint in 160,171,177) {
    while (((Get-Date)-$process.StartTime).TotalSeconds -lt $checkpoint) { Start-Sleep -Milliseconds 500 }
    .local/venv/Scripts/python.exe tools/probe_runtime_rpc.py $runtime $code "$run/at-$checkpoint" --movie $movie
}
$actual = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
if (-not $actual -or $actual.ExecutablePath -ine $exe) { throw 'Process identity changed' }
Stop-Process -Id $actual.ProcessId
.local/venv/Scripts/python.exe tools/collect_runtime.py "$runtime/user" $package "$run/runtime"
```

Independently inspect both frame sequences for the movement described above.
Capture timing is approximate; if startup/shader delays differ substantially,
capture neighboring frames while playback remains active and record their
order and elapsed times. Do not accept an unobserved movement result.

```powershell
.local/venv/Scripts/python.exe tools/verify_startup_replay.py analysis/private/my-gameplay-original/at-177 analysis/private/my-gameplay-rebuilt/at-177 extracted/base/exefs/code.bin analysis/private/startup-both-integrated-1/out/code.bin analysis/private/my-gameplay-plan/startup.ctm --plan config/runtime-gameplay-replay.json
```

### Replayed introduction checkpoint (2026-10-12)

Original and combined builds now advance beyond language selection using the
same CTM input movie in two fresh portable profiles, with empty initial saves
and matching global settings. Both inspected RPC frames show Professor Kukui
holding Rockruff at the same Pokémon Trainers dialogue. Both retain the verified
live constructor/BSS/literal bytes. Eight recorded runtime settings agree.

The selected movie SHA-256 is
`a1fbd184dfc17f999e01fc089c5d9572ca6d06aa28cfe147eba32992dbf40fba`.
It contains 42,120 pad samples, paired with neutral touch records, at the
emulator's 234 Hz pad rate. A is held for 59 samples every 702 samples, from
sample 3,510 inclusive through 17,550 exclusive; all later inputs are neutral.
The 180-second horizon permits a settled capture around 95 seconds before
completion. Both retained logs report movie ID 2 loaded and no input-type
desynchronization or revision warning through capture. Playback was stopped
after capture; completion of the entire movie and timing determinism are not
claimed. Frame hashes differ because animation phases differ.

The supported short playback option `-p` loads successfully. The pinned
[entry dispatcher](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_meta/main.cpp),
[CLI option scan](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_cli/citra_cli.cpp),
and [capture options](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_cli/citra_cli.h)
suggest long-option collision with the compression dispatcher as the cause of
the earlier empty-log trial. Do not use that failed run as replay proof.
The [Qt frontend](https://github.com/azahar-emu/azahar/blob/2126.2/src/citra_qt/citra_qt.cpp)
pauses emulation and opens a dialog at movie completion. A 90-second trial lost
RPC response at that boundary; the selected longer movie avoids that boundary
while collecting evidence. No native desktop control was used.

`startup_movie.py` generates and statically checks this bounded sequence.
`probe_runtime_rpc.py --movie` retains raw log bytes and binds the selected
movie ID/hash. `verify_startup_replay.py` checks both movie/log receipts and
RPC evidence; visual checkpoint inspection remains separate. An early private
capture script translated log newlines on Windows; corrected copies preserve
the logged text's original hash, and the earlier copies remain retained.
The public capture path now preserves bytes and has a CRLF regression test.
The source-owned suite passes 40 tests.

To reproduce, prepare new profiles, copy the same chosen global configuration
only, enable RPC, and use new evidence directories. Do not copy used save data.
Generate the movie and launch each variant sequentially:

```powershell
.local/venv/Scripts/python.exe tools/startup_movie.py analysis/private/my-replay-plan
# Use the corresponding fresh profile executable and verified CXI.
# Launch arguments: -p "C:\code\UltraSunnyMoon\analysis\private\my-replay-plan\startup.ctm" "<package.cxi>"
# Capture while playback is still running, around 95 seconds after launch:
.local/venv/Scripts/python.exe tools/probe_runtime_rpc.py <runtime-directory> <selected-code.bin> analysis/private/my-replay-evidence --movie analysis/private/my-replay-plan/startup.ctm
```

Then pass original/rebuilt evidence directories, their selected raw code images,
and the movie to `verify_startup_replay.py`. Verify process identity before
stopping each test instance. This checkpoint is still an introduction, not
controllable gameplay. Extend the same bounded approach through avatar/name
selection was the next step at that milestone; the newer gameplay result above
completes the bounded acceptance.

### Combined BSS and constructor startup check (2026-10-12)

The combined [startup build](STARTUP_BSS.md) is packaged in a new private run.
The original CXI still has the digest above. The combined CXI SHA-256 is
`95f7d7029f1d85218671175c1beb82b128bb30b0f092e3a9c2b1f38ceeb95086`,
and its code SHA-256 is
`1f13be78a12c7f47758271f1a8e8bd63dd4c811bb85c752b6be3f2fe6226b839`.
Independent verification checks the original partition, ExeFS entries and
container hashes, selected code, and every other container byte. Exactly 109
bytes differ: 45 replacement bytes and 64 required hash bytes. Assets, modules,
extended header, and all other regions remain original.

Sequential Azahar CLI/RPC runs reach language selection with English highlighted
in both variants. The probe now reads the 36-byte BSS body/literal range at
`0x00100024` plus eight preserved startup-literal bytes, alongside the 34-byte
constructor. All loaded bytes match their selected images; the two preserved
startup literals agree across variants. The comparator checks both startup
readbacks and rendered-frame integrity. Four source-owned startup-evidence
regressions raise the repository suite to 31 passing tests.

An initial original frame caught the opening ocean animation. Its prematurely
recorded language-selection label is invalid and has a private correction note.
Only the later settled original frame supports the checkpoint comparison.
No input movie or controller input was used, and no gameplay progression is
claimed. Startup readbacks prove loading; routine execution counts remain
unverified. Both test processes were stopped after evidence collection.

For combined-build reproduction, pass its main-build directory to the package
tool, its `out/code.bin` to the rebuilt RPC probe, and use newly captured original
and rebuilt RPC evidence with the comparator. Historical constructor-only
evidence remains supported. New startup evidence must be paired; mixing old
constructor-only observations with a new startup readback is rejected.

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

Azahar's API supplies live-byte proof and rendered-frame observation. Supported
input-movie replay now supplies the reproducible first gameplay path above;
controller input is not exposed by the shipped RPC client. The result does
not establish complete game compatibility.

The bounded gameplay acceptance in #19 is met. Phase/roadmap closure remains a
separate scope review. Exact compiler matching remains separate in #15.
