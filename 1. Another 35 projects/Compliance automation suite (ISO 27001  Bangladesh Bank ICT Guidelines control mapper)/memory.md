# Memory — Compliance Automation Suite

Project context for future sessions.

## What this project is
- **Compliance Automation Suite**: local web app (+ EXE) to assess, map and
  report security controls across **ISO/IEC 27001:2022 Annex A (93 controls)**,
  **Bangladesh Bank ICT Security Guideline v2.0 (18 domains, B-01…B-18)** and
  **NIST CSF 2.0 (22 categories)**.
- Built for banks/NBFIs in Bangladesh preparing for BB ICT audits and ISO
  certification; also useful as a generic CSF control mapper.

## Environment
- Windows, Python 3.14 available at `C:\Python314\python.exe` (also 3.10, 3.13).
- Workspace was empty at project creation (2026-09-22); project lives at repo root.
- No git commits made yet besides the initial repo state.

## Technical decisions (and why)
- **Python stdlib only** (`http.server`, `json`, `html`) — no pip deps, so
  PyInstaller produces a lean single EXE and nothing breaks in restricted
  bank environments.
- **Vanilla JS/CSS SPA** in `app/web/` — no node, no build step, dark theme.
- **JSON file storage** with atomic writes (`.tmp` + `os.replace`) and a
  bounded audit log; corrupt file falls back to `.bak` + clean state.
- **Crosswalk bridge**: BB ICT domains are the hub; ISO↔NIST mapping goes
  through the BB domains (`BBICT_TO_ISO`, `BBICT_TO_NIST` in `app/data.py`).
- **Scoring**: Implemented 1.0 / Partial 0.5 / Planned 0.25 / NotImpl 0;
  N/A excluded from denominator; maturity L1–L5; gap risk up to 10.0 with
  +15% boost for Technological controls.
- **Report**: fully self-contained inline-CSS HTML (no JS/CDN) — safe for
  offline auditors, downloadable from `/api/report` or the UI buttons.

## Gotchas learned
- `write_file` tool on this setup requires all of `path`, `instructions`,
  `content` parameters at once.
- Windows: use POSIX commands in bash (`mv`, `rm`, forward slashes).
- PyInstaller on 3.14: keep `--onefile` + `--add-data "app/web;app/web"`
  (semicolon on Windows); data dir switches to `%APPDATA%/ComplianceSuite`
  via `sys.frozen` check in `app/config.py`.

## Where things live
- Backend: `app/server.py`, `app/services.py`, `app/report.py`, `app/store.py`,
  `app/data.py`, `app/config.py`
- Frontend: `app/web/index.html`, `app/web/app.css`, `app/web/app.js`
- Entries: `run.py` (dev), `exe_start.py` (EXE), `build_exe.ps1` (build)
- Docs: `architecture.md`, `readme.txt`, `state.md`, `todo.txt`, this file
- Runtime data: `data/compliance_data.json` (dev), `%APPDATA%/ComplianceSuite/` (EXE)
