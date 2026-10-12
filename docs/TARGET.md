# Initial Ultra Sun analysis target

The pilot uses the supplied **base version 0** executable. The update remains a separate comparison input; it has not been applied to the base image. The supplied filename labels the base USA; that is not independent verification of region behavior.

## Header observations

| Field | Base | Update |
| --- | --- | --- |
| Container | NCSD `.3ds` | CIA containing NCCH |
| Title ID | `00040000001b5000` | `0004000e001b5000` |
| Product code | `CTR-P-A2AA` | `CTR-U-A2AA` |
| Stored title version | 0 | 2080 (`0x0820`) |
| Filename version label | Base | v1.2 |
| Code-set name | `momiji` | `momiji` |
| Text address | `0x00100000` | `0x00100000` |
| Text logical size | `0x004b99f0` | `0x004bb818` |
| Read-only address | `0x005ba000` | `0x005bc000` |
| Data address | `0x00667000` | `0x00669000` |
| Data logical size | `0x0003cd48` | `0x0003cd88` |
| BSS size | `0x000301bc` | `0x000301bc` |

CTRTool renders the update version as `2.2.0 (2080)`. Record the stored integer and the filename's v1.2 label separately; do not equate the tool's version rendering with the marketing version.

## SHA-256 identities

| Local input | SHA-256 |
| --- | --- |
| Base container | `3bb3b4eb0d17f18875d8b847c871dc97a172beeda03ce99e59e62a78ed5c1a53` |
| Update container | `16d2a3409c05c315edbd70e82192bcb3d56be8ad7f979a6d5560e7d87e859a93` |
| Base extracted code | `b5388f7500d91be01499a99ca007c98212068608ed7c83c43952e1d5148e9e09` |
| Update extracted code | `421774f2e5e2076b4b09a6f761b2826a99f01900c23655f8588fcd25ce16200f` |

These identify the supplied local dumps, not every Ultra Sun copy or decrypted container.

## Coverage

The initial import proof covers a bounded startup function in base code. Complete initialized segment mappings have been inspected separately. RomFS, dynamically loaded modules, compiler identity, emulator/hardware gameplay baseline, and complete-game reconstruction remain future work.
