# Architecture — Compliance Automation Suite

A local-first compliance automation application that maps and tracks security
controls across three frameworks:

| Framework | Coverage in this app |
|---|---|
| **ISO/IEC 27001:2022 Annex A** | All 93 controls in 4 themes (Organizational, People, Physical, Technological) |
| **Bangladesh Bank ICT Security Guideline v2.0** | 18 domains (B-01 … B-18) |
| **NIST Cybersecurity Framework 2.0** | 22 categories across GV / ID / PR / DE / RS / RC |

## High-level view

```
┌──────────────────────────────────────────────────────────────────┐
│                          Browser (SPA)                           │
│   app/web/index.html + app.css + app.js  (vanilla JS, no build)  │
│   Dashboard · Control Register · Mapper · Gaps · Crosswalk ·     │
│   Report download                                                │
└───────────────▲──────────────────────────┬───────────────────────┘
                │ static files             │ JSON API (fetch)
┌───────────────┴──────────────────────────▼───────────────────────┐
│                 app/server.py (stdlib http.server)               │
│  ThreadingHTTPServer · GET /api/* · POST /api/* · static /       │
└───────────────┬──────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────┐
│  app/services.py        business logic (scoring, gaps, mapping)  │
│  app/report.py          self-contained HTML report generator     │
│  app/store.py           JSON persistence + audit log (atomic)    │
│  app/data.py            control catalogs + keyword crosswalk     │
│  app/config.py          paths (handles PyInstaller _MEIPASS)     │
└───────────────┬──────────────────────────────────────────────────┘
                │
        data/compliance_data.json   (dev)  or
        %APPDATA%/ComplianceSuite/  (frozen EXE)
```

## Key design decisions

1. **Zero third-party runtime dependencies.** Only the Python standard
   library is used, so the EXE is small, starts instantly, and nothing can
   break on import. PyInstaller just needs `--add-data app/web`.

2. **Local-first.** All data stays in one JSON document next to the user
   (or in `%APPDATA%` when frozen). No cloud, no database server — easy to
   run inside a bank's restricted network.

3. **BB domains as the crosswalk bridge.** `BBICT_TO_ISO` and
   `BBICT_TO_NIST` are explicit, hand-curated dictionaries in
   `app/data.py`. Any control in one framework maps to the others by going
   through the BB domain(s) that reference it — auditable and easy to edit.

4. **Scoring model.**
   - Implemented = 1.0, Partially = 0.5, Planned = 0.25, Not Impl. = 0
   - `Not Applicable` is excluded from the denominator
   - Framework % = weighted sum / assessed controls
   - Maturity levels: ≥90 Optimized (5), ≥75 Managed (4), ≥55 Defined (3),
     ≥30 Developing (2), else Initial (1)
   - Gap risk = status weight (3/2/1) × 2.2, +15% for Technological theme,
     capped at 10.0; findings sorted by risk descending.

5. **Report.** `/api/report` renders a fully self-contained HTML document
   (inline CSS, no JS/CDN) — framework scores, prioritized gap analysis,
   crosswalk matrix and the complete control register. It opens in a new
   tab and is saved with Ctrl+S / "Save as…". Print-friendly via @media print.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/summary` | dashboard KPIs, per-framework scores, maturity |
| GET | `/api/catalog` | all controls + current assessment state |
| GET | `/api/gaps` | prioritized open findings |
| GET | `/api/matrix` | BB→ISO/NIST crosswalk coverage matrix |
| GET | `/api/map?framework=&id=` | one control mapped to the other frameworks |
| GET | `/api/report` | downloadable self-contained HTML report |
| POST | `/api/status` | update one control (status/owner/notes/evidence) |
| POST | `/api/bulk` | set one status for many controls |
| POST | `/api/organization` | set organization name |
| POST | `/api/findings` | persist a findings snapshot |
| POST | `/api/reset` | clear all assessments (keeps org name) |

## Extending

- **More frameworks** (e.g. PCI DSS): add a dataset to `app/data.py`, add a
  catalog builder in `app/services.py`, add a tab in the UI — the scoring,
  gap and report engines are framework-agnostic.
- **Real evidence files**: extend `store.py` to hash + archive attachments
  into `DATA_DIR/evidence/`.
- **Multi-user**: swap `ThreadingHTTPServer` for a WSGI app behind IIS/nginx
  and move the JSON store to SQLite (interface already isolated).
