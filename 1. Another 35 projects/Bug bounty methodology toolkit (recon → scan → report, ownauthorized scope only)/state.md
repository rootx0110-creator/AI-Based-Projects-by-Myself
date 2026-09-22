# State — Bug Bounty Methodology Toolkit

Snapshot of project + runtime state. Update after major milestones.

## Build state

| Item | Status | Notes |
|---|---|---|
| Project docs (architecture / memory / state / todo / readme) | DONE | Root of project directory |
| Backend `app.py` (server, scope engine, gate, pipeline, report) | DONE | Python 3 stdlib only, port 8765 |
| Frontend SPA (`static/`) | DONE | 5 tabs: Scope, Pipeline, Findings, Report, Toolkit |
| Scope engine (domain / wildcard / ip / cidr / url) | DONE | Out-of-scope always wins |
| Authorization gate | DONE | 403 until attestation confirmed |
| Recon pipeline (8 stages, threaded worker) | DONE | Passive checks only, rate-limited |
| Findings engine (severity-ranked) | DONE | ids F-001… |
| HTML report + download | DONE | `GET /api/report/download` |
| Live status/log polling | DONE | `/api/recon/status` every ~800 ms |
| Command cookbook (external tools, scoped) | DONE | Copy-only templates |
| Exe packaging (`build_exe.bat` + PyInstaller) | DONE | `dist\BBMToolkit.exe` built (9.3 MB) and verified standalone on port 8811 |
| End-to-end smoke test | DONE | localhost URL target + live example.com target verified; report download tested |

## Runtime state (defaults)

- **Data file:** `data/state.json`
  - `authorization.confirmed = false` on first boot (gate closed)
  - `scope = []`, `findings = []`, `runs = []`, `recon_data = {}`
- **Reports directory:** `reports/` — timestamped HTML files accumulate; safe to delete.
- **Server:** binds `127.0.0.1:8765` by default (local-only; not exposed to LAN unless `--host` given).
- **Run states:** `idle → running → done | cancelled | error` (held in memory at `RUNTIME`, mirrored into `state.json` runs on completion).

## Last verified
- Smoke test: scope `127.0.0.1` + `localhost` → attestation → full 8-stage run → findings generated → HTML report downloaded with `Content-Disposition` attachment header.
