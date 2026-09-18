# Memory — Disk Image Acquisition & Hashing Toolkit

> Persistent working memory for autonomous coding sessions and future maintainers.
> Read first at the start of any session. Update at the end of significant work.

## Project Identity

- **Name:** Disk Image Acquisition & Hashing Toolkit (Chain of Custody Automation)
- **Goal:** Local Windows EXE for forensic disk imaging, live hashing, and automated chain-of-custody documentation.
- **Deliverable:** A single windowed EXE plus this memory set (`architecture.md`, `state.md`, `memory.md`).

## Hard Constraints & Conventions

- **Offline-only.** No network calls, ever. Evidence-grade tools must not phone home.
- **Windows-native paths.** Real paths use `\\.\PhysicalDriveN` for raw access. Imaging must open source read-only.
- **Timestamps stored in UTC** with ISO-8601 string form; local time shown in UI.
- **Append-only custody log.** Never mutate/delete entries; new entries chain to the previous HMAC.
- **Hashing is streaming.** Never load whole images into RAM; chunked reads (1 MiB blocks) with a progress callback.
- **Atomic writes.** JSON state written to temp file then `os.replace()` so a crash never corrupts the registry.
- **Portable data dir.** When frozen, state lives in `data/` beside the EXE so the tool runs from a USB stick.
- **No comments in code unless required** by the repo's convention; keep code self-documenting with clear names.

## Tech Decisions (locked)

- GUI: **CustomTkinter** (dark theme). NOT Electron / webview (keeps single-file EXE small and native).
- Hashing: stdlib `hashlib`. Imaging: raw streaming; folder→ STORE zip.
- Persistence: JSON (`cases.json`, `custody.json`). No SQLite (audit files should remain human-greppable).
- Packaging: **PyInstaller** `--noconsole --onefile` (single EXE) with `--collect-all customtkinter`.

## Gotchas Log

1. Python 3.14 + PyInstaller: ensure PyInstaller ≥ 6.x for 3.14 support; collect CustomTkinter theme/assets explicitly.
2. Physical drive listing on Windows: use PowerShell `Get-CimInstance Win32_DiskDrive` via subprocess (not ctypes) for portability.
3. tkinter must run its loop on the main thread → background threads post progress via `widget.after()` polling of a `queue.Queue`.
4. When frozen, `sys.executable` directory must be used for the data folder (not `__file__` inside the bundle).

## Open Questions

- Should the tool add E01 (Expert Witness) container writing? (Deferred; `dd` + hash set is court-acceptable and simpler.)
- Should reports support one-tap PGP signing? (Nice-to-have; parked.)

## Next-Session Checklist

- [ ] Re-read `state.md` for pending items.
- [ ] Re-run `build.py` if any source changed.
- [ ] Re-smoke-test the EXE after any UI change.