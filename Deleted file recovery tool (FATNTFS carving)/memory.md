# Memory / Session Notes

## Project context
- Target: Windows 10/11 desktop EXE.
- Primary use case: recover accidentally deleted files from USB sticks (FAT)
  and hard drives / SSDs (NTFS).
- UI style: modern dark theme, tabbed interface, customtkinter.
- Report: self-contained HTML with embedded CSS, opened in browser or saved.

## Key implementation decisions
- **Raw disk I/O** via `CreateFileW("\\.\C:")` + `ReadFile` (ctypes) instead
  of a third-party library — no extra deps, works under elevation.
- **FAT recovery** reads the directory tables (not the FAT bitmap alone) so
  deleted 0xE5 entries recover name, cluster chain and original size.
- **NTFS recovery** mines `$MFT` for non-in-use records; supports both
  resident DATA and non-resident DATA with parsed cluster runs.
- **Raw carving** uses 2 MB streaming chunks with 64-byte overlap to avoid
  missing signatures that straddle a chunk boundary. Signatures come from
  `app/utils/file_types.py`.

## Environment facts (this machine)
- Python 3.14.7 at `C:\Python314`
- customtkinter 6.0.0 installed (user site-packages)
- pyinstaller 6.22.2
- EXE build successful: `dist\DeletedFileRecovery.exe` (~21 MB)

## Verification
| Test | Result |
|------|--------|
| `tests/test_fat.py` (FAT12 deleted entry + cluster chain) | PASS |
| `tests/test_ntfs.py` (deleted MFT record, resident + non-resident) | PASS |
| `tests/test_carver.py` (JPEG/PNG/PDF signature carving) | PASS |
| Frozen EXE launch smoke test | PASS |

## Gotchas
- `pack_into` / `struct` offsets for MFT attributes are relative to the
  attribute header start; the FILE_NAME content offset field lives at
  header+0x14 (not 0x10).
- Deleted FAT entries put `0xE5` in the first name byte; `_clean()` maps it
  to `?` so names remain readable.
- Physical-drive size query requires elevation; logical drives report sizes
  via `GetDiskFreeSpaceExW`.
- 0xE5 bytes inside arbitrary binary blobs will yield false positives in raw
  carving; MIN_CARVE_SIZE (8 KiB) filter mitigates noise.