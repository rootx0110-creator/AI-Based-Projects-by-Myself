# State — Lightweight SIEM Log Correlator

## Session Log

| Date | What happened | Outcome |
|---|---|---|
| 2026-09-13 | Project scaffold created: docs, package layout, Flask app design | Directory structure + architecture/memory/state docs in place |
| 2026-09-13 | Full pipeline implemented, tested end-to-end, server verified | 213 events → 24 correlations → 24 alerts in load test; report HTML verified (13KB); runs on 127.0.0.1:5000 PID 8880 |

## Current Build State
- **Runtime:** Flask dev server, Python 3.8+ (stdlib + Flask) — verified on Python 3.14.7 / Flask 3.1.3
- **Persistence:** `state.json` snapshot (logs, events, alerts, stats kept in memory)
- **Backend modules:** `app.py`, `correlator/ingest.py`, `normalizer.py`, `correlator.py`, `alerter.py`, `store.py`, `samples.py`
- **Frontend:** single-page `templates/index.html` + `static/css/style.css` + `static/js/app.js`
- **Views:** Dashboard, Live Logs, Events (normalized), Correlations, Alerts, Rules
- **Report:** standalone HTML with inline CSS (client-initiated, server-rendered) — exports KPIs, severity chart, hourly volume, top sources/types, analyst insight, alerts table
- **Status:** server currently running and serving (PID 8880 on 127.0.0.1:5000)

## Open Items / Next Steps
1. Wire the alert acknowledgement + close actions into the UI and store.
2. Add a UDP/TCP syslog listener ingest mode.
3. Add CSV export for events/alerts alongside the HTML report.
4. Consider shipping as a packaged `.exe` via PyInstaller for users without Python.
5. Add unit tests for normalizer regexes and correlation window logic.

## Decisions Log (TBD while building)
- Report format: **HTML** (single-file, no dependencies) — per user requirement.
- Correlation model: rule-based temporal windows (deterministic, explainable), not ML.
- Storage: in-memory + JSON snapshot (lightweight; not a full DB).