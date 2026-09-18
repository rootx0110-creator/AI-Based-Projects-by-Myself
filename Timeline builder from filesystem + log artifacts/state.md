# Project State

## Status
Core scanning, log parsing, HTML/CSV export and GUI are implemented and
verified. A single-file EXE is produced with PyInstaller.

## Done
- Filesystem scanning (created / modified / accessed, size) incl.
  long-path support on Windows.
- Log artifact timestamp parsing across common formats.
- Timeline merge + sort + filtering (event type, date range, query).
- CustomTkinter GUI with theme toggle, metrics, table, detail pane,
  progress, HTML + CSV export.
- Self-contained HTML report (charts, search, sort, pagination, print).
- CLI mode (`--cli`) for headless scan/report.
- PyInstaller single-file build (dist/TimelineBuilder.exe).

## Verified
- CLI scan + report generation on a fixture tree with synthetic logs.
- GUI launches on Python 3.14 / tkinter 9.0 / CustomTkinter 6.0.
- HTML report renders in a browser; search/sort/filter/pagination work.

## Known limitations
- Log parsing is text-based; binary formats (.evtx) only surface the
  file itself, not internal records.
- Scanning is single-threaded (bounded log reads); very large trees
  take proportionally long.
- Access events can add noise and are toggleable at scan time.