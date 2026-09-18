# SOAR-Lite — State

Status snapshot of the project. Updated each change batch.

| Area            | Status      | Notes |
|-----------------|-------------|-------|
| Server / REST   | ✅ Implemented | Zero-dependency Node HTTP, JSON API under `/api/*` |
| Playbook engine | ✅ Implemented | 11 step types, decisions, error policies, auto-run matching |
| Storage         | ✅ Implemented | Atomic JSON persistence in `data/soar.json`, seeded first boot |
| GUI (tabs)      | ✅ Implemented | Dashboard, Playbooks, Incidents, Automation, Reports, Docs |
| Reports         | ✅ Implemented | **HTML (primary)** + JSON + Markdown + CSV |
| Docs rendering  | ✅ Implemented | `docs/*.md` rendered in the Docs tab |
| Real connectors | 🚧 Planned     | Adapter seam exists; integrations currently simulated |
| Auth/RBAC       | 🚧 Planned     | Local single-operator console for v1 |
| Windows EXE     | 🚧 Planned     | `start.bat` today; see packaging notes in README |

## Verified behaviour
- Seeding creates 4 playbooks, 14 incidents, ~8 historical runs and activity history.
- Ingesting an incident with `autoRun` enabled matches a playbook by severity and runs it automatically.
- Running a playbook streams per-step status/logs to the Automation tab; step failures honour `errorPolicy`.
- Reports filter by date/severity/category/status/playbook and download cleanly as `.html`.

## Known limitations (v1)
- Simulated integrations produce deterministic-looking sample outputs — no real security tooling is contacted.
- In-memory run execution: runs are lost on restart unless finished (finished runs are persisted).
- Single process / single user.
- No encryption at rest (local JSON, plaintext by design for a lab tool).

## Next milestones
1. **v1.1** — real HTTP adapter for a SIEM/EDR via configurable webhook; enrich against VT/MISP API.
2. **v1.2** — scheduled playbooks + MITRE ATT&CK mapping on steps.
3. **v1.3** — read-only role + audit log export (CSV).
4. **v1.4** — package as a Windows EXE (`pkg`/`nexe`) and macOS/Linux shell script.

## Open decisions
- Backend language if the EXE packaging route is chosen: keep Node (pkg) vs. port to Go.
- Report slicer: add PDF export (requires a dependency) or keep self-contained HTML printing to PDF.
- Persistence: stay JSON-file (current) vs. move to SQLite (heavier, safer under concurrency).