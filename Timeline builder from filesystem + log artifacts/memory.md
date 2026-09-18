# Project Memory

## Purpose
Timeline Builder: reconstruct a chronological timeline from filesystem
metadata + timestamped log artifacts, export as HTML report.

## Timeline / decisions
- 2026-09-17  Project scaffolded from scratch. Chose Python +
  CustomTkinter + PyInstaller over Electron/PySide because it yields a
  small single-file EXE with a modern look and no oversized runtime.
  Dependencies already present: customtkinter 6.0.0, pyinstaller 6.22.2,
  pillow, Python 3.14.7 (tkinter 9.0).
- 2026-09-17  Timestamp politics: normalise all parsed stamps to local
  naive time so sorting/display is consistent; timezone-aware input is
  converted via astimezone().
- 2026-09-17  Event model is flat (`ts,type,source,label,path,details,
  size`) so GUI, CSV and HTML share one shape; the HTML report carries
  the same shape as a JSON payload.
- 2026-09-17  Log reads are bounded (2MB / 100k lines per file) and
  skip non-text snapshots to keep scans usable.

## Gotchas
- Windows `st_ctime` is creation time (unlike POSIX).
- CustomTkinter has no table widget; use ttk.Treeview restyled per
  appearance mode.
- JSON payload inside <script> must escape "</" -> "<\/".
- PyInstaller onefile: keep all imports at module top-level to avoid
  hidden-import surprises.