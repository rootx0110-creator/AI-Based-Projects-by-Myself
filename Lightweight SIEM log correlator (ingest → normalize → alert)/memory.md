# Memory — Lightweight SIEM Log Correlator

## Project Purpose
A lightweight, runnable SIEM log correlator demonstrating the full pipeline:
**Ingest → Normalize → Correlate → Alert**, with a polished web UI and one-click **HTML report download**.

## Current Status
- ✅ Architecture defined & documented (`architecture.md`)
- ✅ Flask backend skeleton with all 5 pipeline stages
- ✅ In-memory store with JSON snapshot persistence
- ✅ Sample log generator (realistic SOC-style data)
- ✅ Correlation engine with sliding time windows + rules
- ✅ Alert lifecycle (open / ack / close)
- ✅ Dark-themed web UI (dashboard, logs, alerts, correlation views)
- ✅ Standalone HTML report export
- ✅ Ingest API + file upload
- 🚧 (Pending) optional CSV export, syslog UDP listener

## Key Implementation Notes
- Frontend polls backend every 2 s for live updates (no websockets needed).
- Event hash is derived from normalized fields for dedup.
- Snapshots written to `state.json` on every mutating call (cheap for a demo).
- Rule set lives in `correlator/correlator.py` under `DEFAULT_RULES` — easy to extend.
- Report generated server-side with inline CSS so it opens in any browser offline.

## Command Reference

| Action | Command |
|---|---|
| Install deps | `pip install -r requirements.txt` |
| Run server | `python app.py` (defaults to 127.0.0.1:5000) |
| Port override | `python app.py --port 8080` |
| Load sample data | open UI → "Generate Sample Logs" or `python -m correlator.samples --push` |
| Reset state | delete `state.json` and restart, or use UI "Reset" |
| View report | Dashboard → "Download HTML Report" |

## Gotchas
- Windows paths in this repo contain `→` characters — always quote paths in PowerShell.
- The app binds to `127.0.0.1` by default for safety; pass `--host 0.0.0.0` to expose on LAN.
- Keep logs under a few thousand events for the demo; JSON snapshot writes are sync.

## Rule Cheat-Sheet (in correlator.py)
- `brute_force`: ≥5 `ssh_failed` / `login_failed` from one src_ip in window.
- `port_scan`: ≥10 distinct dst_ports from one src_ip in window.
- `data_exfil`: `outbound` + high bytes from one src_ip.
- `escalation`: medium event → high event from same actor within window.