# SOAR-Lite — Memory

Persistent team / system memory for SOAR-Lite. This file captures project
context, decisions, and open knowledge so future sessions (human or AI) start
without re-deriving everything.

## 1. Project identity

- **Name:** SOAR-Lite
- **Type:** Automated incident response playbook runner (SOAR-lite)
- **Runtime:** Flask web application; optionally packaged as a Windows EXE.
- **Mode:** Single-analyst SOC demo / trainer; simulated integrations only.

## 2. Current state snapshot

- Core engine complete: incidents, playbooks, execution engine, integration
  bus (8 simulated adapters), risk scoring, HTML report generator.
- UI complete: dark SOC-themed dashboard, incident queue, incident detail with
  live execution timeline, playbook library, executions log, settings.
- Demo data seeded on first run (5 incidents, 5 playbooks, execution history).
- Reports: standalone HTML download per incident.

## 3. Key decisions (ADRs - lightweight)

- ADR-001 **JSON store over SQLite**: auditability, portability, zero deps.
  Revisit if concurrent writers become a bottleneck.
- ADR-002 **Simulated integrations**: all adapters return realistic fake data;
  never touch real systems. Interface designed so real adapters drop in.

## 4. Important conventions

- Playbook step kinds: `title task integration condition delay`.
- Step links: `next`, `on: []` (branch by prior result), `goto`.
- Incident lifecycle: `open → triage → contained → eradicated → recovered → closed`
  (+ `monitoring`, `cancelled`).
- Risk score: 0-100, computed in `risk.py` from weighted signals.
- Reports are fully self-contained HTML (inline CSS) - printable/PDF-ready.
- All runtime data lives in `data/`; keep it out of git.

## 5. Integration adapter contract

```
{ name, health() -> {ok, detail}, execute(action, params) -> 
  {ok: bool, output: any, latency_ms: int, error?: str} }
```
Actions are namespaced: `ti.url_reputation`, `edr.isolate_endpoint`, etc.
Playbook steps reference these exact action strings.

## 6. Known limitations / tech debt

- No auth (single analyst). Multi-user on roadmap.
- Execution history is unbounded - no retention policy yet.
- No real integrations wired (by design).
- UI polling every ~1.2s; fine for LAN demo, revisit for many concurrent runs.

## 7. Useful facts

- Entry point: `python app.py` -> http://127.0.0.1:5000
- Playbooks hot-reload from `/playbooks` without restart.
- `data/reset` endpoint wipes runtime data and re-seeds.
- Report generation is idempotent; cached until incident changes.

## 8. Open questions

- Should report exports include raw JSON evidence? (proposal: yes, via collapsible section)
- Do we want a playbook visual editor (node graph) or is structured JSON enough?