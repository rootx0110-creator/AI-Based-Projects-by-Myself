# SOAR-Lite — Architecture

**SOAR-Lite** is a lightweight, self-contained **Security Orchestration, Automation and Response** playbook runner. It automates the execution of incident-response playbooks against incoming security incidents and produces downloadable reports.

## 1. Goals & Non-Goals

### Goals
- Execute structured, multi-step IR playbooks automatically or on demand.
- Correlate incidents with playbooks and track every run step-by-step.
- Provide a polished, tabbed operator console (Dashboard / Playbooks / Incidents / Automation / Reports / Docs).
- Produce professional reports with **HTML** as the primary download format (plus JSON, Markdown, CSV).
- Run with **zero external dependencies** so it can be launched from a terminal or double-click `start.bat`.

### Non-Goals (v1)
- No persistent SIEM/EDR/NDR connectors — integrations are *simulated* behind a clean adapter seam.
- No multi-user auth/RBAC (single-operator local console).
- No distributed orchestration or high availability.

## 2. High-Level Components

```
                 +--------------------------------------------------------------+
                 |                        BROWSER (operator)                     |
                 |  Dashboard | Playbooks | Incidents | Automation | Reports | Docs|
                 +-----------------------------+--------------------------------+
                                               |  HTTP/JSON (same origin)
                                               v
                 +--------------------------------------------------------------+
                 |                    server.js  (Node HTTP server)             |
                 |   REST API      static assets  (public/)    docs rendering   |
                 +---------+----------------+---------------+--------------------+
                           |                |               |
            +--------------v-----+   +------v--------+   +--v----------------+
            |   lib/engine.js    |   | lib/store.js  |   | lib/reports.js    |
            |   playbook runner  |   | file storage  |   | HTML/JSON/MD/CSV  |
            |   step simulator   |   | seed data     |   | lib/markdown.js   |
            +--------------------+   +------+--------+   +--------------------+
                                           |  atomic JSON writes
                                   +-------v--------+
                                   |  data/soar.json |
                                   +-----------------+
```

### Runtime
- **`server.js`** — zero-dependency Node HTTP server. Serves the SPA from `public/`, exposes a JSON REST API under `/api/*`, generates reports, and renders `docs/*.md` to HTML.
- **`lib/engine.js`** — the playbook runner. Executes steps asynchronously, simulates integration outcomes, evaluates `decision` branches, applies error policies, and writes a full audit trail per run.
- **`lib/store.js`** — JSON-file persistence with atomic writes (write-temp-then-rename). Seeded on first boot from `lib/seed.js`.
- **`lib/reports.js`** — aggregates filtered data and renders **HTML** (styled, self-contained, printable), plus JSON, Markdown and CSV variants.
- **`lib/markdown.js`** — small, safe markdown renderer used for the Docs tab.

## 3. Data Model

| Collection   | Purpose                                                        | Key fields (abridged) |
|--------------|----------------------------------------------------------------|------------------------|
| `playbooks`  | Registered playbooks with ordered steps                         | `name, trigger, active, errorPolicy, steps[]` |
| `incidents`  | Security incidents received from sources                        | `title, severity, status, category, artifacts[]` |
| `runs`       | Executions of playbooks against incidents (or standalone)      | `playbookId, incidentId, status, steps[]`, `logs[]` |
| `activity`   | Append-only operator feed                                       | `type, title, detail, ts` |

### Step model
Every playbook step is `{ id, type, name, params }`. Supported `type`s:

| Type        | Simulated effect                                              | Key params |
|-------------|---------------------------------------------------------------|------------|
| `notify`    | Alert a channel/person                                        | `channel` |
| `enrich`    | Look up context (IP/domain/hash)                              | `source`, `field` |
| `extract`   | Pull indicators of compromise out of the incident             | — |
| `quarantine`| Isolate an affected asset                                     | `host` |
| `block`     | Block an IOC at a control point                               | `device`, `ioc` |
| `collect`   | Gather evidence/logs                                          | `target` |
| `command`   | Run a response command on a target host                       | `host`, `cmd` |
| `decision`  | Branch on an incident field or prior output                   | `field`, `op`, `value`, `branch` |
| `escalate`  | Escalate severity / assign responder                          | `assignee`, `priority` |
| `wait`      | Hold between actions                                          | `ms` |
| `resolve`   | Close the loop, apply resolution note                         | `note` |

### Error policy
`playbook.errorPolicy` — `continue` (mark step failed and proceed), `stop` (halt the run as failed) or `abort-incident` (halt and flag the incident).

## 4. Key Flows

### 4.1 Incident ingestion → automated response
1. Operator clicks **Ingest (Simulate)** or a connector POSTs an incident to `POST /api/incidents`.
2. `store` persists the incident and appends an activity event.
3. If `settings.autoRun` is enabled, the server asks the engine to match against **active** playbooks whose `trigger.severityMin` is satisfied.
4. The engine spawns an async `run`, executing each step with simulated latency and outcomes, streaming `logs[]` and per-step status.
5. On `resolve` steps, the incident may be auto-marked resolved (playbook `postAction`).

### 4.2 Manual run
- `POST /api/playbooks/:id/run` with an optional `incidentId` creates a run immediately visible in Automation and spawns execution.

### 4.3 Reporting
- `GET /api/reports` with filters + `format` renders an aggregate.
- `GET /api/reports/download?format=html&...` streams `Content-Disposition: attachment` so the browser saves the file as `soar-report-<date>.html`.

## 5. Adapter Seam (future real integrations)

Implemented as `simulateStep(step, ctx)` in `engine.js`. Swapping in real connectors (`SIEM`, `EDR`, `NDR`, `SOAR VM`) only requires replacing the body of the step handler per `type` — no changes to the runner loop, store, or UI.

## 6. Security Notes
- Local-first single process; binds to `127.0.0.1`.
- No external packages; no network egress from the server.
- Markdown rendering escapes HTML before formatting (no XSS from docs content).

## 7. Sequence Diagram (automated run)

```
 Operator            server.js             engine.js              store/JSON
    |  POST /api/incidents |                    |                      |
    |--------------------->|                    |                      |
    |                      | match trigger      |                      |
    |                      |-------------------->    startRun()        |
    |                      |                    |--> save run (queued) |
    |                      |                    |  async loop over steps|
    |                      |                    |---> update step/log   |
    |                      |                    |---> simulateStep      |
    |  GET /api/runs :id   |                    |<--- result            |
    |<---------------------|-------------------------------------------------|
    |                      |                    |---> run success/failed|
    |                      |                    |---> postAction/activity|
```