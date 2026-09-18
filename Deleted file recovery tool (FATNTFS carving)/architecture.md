# Architecture

## Overview
Deleted File Recovery Tool is a Windows desktop application (built with
Python + customtkinter) that recovers deleted files from FAT12/16/32 and NTFS
volumes using two complementary strategies: **filesystem metadata analysis**
and **raw file carving**.

```
main.py
  └── App (app/ui/main_window.py)          # CustomTkinter window, 5 tabs
        ├── Disks                                # drive enumeration + selection
        ├── Scan                                 # scan configuration + live progress
        ├── Results                              # searchable/filterable result table
        ├── Recovery                             # select files -> recover to folder
        └── Report                               # HTML report generation/download

app/core                                        # engine layer (no UI dependencies)
  ├── disk_reader.py                            # low-level raw disk access via ctypes
  ├── scan_engine.py                            # orchestration, threading, progress
  ├── fat_parser.py                             # FAT12/16/32 directory+FAT analysis
  ├── ntfs_parser.py                            # $MFT record mining for deleted files
  ├── file_carver.py                            # signature-based raw carving
  └── recovery.py                               # byte extraction to disk
app/utils
  ├── file_types.py                             # magic-byte signature database
  └── report.py                                 # HTML report renderer
app/ui
  ├── theme.py                                  # colors, fonts, app constants
  └── main_window.py                            # App window and all tabs
tests
  ├── test_fat.py                               # synthetic FAT12 image test
  ├── test_ntfs.py                              # synthetic NTFS $MFT test
  └── test_carver.py                            # in-memory carving test
```

## Data flow

1. **Drive selection**: `get_logical_drives()` (Win32 API via ctypes) lists
   logical volumes with size, filesystem hints and volume label, and
   `get_physical_disks()` enumerates physical drives. Raw access requires
   Administrator rights.
2. **Scanning**: `ScanEngine` runs in a background thread and calls
   `detect_bootsector()` to identify the filesystem:
   - `FAT*`: `FATScanner` walks the root directory (and FAT32 cluster chains),
     decodes 32-byte directory entries, and harvests entries whose first name
     byte is `0xE5` (deleted marker). The start cluster and size are retained
     for recovery.
   - `NTFS`: `NtfsAsminer` walks `$MFT` records at the LCN from the boot
     sector, parses `FILE_NAME` (0x30) and `DATA` (0x80) attributes (resident
     and non-resident with data-runs) and collects records whose in-use flag
     is clear.
   - Raw carving (optional, or on any volume): `RawCarver` streams the device
     in 2 MB chunks, overlapping chunk boundaries by 64 bytes, and matches a
     set of magic-byte signatures. Footers and sizes are inferred per format
     (JFIF `FF D9`, PNG `IEND`, PDF `%%EOF`, ZIP EOCD `PK\x05\x06`, RIFF chunk
     sizes, MP3 frame sync, etc).
3. **Recovery**: `RecoveryEngine` re-reads the physical device and writes the
   recoverable byte range (FAT cluster chain walk, NTFS data-run maps, or raw
   carve extents) to files in a user chosen destination.
4. **Reporting**: `report.py` renders a self-contained HTML document with
   embedded CSS (dark theme), summary cards, filesystem metadata, a
   per-type breakdown with bars, and the full file list. The report opens in
   the browser or can be saved via the Report tab.

## Concurrency model
- The scan runs on a daemon thread (`ScanEngine._thread`).
- Progress/status callbacks marshal back to the UI thread via widget.after().
- Recovery also runs on a daemon thread with per-file progress updates.

## Build & packaging
- `requirements.txt` — customtkinter, pillow, pyinstaller.
- `DeletedFileRecovery.spec` — PyInstaller spec (one-file, windowed, no
  console), collects customtkinter data files and includes the `app` package.
- `build.bat` — builds `dist\DeletedFileRecovery.exe`.

## Security & limitations
- Reading raw volumes requires elevation; without it the tool reports an
  access error for raw scans. Logical-drive listing still works.
- Recovery quality depends on whether deleted clusters were overwritten.
- The RawCarver intentionally ignores tiny (<= 8 KiB) hits to reduce noise.