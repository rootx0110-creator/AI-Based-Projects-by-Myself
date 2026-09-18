# SOAR-Lite

**Automated Incident Response Playbook Runner (SOAR-lite)** — a zero-dependency Node.js web application that lets a SOC operator define playbooks, ingest incidents, watch automation run step-by-step, and download professional incident-response reports.

## Quick start

```
start.bat            # double-click on Windows — opens http://127.0.0.1:8787
node server.js       # or run directly (POSIX: node server.js)
```

No `npm install` needed. Node.js 18+ required. The data store (`data/soar.json`) is seeded automatically on first run.

## Feature tour

| Tab | What you get |
|-----|--------------|
| **Dashboard** | Live KPIs, severity donut, 14-day incident trend, playbook run bars, recent activity |
| **Playbooks** | Visual editor for multi-step response playbooks (11 step types), versioning, active/draft toggle, run-on-demand |
| **Incidents** | Full queue with search/filters, IoC artifacts, case updates, simulated intake + auto-run matching |
| **Automation** | Live run console — per-step status, decisions and branches, streaming logs, cancel/retry, engine & auto-run settings |
| **Reports** | Filterable report builder with **HTML as the primary download format**, plus JSON / Markdown / CSV |
| **Docs** | Rendered `docs/architecture.md`, `docs/state.md`, `docs/memory.md` |

### Playbook step types
`notify` · `enrich` · `extract` · `quarantine` · `block` · `collect` · `command` · `decision` (branches) · `escalate` · `wait` · `resolve`

Error policies: `stop`, `continue`, `abort-incident`.

## Architecture

- `server.js` — zero-dependency HTTP server, REST API (`/api/*`), static SPA serving, report generation
- `lib/engine.js` — asynchronous playbook runner with simulated integration adapter
- `lib/store.js` — atomic-JSON persistence + first-boot seeding
- `lib/reports.js` / `lib/markdown.js` — report renders (HTML/JSON/MD/CSV) and the doc renderer
- `public/` — the tabbed operator console (vanilla HTML/CSS/JS, dark theme)
- `docs/` — architecture, state, memory documents (also shown in the Docs tab)
- `data/soar.json` — runtime store (created on first run)

See [docs/architecture.md](docs/architecture.md) for the full design.

## API (abridged)

```
GET  /api/health · /api/stats · /api/activity · /api/meta · /api/settings
GET/POST /api/playbooks            PUT/DELETE /api/playbooks/:id
POST /api/playbooks/:id/run        POST /api/playbooks/:id/toggle
GET/POST /api/incidents            PUT/DELETE /api/incidents/:id
POST /api/incidents/ingest         (simulated connector intake)
GET  /api/runs                     GET /api/runs/:id
POST /api/runs/:id/cancel | /retry
GET  /api/report                   GET /api/report-options
GET  /api/report-download?format=html|json|markdown|csv
GET  /api/docs · /api/docs/:name
```

## Packaging as an executable (optional)

The app is dependency-free Node, so any of these work:

```bash
# Exe via pkg (single-file Windows binary)
npm i -g pkg
pkg server.js --targets node18-win-x64 --output soarlite.exe

# Exe via nexe
npm i -g nexe
nexe server.js -o soarlite.exe
```

When packaging, remember to ship `public/` and `docs/` alongside the binary (paths are resolved relative to the `server.js` location), or adjust `PUBLIC_DIR`/`DOCS_DIR` in `server.js`.

## Configuration

- Port: `PORT=9000 node server.js` (default `8787`)
- Auto-open browser: set `SOAR_NO_OPEN=1` to disable
- Env vars are read in `server.js` (`PORT`, `SOAR_NO_OPEN`)