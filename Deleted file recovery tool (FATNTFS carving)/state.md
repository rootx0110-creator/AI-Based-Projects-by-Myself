# Project State

## Status: COMPLETE (v2.1)

Everything is implemented, tested, and packaged as a Windows executable.

## UI (v2.1)
- Light theme (background #f3f5f9, white panels, dark text)
- Custom top tab bar: five equal-width tab buttons spanning the full window
  width; selected tab highlighted with the accent color, replaces the
  default CTkTabview segmented control which rendered oddly in v6

## What works
- [x] Drive enumeration: logical volumes, physical disks, raw paths
- [x] Boot-sector detection: NTFS, FAT12/16/32 (and exFAT detection)
- [x] FAT deleted-file scanning (deleted directory entries, 0xE5 marker)
- [x] FAT chain recovery (cluster-walk byte extraction)
- [x] NTFS `$MFT` mining for non-in-use records
- [x] NTFS resident + non-resident (data-run) DATA recovery
- [x] Raw signature carving for ~50 file types with per-type footer logic
- [x] Beautiful dark tabbed UI (Disks / Scan / Results / Recovery / Report)
- [x] Search + filter in Results
- [x] Bulk recovery with progress bar, Select All / Clear
- [x] HTML report generation (summary cards, FS metadata, type bars, file list)
- [x] Report download (Save As) and open-in-browser
- [x] PyInstaller one-file EXE build (`dist\DeletedFileRecovery.exe`)
- [x] `build.bat` one-command rebuild
- [x] Automated unit-style tests for FAT, NTFS, and carver

## Known limitations
- Raw disk access requires **Run as administrator**. Without elevation the
  tool enumerates drives but raw scanning reports an access error.
- Scan speed for raw carving on large disks is limited by raw sector IO;
  the filesystem pass is fast, raw carving is optional via scan modes.
- Recovering a deleted file is best-effort: clusters re-used after deletion
  produce partial/corrupt output.
- exFAT deep parsing is not implemented (filesystem is detected, raw carving
  can still run).

## Build output
- `dist\DeletedFileRecovery.exe` — single-file, windowed (no console).

## Next steps (future ideas, not required)
- [ ] Add exFAT BPB/upcase-table parsing for deleted $FAT entries
- [ ] Multi-thread raw carving using per-band reader threads
- [ ] Preview / thumbnails for carved images in the UI
- [ ] Export report to CSV alongside HTML
- [ ] Localized UI strings