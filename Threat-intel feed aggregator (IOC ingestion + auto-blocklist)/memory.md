# Memory

Engineering memory / notes for the ThreatIntel Feed Aggregator. Written for future
agents and maintainers: what was decided, why, and what not to forget.

## 1. Project intent

- Ingest public threat-intel feeds (TXT / CSV / JSON blocklists).
- Extract Indicators of Compromise automatically.
- Auto-generate firewall/DNS blocklist artifacts.
- Provide a web dashboard with report download.

Delivered as a **web application** (single Flask process + browser UI) rather than
an EXE — cross-platform, remote feeds need an HTTP stack anyway, and the same code
can be packaged to EXE later (see architecture.md §9).

## 2. Key decisions & rationale

| Decision                    | Reason                                                       |
|-----------------------------|--------------------------------------------------------------|
| Flask + SQLite, no build    | Zero infra, single file DB, trivial for SOC labs.            |
| Vanilla JS, canvas chart    | No npm/node dependency; chart is hand-drawn.                 |
| Feed reputation → confidence| Auditable, transparent scoring; easy to reason about.        |
| `UNIQUE(value,type)` upsert | Re-ingests bump `last_seen` instead of duplicating rows.     |
| Reject private/reserved IPs | Keeps blocklists meaningful (RFC 1918, 127/8, etc. removed). |
| Auto `pf` blocklist post-ingest | Fastest time-to-blocklist for pf/PF Sense users.         |
| `os.path.basename` on downloads | Defends against path-traversal on reported filenames.   |

## 3. Gotchas discovered

- **Regex TLD lists break easily** — earlier draft of `_DOMAIN_RE` had a stray
  `"` + `;` mid-string that produced a `SyntaxError`, and an unbalanced parenthesis
  that failed `re.compile`. Lesson: keep TLD alternation small & compile-tested;
  `python -c "import re; re.compile(...)"` before saving.
- **Feed sources rot** — ZeuS Tracker (DNS dead, retired 2020) and CINS (404)
  were removed; URLhaus CSV timed out (huge) so it was switched to the fast
  `text/` endpoint (56k URLs). `sync_seed_feeds()` in `database.py` repairs the
  live DB at startup: deletes `DEAD_FEEDS`, inserts missing seeds, refreshes
  existing seed URLs. Keep `DEAD_FEEDS`/`SEED_FEEDS` maintained as sources change.
- **Multi-token feeds need smart line parsing** — Tor exit list emits
  `IPAddress a.b.c.d`; naive "first token" parsing dropped the IP. Now
  `_score_token()` in `parser.py` picks the most IOC-like token per line.
- **SQLite idempotent seeding** — `seed_feeds()` only seeds on empty DB;
  `sync_seed_feeds()` handles incremental repair so existing installs heal.
- **Flask debug + reloader** — `use_reloader=False` in `app.py` avoids a second
  process holding the SQLite DB during dev.
- **Windows PowerShell** — no `&&`; scripted steps must use `;` and `if ($?)`.
- **DB folder bootstrapping** — `init_db()` mkdirs `data/` and `reports/` before
  the first query; call it at import time so `seed_feeds()` has a home.
- **Large feed responses** — `MAX_FEED_BYTES = 10 MB` cap prevents memory blowups;
  fetch length check runs before decode.

## 4. Architecture cheat-sheet

```
HTTP feed ─▶ engine/fetcher ─▶ engine/parser ─▶ engine/extractor ─▶ engine/ingestion ─▶ SQLite
                                                                        │
                      SQLite ─▶ engine/blocklist ─▶ reports/*.txt   (artifact download)
                      SQLite ─▶ engine/reports  ─▶ reports/*.{csv,json,txt}
                      SQLite ─▶ app.py REST ─▶ static/js * ─▶ templates/*.html
```

Code ownership:
- Extract/classify/validate: `engine/extractor.py`
- Format dispatch: `engine/parser.py`
- Pipeline orchestration + DB writes: `engine/ingestion.py`
- Artifacts: `engine/blocklist.py`
- Queries/reports: `engine/reports.py`
- HTTP & rendering: `app.py`

## 5. Conventions to follow

- **No comments unless asked** (repo rule from style guidance).
- Keep the DB access pattern: helper `get_connection()` from `database.py`,
  always `close()` (context-manager not used; be disciplined).
- New feed formats: add function in `parser.py`, expose `fmt` in the feeds UI.
- New blocklist dialect: add `_render_line(typ, value, fmt)` branch in
  `blocklist.py` + a `<option>` in `templates/blocklist.html`.
- Timestamps stored via SQLite `datetime('now')` (UTC).
- API responses are JSON; pages are Jinja2 templates extending `base.html`.
- Frontend uses the `window.api` helper; no fetch calls written twice.

## 6. Test protocol

1. `python -c "import app"` → module load, DB bootstrap, seed feeds.
2. `python app.py` then visit `/` — all pages 200.
3. Ingest one feed (`/api/feeds/<id>/ingest`) → rows appear in `/api/iocs`.
4. `POST /api/blocklist/generate` → file under `reports/`, entry in
   `blocklist_runs`.
5. `POST /api/reports/generate {format:'csv'}` → downloadable file.
6. PATCH `/api/iocs/<id>` blocklisted=1 → reflects in table + excludes from
   future generated artifacts.

## 7. Room for improvement (ordered by value)

1. Scheduled ingest (APScheduler or outer cron/Task Scheduler hit on the route).
2. Analyst=true enrichment: TLP/description fields per IOC, notes in UI.
3. STIX/OpenIOC/MISP feed support (parsers) and STIX2 export.
4. Time-decayed confidence and a purge job for expired IOCs.
5. Auth (basic auth or OIDC) + per-user actions.
6. Postgres migration path + Celery if feeds grow past single-process limits.