# SOAR-Lite — System Architecture

## 1. Overview

SOAR-Lite automates incident response by matching incoming incidents to
**playbooks** and driving them through an **execution engine** against a set of
**integration adapters**. It is intentionally small ("SOAR-lite"), stateless at
the process level, and persists everything as JSON on disk so it can be
archived, diffed, and audited trivially.

```
                       +-----------------------------------------------+
   Web UI (Flask)  --> |  REST API layer (app.py / blueprints)         |
   ------------------> |   /api/incidents  /api/playbooks              |
                       |   /api/executions /api/reports                |
                       +----------------------+------------------------+
                                              |
                                              v
                    +-----------------------------------------------+
                    |                CORE ENGINE (soar_lite)        |
                    |                                               |
                    |  IncidentService    PlaybookService           |
                    |  ExecutionEngine    ReportService             |
                    |  IntegrationBus     RiskScoring               |
                    +----------+-----------------------+------------+
                               |                       |
                               v                       v
                    +---------------------+   +----------------------+
                    |  SIMULATED INTEGS   |   |   JSON STORAGE       |
                    |  SIEM TI EDR FW DNS |   |   data/*.json        |
                    |  Sandbox Mail Tick  |   |   threaded, atomic   |
                    +---------------------+   +----------------------+
```

## 2. Components

### 2.1 Web / API layer (`app.py`)
- Flask app factory; single-page shell served by Jinja2 templates.
- JSON REST API consumed by the vanilla-JS front end (fetch + polling).
- Static assets served from `/static`. Reports served from `/reports`.

### 2.2 Storage layer (`soar_lite/storage.py`)
- Single `Store` class owning all collections: incidents, executions, IOCs,
  settings, report cache.
- Each collection is a JSON document; writes are **atomic** (write temp file +
  rename) and guarded by a module-level `RLock`, writer-thread ordering keeps
  simulation updates consistent.
- Pure-Python, zero deps - keeps the EXE build tiny.

### 2.3 Incident service (`soar_lite/incident.py`)
- CRUD for incidents, lifecycle state machine, risk scoring, IOC extraction.
- Lifecycle: `open → triage → contained → eradicated → recovered → closed`
  plus `monitoring` and `cancelled` (industry NIST IR phases).
- Severity: `critical / high / medium / low / informational`.
- Source channels, analyst assignment, tags, and notes (audit trail).

### 2.4 Playbook service (`soar_lite/playbook.py`)
- Loads playbook JSON from `/playbooks` (hot-reload on each request).
- Validation: known step kinds, referenced integration actions exist,
  condition targets resolve to existing step ids, no infinite cycles.

### 2.5 Execution engine (`soar_lite/engine.py`)
- Each incident **run** is an `Execution` with ordered `RunSteps`.
- The engine walks the playbook graph (steps are linked by `next`, `on:[]`
  branches, and `goto`), executing:
  - `integration` -> adapter call (simulated latency),
  - `task`        -> recorded manual assignment,
  - `condition`   -> branch on prior step output with
                     `eq / contains / regex / exists / gt` operands,
  - `delay`       -> pause,
  - `title`       -> structural heading.
- Runs execute in **background worker threads** so the UI stays responsive;
  step state is flushed to disk immediately per step.
- Error handling: on adapter failure, a step enters `failed`, optional
  `retry` policy applies, and the playbook may route to a manual analyst
  override step (`kind: task`, `on_failure: route`).

### 2.6 Integration bus (`soar_lite/integrations.py`)
- Adapter registry with a uniform interface:
  `name, health(), execute(action, params) -> {ok, output, latency_ms}`.
- Simulated adapters (see readme.txt) with configurable failure rate and
  latency - driven by the stored settings. Health map powers the Settings page.

### 2.7 Risk scoring (`soar_lite/risk.py`)
- Configurable weights: severity, IOCs seen in TI, presence of ransomware
  indicators, target is critical asset, etc. Produces a 0-100 score shown on
  the dashboard and used for triage ordering.

### 2.8 Reports (`soar_lite/report.py`)
- Generates **standalone HTML** incident reports (inline CSS, no external
  refs) from incident + execution + IOC data. Designed for printing/PDF and
  email sharing. Structure: header/GDI/exec summary/timeline/playbook step
  table/IOCs/recommendations/footer.

## 3. Data flow (end-to-end)

1. Analyst creates incident (or simulator pushes one). It is scored and placed
   in the triage queue.
2. Analyst attaches a playbook (auto-suggest by incident type).
3. `ExecutionEngine.start()` clones the playbook graph, persists the run, and
   starts a worker thread.
4. Worker executes steps sequentially; each step writes its result back.
5. UI polls `/api/executions/<id>`; the detail page renders progress live.
6. On completion the engine applies closure recommendations; analyst reviews,
   then downloads the HTML report.

## 4. Technology choices

| Concern        | Choice                                  | Rationale                                  |
|----------------|-----------------------------------------|--------------------------------------------|
| Runtime        | Python 3.10+ / Flask 3.x                | Ubiquitous, tiny EXEs via PyInstaller      |
| Persistence    | Atomic JSON files                        | No infra, auditable, trivially backed up   |
| Concurrency    | `threading` + `RLock` per collection     | Good enough for single-node demo/SOC       |
| Frontend       | Vanilla JS + CSS (no build step)         | Zero deps, works offline, keeps EXE small  |
| Charts         | Inline SVG rendered in JS                | No CDN dependency at demo time             |
| Packaging      | PyInstaller onefile (optional)           | Run as web app or double-clickable EXE     |

## 5. Scalability / evolution path

- Swap JSON store for SQLite (or Postgres) behind the same `Store` interface.
- Real integrations via a `requests`-based adapter implementation behind the
  same bus interface (VirusTotal, MISP, CrowdStrike, etc.).
- Multi-analyst mode: add auth + per-analyst workspaces.
- Webhook intake instead of manual creation.
- See `todo.txt` for the prioritized roadmap.