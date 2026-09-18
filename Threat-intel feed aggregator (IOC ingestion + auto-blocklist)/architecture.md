# Architecture

## ThreatIntel Feed Aggregator

Self-hosted threat-intelligence pipeline that ingests open-source IOC (Indicators of
Compromise) feeds, normalizes and scores them, generates firewall/DNS blocklist
artifacts, and produces downloadable reports.

**Type of application:** Web application (single Python service + browser UI).
It was delivered as a web app rather than a `.exe` because SOC/threat feeds are
remote, the pipeline benefits from a real HTTP API, and the target environment can
be any OS — a native EXE would lock it to Windows. If you need a self-contained
desktop distribution instead, see the packaging options at the end of this doc.

---

## 1. High-level diagram

```
                 ┌────────────────────────────────────────────────┐
                 │              ThreatIntel Aggregator            │
                 │                                                │
 Open-source     │   ┌──────────────┐    ┌─────────────────────┐  │
 feed servers ───┼──▶│  fetcher.py  │───▶│     parser.py       │  │
 (TXT / CSV /    │   └──────────────┘    │  TXT / CSV / JSON   │  │
  JSON lists)    │        │              └──────────┬──────────┘  │
                 │        ▼                         ▼             │
                 │   ┌────────────────────────────────────────┐   │
                 │   │              extractor.py             │   │
                 │   │  regex → IP / DOMAIN / URL / HASH /   │   │
                 │   │  EMAIL  + normalization + validation  │   │
                 │   └────────────────────┬───────────────────┘   │
                 │                        ▼                       │
                 │              ┌───────────────────┐             │
                 │              │  ingestion.py     │             │
                 │              │  dedupe, score,   │             │
                 │              │  upsert into DB   │             │
                 │              └─────────┬─────────┘             │
                 │                        ▼                       │
                 │   ┌────────────────────────────────────────┐   │
                 │   │        SQLite  (data/threatintel.db)   │   │
                 │   │  feeds · iocs · ingest_log ·           │   │
                 │   │  blocklist_runs · settings             │   │
                 │   └───────┬────────────────────────┬───────┘   │
                 │           ▼                        ▼           │
                 │   ┌──────────────────┐   ┌──────────────────┐  │
                 │   │  blocklist.py    │   │   reports.py     │  │
                 │   │  pf / iptables / │   │  CSV / JSON / TXT│  │
                 │   │  hosts / BIND    │   │  → /reports/     │  │
                 │   └──────────────────┘   └──────────────────┘  │
                 │                                                │
                 │      Flask REST API  (app.py)  +  Web UI        │
                 └────────────────────────────────────────────────┘
                                      │
                        Browser  ⇄  /api/*  (fetch/JSON)
                        Analyst ⇄  download blocklist & reports
```

## 2. Directory layout

```
threat-intel-feed-aggregator/
├── app.py                 # Flask app: routes, REST API, page rendering
├── config.py              # paths, constants, default/seed feeds
├── database.py            # SQLite schema, connection helper, settings
├── requirements.txt       # Flask, flask-cors, requests
├── start.bat              # Windows launcher (installs deps, runs server)
├── architecture.md        # this file
├── state.md               # operational state reference
├── memory.md              # engineering / maintenance memory
├── engine/
│   ├── __init__.py
│   ├── fetcher.py         # HTTP retrieval of feed URLs (size-capped)
│   ├── parser.py          # feed format parsing (TXT / CSV / JSON)
│   ├── extractor.py       # IOC regex extraction + validate + normalize
│   ├── ingestion.py       # per-feed pipeline: parse → type → dedupe → store
│   ├── blocklist.py       # blocklist artifact generation & run history
│   └── reports.py         # report generation + statistics queries
├── static/
│   ├── css/style.css      # dark SOC dashboard theme
│   └── js/                # vanilla JS SPA-style page logic
│       ├── app.js         # base helpers, API client, toasts
│       ├── charts.js      # lightweight canvas chart renderer (no deps)
│       ├── dashboard.js   # stats grid + trend chart + health tables
│       ├── feeds.js       # feed CRUD + ingest actions
│       ├── iocs.js        # IOC explorer w/ filter + pagination
│       ├── blocklist.js   # generation form + run history + download
│       ├── reports.js     # report generation + file listing
│       └── settings.js    # settings read/save
└── templates/             # Jinja2 pages extending base.html
```

## 3. Data model (SQLite)

| Table           | Purpose                                                        |
|-----------------|----------------------------------------------------------------|
| `feeds`         | Feed sources: URL, format, IOC types, reputation, enabled flag |
| `iocs`          | Normalized indicators; `UNIQUE(value, type)`, confidence, severity, blocklisted flag |
| `ingest_log`    | Every ingestion attempt (success/error, counts, timestamp)     |
| `blocklist_runs`| Generated artifacts: counts per type, format, path, threshold  |
| `settings`      | Key/value: min_confidence, auto_blocklist, expiry_days         |

Normalization rules (see `extractor.py`):
- IPs must be valid and **public** (RFC1918 / loopback / link-local / multicast / reserved are rejected).
- Domains must be syntactically valid TLDs and not localhost/example/lan gates.
- Hashes are lowercase, must be exactly 32/40/64/128 hex chars.
- URLs are stripped of trailing punctuation; scheme required.
- Every IOC is stored as lowercase where applicable.

## 4. Ingestion pipeline (`ingestion.py`)

1. **Fetch** — `fetcher.fetch_text(url)` with 10 MB cap and timeout guard.
2. **Parse** — format selected from feed config; `parse_by_format()` dispatches:
   - `TXT` → line-per-IOC blocklists, `#` comments stripped
   - `CSV` → header or positional column probing (ip/host/url/value…)
   - `JSON` → `ioc` / `value` / `ip` / `url` / `domain` key probing
3. **Extract/type** — classify each candidate; convert to typed IOC.
4. **Dedupe + store** — INSERT for new indicators, UPDATE `last_seen` for existing
   (re-activating stale rows); `UNIQUE(value, type)` guards duplicates.
5. **Score** — confidence = feed `reputation` (rounded, 0–1); severity derived
   (>=0.85 high, >=0.6 medium, else low).
6. **Auto-blocklist** — if `auto_blocklist` setting is enabled, a `pf` artifact is
   regenerated after any successful ingestion batch.

## 5. Auto-blocklist (`blocklist.py`)

- Rebuilds artifacts from IOCs where `blocklisted = 0`, `confidence >= threshold`,
  `last_seen` within the expiry window.
- Supported output formats:

| Format       | What it contains                                            |
|--------------|--------------------------------------------------------------|
| `pf`         | PF/PF Sense: bare IPs, `domain:` lines, `url:` lines          |
| `iptables`   | `-A INPUT -s <ip> -j DROP` / `-A OUTPUT -d <domain> -j DROP` |
| `hosts`      | `0.0.0.0 <domain|ip>` hosts-file entries                     |
| `bind`       | `zone "<domain>" { type master; file "null.zone"; };`        |
| `domains`    | plain de-duplicated list of IPs & domains                    |

- Artifacts are written to `reports/blocklist_<fmt>_<ts>.txt`, downloadable via the
  web UI. A row in `blocklist_runs` is created each run.

## 6. REST API

| Method | Endpoint                    | Purpose                                   |
|--------|-----------------------------|--------------------------------------------|
| GET    | `/api/stats`                | aggregate IOC counts, feeds, severity      |
| GET    | `/api/trend`                | last-14-days ingestion trend               |
| GET    | `/api/ingest-history`       | last 30 ingestion log rows                 |
| GET    | `/api/feeds/status`         | feed health (status, last check)           |
| GET    | `/api/feeds`                | list feeds                                 |
| POST   | `/api/feeds`                | create feed                                |
| PUT    | `/api/feeds/<id>`           | update feed                                |
| DELETE | `/api/feeds/<id>`           | delete feed                                |
| POST   | `/api/feeds/<id>/ingest`    | ingest one feed                            |
| POST   | `/api/ingest-all`           | ingest all enabled feeds                   |
| GET    | `/api/iocs`                 | query IOCs (`type`,`severity`,`q`,`blocklisted`) |
| PATCH  | `/api/iocs/<id>`            | block/unblock, edit severity/notes         |
| POST   | `/api/blocklist/generate`   | generate artifact                          |
| GET    | `/api/blocklist/runs`       | blocklist run history                      |
| GET    | `/api/blocklist/download/<f>`| download artifact                          |
| POST   | `/api/reports/generate`     | generate CSV/JSON/TXT report               |
| GET    | `/api/reports/list`         | list generated files                       |
| GET    | `/api/reports/download/<f>` | download report                            |
| GET    | `/api/settings`             | read settings                              |
| POST   | `/api/settings`             | write settings                             |

## 7. Technology decisions

- **Flask + SQLite** — zero external services, one process, portable file DB.
  Good for small SOC teams/labs; WAL mode for concurrent reads.
- **Vanilla JS** — no build step; the dashboard chart is hand-rolled on canvas,
  keeping dependencies to three small Python packages.
- **Confidence model** — feed reputation is the single score driver (0–1),
  deliberately simple and auditable. Extensible to count/last-seen decay later.
- **Security posture** — user-provided URLs are fetched server-side; consider
  allow-listing feeds in production. No secrets stored. Validation strips path
  traversal via `os.path.basename` on downloads.

## 8. Extensibility

- Add a new feed format → add a branch in `parser.py` and a preview in feeds UI.
- Add STIX/OpenIOC/TAXII support → new parser module feeding `extractor.py`.
- Add scheduled ingestion → swap `run_ingest` into a scheduler task or the
  Windows Task Scheduler / cron calling `curl -X POST /api/ingest-all`.
- Add external enrichment (VirusTotal, DNS/lookup) → hook in `process_feed` after
  extraction, before `insert`.
- Scaling beyond a single SQLite file → replace `database.py` with SQLAlchemy +
  Postgres while keeping the REST contract.

## 9. Packaging options (optional)

- **Expose to other machines**: Flask runs on `0.0.0.0:5100` already — access at
  `http://<host>:5100`.
- **Windows EXE from this code** (if truly needed):
  `pip install pyinstaller && pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" app.py`
- **Production WSGI**: run with `waitress-serve --listen=0.0.0.0:5100 app:app`
  (pip install waitress) instead of Flask's dev server.
- **Docker**:
  ```
  FROM python:3.12-slim
  COPY . /app
  WORKDIR /app
  RUN pip install -r requirements.txt
  EXPOSE 5100
  CMD ["python", "app.py"]
  ```