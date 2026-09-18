# NetPulse — Bandwidth Monitor & Traffic Visualizer

NetPulse is a Windows desktop dashboard that shows your live network traffic,
per-process breakdowns and historical usage — in one polished, dark-mode-first
UI.

![status](https://img.shields.io/badge/status-v1.0-blue) ![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey) ![license](https://img.shields.io/badge/license-MIT-green)

## Features

- **Live dashboard** — 60-second rolling down/up graph, animated speed gauge vs. link capacity, sparkline cards, top-process donut, 24-hour heatmap
- **Per-process breakdown** — top-25 processes by bandwidth with per-connection drill-down (remote IP:port, state)
- **Interfaces** — per-adapter live chart, state/link/IPv4/MTU table
- **History** — hourly/daily/monthly rollups from SQLite, top talkers, CSV/JSON export
- **Report** — one-click self-contained HTML report (summary cards, SVG charts, top talkers, raw samples) — save it or preview it in your browser
- **Alerts** — sustained-speed threshold, quota warn/crit/exceeded, watched-process new-connection alerts (toast + tray balloon)
- **System tray** — mini-speed tooltip, show/hide, HUD toggle, quit
- **Floating HUD** — draggable always-on-top mini widget
- **Dark/light theme**, config in `%APPDATA%\NetPulse\config.json`, single-instance lock, graceful shutdown

## Quick start (3 commands)

```bat
git clone <this-repo> netpulse && cd netpulse
build.bat
dist\NetPulse.exe --demo
```

1. `build.bat` creates `.venv`, installs requirements, generates `assets/icon.ico`, and runs PyInstaller.
2. `dist\NetPulse.exe` — double-click for live capture, or run with `--demo` for synthetic traffic.
3. Look for the NetPulse tray icon; left-click it to show/hide the dashboard.

Run from source instead:

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python src\main.py
```

## Hotkeys & interactions

| Where | Action |
|---|---|
| Dashboard | Live graphs update at 10 FPS; gauge animates |
| HUD | Drag to move · double-click to hide · tray ▸ Toggle HUD |
| Tray icon | Left-click show/hide · right-click menu |
| Processes | Click a row → connection drill-down on the right |
| History | Pick range/granularity → Refresh · Export CSV/JSON |
| Settings | Edit + Save (some fields apply live, others after restart) |
| Main window ✕ | Minimizes to tray (configurable); tray ▸ Quit exits |

## Screenshots

Run `dist\NetPulse.exe --demo` to see the dashboard populated with synthetic
traffic (or `python scripts\seed_demo_db.py` to fill the History tab with a
week of data).

## Data & privacy

- Everything stays local: `%APPDATA%\NetPulse\` (config, `netpulse.db`, logs, exports)
- No telemetry, no network calls beyond reading OS counters

## Admin rights (optional)

Without elevation, per-process connection listing can be limited on some
Windows builds; interface traffic works fine either way. To elevate at launch,
uncomment the `trustInfo` block in `assets/netpulse.manifest` and rebuild with
`uac_admin=True` in `build.spec`.

## License

MIT — see below.

```
MIT License. Copyright (c) 2026 NetPulse contributors.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright
notice and this permission notice shall be included in all copies or substantial
portions of the SOFTWARE. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
ANY KIND, EXPRESS OR IMPLIED.
```
