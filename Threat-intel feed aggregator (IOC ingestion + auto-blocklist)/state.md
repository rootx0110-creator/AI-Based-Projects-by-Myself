# State

Operational state reference for the ThreatIntel Feed Aggregator project.

## 1. Current state (as of last verified run)

| Area            | State                                                        |
|-----------------|--------------------------------------------------------------|
| Application     | Web app, works. Flask server on `0.0.0.0:5100`.              |
| Backend         | `app.py` imports cleanly; all `engine/*` modules import OK.  |
| Database        | SQLite `data/threatintel.db` created on first launch.        |
| Seed feeds      | 10 bundled open-source feeds; synced on startup (`sync_seed_feeds` removes dead services, adds missing, refreshes URLs). |
| Ingestion       | Tested end-to-end against live blocklist.de (378 KB fetched, parsed, scored, stored). |
| Extraction      | Verified: public-IP filter, domain/URL/hash/email extraction, dedupe, upsert. |
| Blocklist       | Verified generation → `reports/blocklist_pf_<ts>.txt`.       |
| Reports         | Verified CSV + JSON generation → `reports/threat_report_*`.  |
| Web UI          | All 6 pages return HTTP 200; static assets load.             |
| Dependencies    | flask, flask-cors, requests installed (Windows, Py 3.14).    |

## 2. Data locations

| Path                                    | Purpose                          |
|-----------------------------------------|----------------------------------|
| `data/threatintel.db`                   | SQLite database (auto-created)   |
| `reports/blocklist_*.txt`               | generated firewall/DNS artifacts |
| `reports/threat_report_*.{csv,json,txt}`| generated reports                |

## 3. Settings catalog

Backed by the `settings` table; defaults applied on first run:

| Key              | Default | Meaning                                       |
|------------------|---------|-----------------------------------------------|
| `min_confidence` | `0.5`   | Blocklist/include threshold for auto generation |
| `auto_blocklist` | `1`     | Auto-generate a `pf` artifact after each ingest batch |
| `expiry_days`    | `90`    | IOCs not re-seen in N days are excluded from blocklists |
| `last_autogen`   | `""`    | Timestamp of last auto-generated blocklist      |

## 4. Feed model fields

| Field         | Type    | Meaning                                              |
|---------------|---------|------------------------------------------------------|
| `name`        | text    | Display name                                         |
| `url`         | text    | Feed endpoint                                        |
| `format`      | text    | `TXT` / `CSV` / `JSON`                               |
| `ioc_types`   | text    | Comma list, e.g. `IP,DOMAIN,URL,HASH`                |
| `reputation`  | real 0-1| Drives indicator confidence & severity               |
| `enabled`     | int 0/1 | Master on/off                                        |
| `auto_ingest` | int 0/1 | Include in "ingest all" batches                      |
| `last_status` | text    | `success` or error substring from last run           |
| `last_check_at`| text   | Timestamp of last attempt                            |

## 5. IOC model fields

| Field         | Meaning                                                  |
|---------------|----------------------------------------------------------|
| `value`       | Normalized indicator (unique together with `type`)       |
| `type`        | `IP` / `DOMAIN` / `URL` / `HASH` / `EMAIL`               |
| `source_feed` | Feed display name that last contributed the IOC          |
| `confidence`  | 0–1 (currently = feed reputation at last ingest)         |
| `severity`    | `high` (≥0.85) / `medium` (≥0.6) / `low`                 |
| `tags`        | free-form (unused in v1 flow, column reserved)           |
| `first_seen`  | first observed timestamp                                 |
| `last_seen`   | most recent observation timestamp                        |
| `blocklisted` | 0/1 flag; manual toggles also honored                     |
| `notes`       | analyst notes via API (reserved column)                  |

## 6. Known behaviors / decisions

- Re-seen IOCs get `last_seen` refreshed (kept alive past expiry window).
- Private/loopback/reserved IPs and example/local TLDs are **filtered out** at
  extraction (reduces noise from test feeds).
- Hash auto-detection requires 32/40/64/128 hex characters.
- Confidence has no time-decay yet — stale high-rep feeds keep their score until
  they drop out of the expiry window.
- Running `Ingest All Feeds` is synchronous; large feeds block the request briefly.
  Fine for small deployments; move to a job queue if many/large feeds are added.

## 7. Current gaps & next steps

1. **Scheduled ingestion** — no built-in timer; wire `/api/ingest-all` to cron /
   Task Scheduler, or add APScheduler.
2. **Expiry purge** — old IOCs are filtered from blocklists but not deleted;
   add a purge job if desired.
3. **Authn / authz** — no login; bind to loopback for single-operator use, or add
   a reverse proxy with SSO in front.
4. **STIX / OpenIOC / MISP** parsing — only TXT/CSV/JSON are supported today.
5. **Export compatibility** — MISP/STIX2 scenes, more blocklist dialects (suricata,
   squid, DNS RPZ) can be added to `blocklist.py`.
6. **Multi-instance** — SQLite WAL supports concurrent readers; heavy writers
   should move to Postgres (see architecture.md §8).

## 8. Verification commands

```bash
# import / sanity check
python -c "import app"

# launch
python app.py            # http://127.0.0.1:5100

# API smoke test
Invoke-RestMethod http://127.0.0.1:5100/api/stats
```