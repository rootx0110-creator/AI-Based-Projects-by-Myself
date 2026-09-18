# HIDS Agent — Memory (project notes for AI assistants / future agents)

## What this project is

A Windows desktop HIDS: **file integrity monitoring** + **process monitoring**,
packaged as a single EXE. Pure **Python 3.14**, UI is **customtkinter 6.0.0**
(dark), detection uses **psutil** and **sqlite3** (stdlib). No CI, no tests
framework yet — verification is done with throwaway `python -c` scripts.

## Repo map — touch these, not those

| Path | Purpose |
|------|---------|
| `main.py` | Entry point. `--headless` runs the agent without GUI |
| `app/agent.py` | Orchestrator: worker loop, FIM pass, proc pass, live status dicts |
| `app/fim.py` | Streaming hash, `build_baseline`, `scan` → `ScanResult` |
| `app/process_monitor.py` | `snapshot()` (module fn), `ProcessEngine` |
| `app/storage.py` | SQLite wrapper, `RLock`, all SQL lives here |
| `app/alerts.py` | `AlertBus`, severity constants |
| `app/reporter.py` | Report generators: `build_html` / `build_json_str` / `build_txt` / `build_csv_rows`, `system_info` |
| `app/ui/app.py` | Root window `HIDSUI`; nav (6 tabs) + 1 s tick |
| `app/ui/theme.py` | Color map (BG/CARD/ACCENT/OK/WARN/CRIT/…). Add colors here first |
| `app/ui/widgets.py` | `make_tree`, `card`, `stat_card`, `build_btn`, `entry` |
| `app/ui/*_view.py` | One view per tab. Every view implements `refresh()` |
| `scripts/build_exe.ps1` | PyInstaller build |
| `assets/icon.ico` | EXE icon (regenerate: `python scripts/make_icon.py`) |

## Conventions

- **Every view has a `refresh()`** called by the root tick (1 s). Keep it cheap;
  do heavy work in worker threads and publish via `after(0, callback)`.
  `ProcessView.refresh(force=False)` throttles its psutil snapshot to 4 s —
  keep that pattern when adding per-second views.
- **Never touch Tk widgets off the main thread.** FIM jobs and report generation
  run in background threads and return via `self.after(0, …)`.
- **SQL only in `app/storage.py`.** Both UI and worker threads call it, so access
  is locked with an `RLock` (`check_same_thread=False`).
- **Alert severity is an int** (1/2/3). Labels come from `app/alerts.SEVERITIES`
  — import that constant instead of redefining label dicts in views.
- **`HIDSAgent.config` is a single shared dict.** `save_settings`/`reload_settings`
  mutate it **in place** (clear+update) so `FIMEngine`/`ProcessEngine` see change
  immediately. Never rebind `self.config = load_config()` again, or engine
  settings go stale until restart.
- Files over `max_file_size_mb` are skipped during hashing (never flagged).
- No comments in code unless asked (project rule). Keep docstrings short.

## Build & verify commands

```powershell
# dev run (UI)
python main.py

# build EXE
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
# -> dist/HIDS_Agent.exe  (onefile, windowed)

# headless agent (no GUI)
dist/HIDS_Agent.exe --headless
```

Smoke check after any core change:

```python
# syntactics... python -c "import ast; ..."
# agent+reporter:  scripts at C:\Users\ASUS\AppData\Local\Temp\opencode\test_enh.py
# full UI incl. Reports: C:\Users\ASUS\AppData\Local\Temp\opencode\test_ui.py
```

Before building: update `app/config.py APP_VERSION` (sidebar reads it
automatically). Rebuild: `powershell -File scripts/build_exe.ps1`.

## Gotchas (things that will bite again)

1. **customtkinter 6.0 API drift.** Widgets reject unknown kwargs with
   `ValueError: ... are not supported arguments`. Check the signature before
   passing `text_color_active`, `segment_button_selected_hover_color`, etc.
   CTkTabview's segmented-button palette uses `segmented_button_*` keys and
   `text_color` only. ComboBox needs `button_color`/`button_hover_color`.
2. **`_show(name)` takes the view class name** (`"DashboardView"`), not the tab
   label (`"Dashboard"`). Root tab labels live in `HIDSUI.TABS`; new tabs need
   a matching entry in BOTH `TABS` and the `_create_view` mapping.
3. **Combo box test caveat:** programmatic `.set("Critical")` does NOT fire the
   widget's `command` — simulate a user click by calling the handler
   (`view._on_sev("Critical")`) in tests, then the widget-state change to check.
4. **Version-bump**: `app/config.py APP_VERSION`; the UI reads it.
5. **Data dir is shared per-user and persists across EXE rebuilds** —
   `%LOCALAPPDATA%\HIDS_Agent`. For dev tests always patch
   `app.config.DB_PATH` **and** `CONFIG_PATH` to a temp dir first, or you
   pollute the user's real DB/config. `HIDSAgent.add_watch_dir` also SAVES
   config — never let a test dir leak into the real config.json (clean it if it
   does; see test_enh.py incident).
6. **Process keys** are `exe:<lowercased path>` or `name:<name>` fallback —
   keep them lowercased or new-process detection breaks on case.
7. `ProcessEngine.snapshot()` (method) calls the module-level `snapshot()` —
   don't shadow one with the other.
8. Resource/new-process alerts are de-duplicated (`_hog_state`, `_known_new`
   + whitelist refresh each pass). Manual whitelist rebuild must call
   `agent.reset_process_state()`. System Idle Process / pid<=4 are excluded
   from resource alerts.
9. **Worker busy-spin:** an undispatched manual `Event` makes the loop spin.
   `_run_*_pass` clear their event at the START; disabled modules drop it in the
   worker. Don't "fix" that by removing the clears.
10. `stat_card` label order → `_set_card` finds `[label, value, sub]` by child
    order; controls added to a card before values will break it.
11. Reports flow: data generation runs in a background thread, the file write
    happens on the UI thread through an `after(0,…)` callback (keep writes
    short). "Open" uses `os.startfile` (Windows only); guard for missing path.

## State of record

See `state.md` for implemented features, known limitations and roadmap. If a
limitation is fixed, move it out of "Known limitations" into "Implemented".