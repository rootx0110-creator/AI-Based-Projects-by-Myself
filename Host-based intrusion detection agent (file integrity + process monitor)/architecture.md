# HIDS Agent — Architecture

Host-based Intrusion Detection System: **File Integrity Monitoring (FIM)** +
**Process Monitoring**, packaged as a single Windows EXE with a desktop GUI.

## 1. High-level view

```
                 ┌─────────────────────────────────────────────┐
                 │                 UI (Tk)                     │
                 │  Dashboard · FIM · Processes · Alerts ·     │
                 │  Reports · Settings  (app/ui/*.py)          │
                 └───────────────▲─────────────────────────────┘
                                 │ polls state + storage (1 s tick)
                 ┌───────────────┴─────────────────────────────┐
                 │              HIDSAgent (app/agent.py)       │
                 │   daemon worker thread → detection passes   │
                 └───────▲──────────────────────▲──────────────┘
                         │                      │
              ┌──────────┴─────────┐  ┌─────────┴──────────────┐
              │   FIMEngine        │  │  ProcessEngine         │
              │   baseline + scan  │  │  snapshot / whitelist  │
              │   (app/fim.py)     │  │  (app/process_monitor) │
              └──────────┬─────────┘  └──────────┬─────────────┘
                         │                       │
                         ▼                       ▼
        ┌──────────────────────────────────────────────────────┐
        │               Storage (SQLite, app/storage.py)       │
        │   files_baseline · process_baseline · alerts · cfg   │
        └───────────────▲──────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐    ┌─────────────────┐
        │  Reporter (app/reporter.py)   │    │ Report UI       │
        │  HTML / JSON / TXT / CSV      │───▶│ (reports_view)  │
        └───────────────────────────────┘    └─────────────────┘
```

## 2. Threat model & detection rules

| Module   | Rule                                       | Severity |
|----------|--------------------------------------------|----------|
| FIM      | File added to a watched directory          | Warning  |
| FIM      | Existing file hash/size changed            | Warning  |
| FIM      | File removed from a watched directory      | Critical |
| Process  | New process not in whitelist               | Warning  |
| Process  | CPU usage above threshold                  | Warning  |
| Process  | Memory usage above threshold               | Warning  |
| Agent    | Baseline created / internal error          | Info     |

Alert severities: `1 = Info`, `2 = Warning`, `3 = Critical`.
A whitelist is auto-learned from the running process set on the first pass and
re-built every pass, so new-process alerts fire once and do not repeat; resource
hogs are de-duplicated per PID so they do not spam every cycle.

## 3. Components

### `app/config.py`
Loads/saves `config.json` in `%LOCALAPPDATA%\HIDS_Agent` (or `~/.hids_agent` on
POSIX). Defaults are merged over stored values so new keys never break old files.

### `app/storage.py`
Single SQLite connection guarded by an `RLock` (threads: UI + worker). Tables:

- `files_baseline(path, rel_path, file_hash, size, mtime, added_at)` — FIM manifest.
  Primary key `(path, rel_path)`, so the whole manifest can be rebuilt per directory.
- `process_baseline(key, name, exe, first_seen)` — whitelist. `key` is `exe:<path>`
  when the executable is known, else `name:<name>`.
- `alerts(id, ts, severity, source, title, detail, status)` — security event log,
  `status` is `open` or `acked`.

### `app/fim.py`
- `hash_file` streams 1 MiB chunks; files over `max_file_size_mb` are skipped.
- `build_baseline(path)` walks a directory, clears its manifest in SQLite and
  re-inserts every file → O(n) hashes, intended for cold start.
- `scan(path)` walks again and diffs against the manifest using a single
  `{rel_path: row}` dict for O(1) lookups, classifying `added`, `modified`,
  `removed`, `unchanged`. Progress callbacks are threadsafe-friendly (pushed to
  the UI via `widget.after`).

### `app/process_monitor.py`
Wraps `psutil.process_iter` (`pid, name, username, cpu_percent, memory_info, exe,
create_time, status`). `snapshot()` tolerates `NoSuchProcess` / `AccessDenied`.

### `app/alerts.py`
`AlertBus` persists to storage and fans out to in-process listeners.
`SEVERITIES/ALERT_COLORS` centralise labels/colour mapping used by the UI.

### `app/agent.py`
Orchestrator with a single daemon thread `_worker`:

1. If a watched dir has no baseline → build one (alert Info).
2. Else scan → alert per drift, plus one summary line.
3. Snapshot processes → alert new ones (first pass only builds whitelist), alert
   resource hogs (de-duplicated), refresh whitelist.
4. FIM and process modules run on **independent intervals** — the loop wakes to
   whichever is due next (min granularity 3 s), and manual scan/snapshot
   requests are `threading.Event`s that shortcut the sleep loop.

Key invariants:

- `self.config` is one mutable dict shared by `FIMEngine`/`ProcessEngine`.
  `save_settings`/`reload_settings` clear-and-update it **in place** so hash
  algorithm, thresholds and file-size caps apply immediately, without a restart.
- Manual events for a disabled module are dropped by the worker (busy-spin guard).
- `_hog_state`/`_known_new` de-duplicate resource and new-process alerts across
  cycles; `reset_process_state()` clears them after the user rebuilds the
  whitelist manually.
- `paused` flag halts detection without killing the thread; `toggle_pause()`.

`paused` flag, live status dicts (`last_scan`, `last_snapshot`, `progress`) are
shared with the UI and safe under the GIL.

### `app/reporter.py`
Pure-data report generator, no Tk dependency. `system_info()` collects host +
agent snapshot; then:

- `build_html()` — self-contained, dark-styled report with system stats, alert
  summary by severity, watched dirs, recent events and top processes.
- `build_json_str()` — structured JSON for machine consumption.
- `build_txt()` — plain-text console-style report.
- `build_csv_rows()` — alert log as CSV rows (header + data) for the log export.

### `app/ui/`
`customtkinter` 6.0 dark theme. One `CTkFrame` view per screen, swapped by the
root `HIDSUI._show`. A 1 s `after()` tick refreshes the active view and status
bar. `ProcessView` throttles its psutil snapshot to every 4 s. Long FIM jobs and
report generation run in background threads and post results through
`widget.after(0, …)` so the UI never blocks.

## 4. Threading rules

- Exactly one agent worker thread + short-lived FIM job threads + UI main thread.
- SQLite is the only shared mutable state besides a few GIL-protected dicts.
- Never touch Tk widgets off the main thread — always `after(0, …)`.
- `Storage` uses `check_same_thread=False` + explicit locking because both the
  worker and UI threads query it.

## 5. Build & packaging

One-file, windowed EXE produced with PyInstaller (see `scripts/build_exe.ps1`):

```
pyinstaller --noconfirm --onefile --windowed --name HIDS_Agent  ^
    --icon assets/icon.ico --add-data "assets/icon.png;assets" main.py
```

Runtime data lives outside the bundle in `%LOCALAPPDATA%\HIDS_Agent` so upgrades
of the EXE never wipe baselines or the alert history.

## 6. Repository layout

```
main.py                 entry point (GUI, or app/ui.app run)
app/{__init__,config,storage,alerts,fim,
     process_monitor,agent,reporter}.py
app/ui/{app,theme,widgets,dashboard,fim_view,
        process_view,alerts_view,reports_view,settings_view}.py
scripts/build_exe.ps1   PyInstaller build driver
assets/icon.ico         EXE icon
architecture.md state.md memory.md
```