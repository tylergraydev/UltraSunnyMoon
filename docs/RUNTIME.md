# Runtime comparison preparation

The original and rebuilt Ultra Sun base applications are packaged locally
as decrypted standalone CXIs. Both pass container and payload verification.
**No original-game or rebuilt-game execution has been observed yet.**
The runtime comparison remains open in
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
either runtime. No measured runtime configuration is recorded yet.

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

## Remaining execution gate

Automatic approval review rejected the attempted Azahar window launch:
“Computer Use was not approved to use azahar.” The user explicitly approved
the original/rebuilt comparison, but the subsequent launch received the
same rejection and Azahar was absent from the Computer Use app inventory.
Session-level app access remains unavailable. No launch through another
method was attempted after that rejection.

Once Azahar access is approved, launch the original CXI in its fresh
profile, record actual version/configuration and any startup requirements,
and observe the first reproducible in-game path. Then repeat with the
rebuilt CXI under equivalent initial conditions. Record screenshots/logs
locally and compare observations. A package verification pass or the prior
isolated helper tests do not establish game compatibility.

Phase four remains open until a working rebuilt-game comparison is
observed. Exact compiler matching remains separate in #15.
