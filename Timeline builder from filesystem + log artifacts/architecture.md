# Timeline Builder — Architecture

## Overview
Timeline Builder is a Windows desktop tool (packaged as a single EXE)
that reconstructs a chronological event timeline from a folder's
filesystem metadata and timestamped log artifacts, and exports the
result as a self-contained HTML report.

## Layers

```
main.py (entry)
   |-- timeline_app.py    GUI (CustomTkinter)
   |      |-- timeline_core.py     scanning + parsing + timeline engine
   |      `-- timeline_report.py   HTML report generation
   `-- CLI mode: arg parse -> timeline_core -> timeline_report
```

### timeline_core.py
- `Scanner` — walks the tree with `os.walk` (uses the `\\?\` prefix on
  Windows for long paths), collects `created / modified / accessed`
  events (ntime/mtime/atime, `st_ctime` = creation on Windows) and
  `size` per path.
- Log artifact parser — for `.log`, `.txt`, `.jsonl` files reads the
  first ~2 MB / 100k lines and matches timestamp patterns:
  - ISO 8601 (`YYYY-MM-DD[T ]HH:MM:SS[.fff][Z|+-HH:MM]`)
  - `MM/DD/YYYY HH:MM:SS`
  - `DD.MM.YYYY HH:MM:SS` / `YYYY/MM/DD`
  - RFC 2822 English dates
  - epoch seconds / millis / micros (range validated)
  Timezone-aware stamps are normalised to local (naive) time so all
  events sort on one axis.
- `TimelineEvent` — normalised record: `ts, type, source, label, path,
  details, size`.
- `build_timeline(events)` — sort by epoch-millis, attach rank/index.
- `filter_events(...)` — filter by event types, date range, text query.
- `scan_folder(root, progress) -> (events, stats)` — single entry.

### timeline_report.py
- `build_html_report(events, stats, root, options) -> str` generates a
  fully self-contained HTML document (inline CSS + JS, no external
  assets): header metrics, per-bucket frequency bar chart and type
  legend, searchable / sortable / paginated event table, row-detail
  viewer and a browser print stylesheet.
- Data is embedded as a JSON payload (`window.__DATA__`) and rendered
  client-side; `</` is escaped to keep the payload XSS-stable.

### timeline_app.py
- CustomTkinter single-window app: toolbar (folder picker + scan),
  metric cards, filter bar, ttk.Treeview table, detail pane,
  progress bar, HTML/CSV export.
- Scanning runs on a worker thread; results are marshalled back via
  `widget.after(...)`. The Treeview is restyled on theme switch.

## Key decisions
- Pure-Python + stdlib tkinter with CustomTkinter cosmetics: no heavy
  runtime deps, tiny EXE.
- Log parsing is bounded (2 MB / 100k lines per file) for speed.
- Report is self-contained so it can be shared/archived without a
  server.