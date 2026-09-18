# Architecture — Web App Fuzzer for Input Validation Testing

> Version 1.0.0 · September 2026

## 1. Overview

The fuzzer is a self-contained web application built with **Flask (Python)**
on the backend and a **vanilla HTML/CSS/JavaScript** single-page interface on
the frontend. It sends a library of security payloads through the fields of a
target endpoint, analyzes the responses for anomalies, and exports the results
as a self-contained HTML report.

```
 Browser (Single-Page UI)
   │  fetch /api/*
   ▼
 Flask app.py               (API layer, job registry, report endpoint)
   │
   ├── fuzzer.py            (payload library · detection engine · threaded runner)
   ├── report.py            (HTML report generator)
   └── templates/static/    (rendered UI)
```

## 2. Component responsibilities

### 2.1 `app.py` — HTTP & scan orchestrator
- Serves the single-page UI at `/`.
- `POST /api/scan` validates the target configuration, creates a **scan job**
  in an in-memory registry (`SCANS`), and starts it on a background thread.
- `GET /api/scan/<token>` streams progress, a rolling log and live results.
- `POST /api/scan/<token>/cancel` sets an abort flag consumed by workers.
- `POST /api/report` turns client-posted results + config into a downloadable
  HTML report (used by the UI's "Download HTML report" button).
- `GET /api/report/<token>` produces the same report from the server-side copy.
- `GET /api/suggest/<field>` maps a field name to suggested payload categories.
- `GET /api/categories` lists payload categories with metadata.

### 2.2 `fuzzer.py` — the fuzzing core
- **Payload library (`PAYLOADS`)** — one entry per attack class, each with a
  friendly name, description, default severity, a list of
  `(payload, technique)` pairs and a short hint. Supported classes: SQLi, XSS,
  command injection, path traversal / LFI, LDAP, SSTI, SSRF, XXE, open redirect,
  format string, JWT/auth tampering.
- **Request construction (`Fuzzer.build_request`)** — injects the payload into
  the matching parameter depending on the configured method and injection
  points (query string, form body, or custom headers).
- **Threaded runner (`Fuzzer.run`)** — builds a flat job list
  (`category × field × payload`), optionally shuffles it, and dispatches jobs
  from a shared queue to a configurable pool of worker threads (1–12). A
  `cancel_event`/abort flag lets a scan be stopped mid-flight.
- **Detection engine (`analyze_response`)** — evaluates each response with a
  weighted risk model that combines:
  1. **Reflection** — payload text (or a distinctive fragment) echoed back;
  2. **Error leakage** — regex signature sets for SQL errors, stack traces and
     framework error pages;
  3. **Timing** — elapsed time vs. a baseline request, flagging time-based
     injection sleeps (SLEEP/pg_sleep/WAITFOR DELAY) that exceed ~5 s or a 4x
     ratio;
  4. **Status anomalies** — 4xx/5xx shifts and server errors;
  5. **Semantic content checks** — e.g. `/etc/passwd`-like output for LFI
     payloads, evaluated `7*7` → 49 for SSTI, win.ini markers, SSRF redirects
     to internal targets.
- Risk is normalized to a severity (`high / medium / low / ok`) and each
  finding records status, latency, length, reflection flag, matched signals
  and human-readable evidence bullet points.

### 2.3 `report.py` — HTML report generation
- Produces a **self-contained HTML document** (inline CSS, JS-free) with:
  - header chips (target, method, generated-at, counts, score),
  - an overall security grade (A+ … D) from weighted findings,
  - severity breakdown bars and category volume bars,
  - summary stat cards,
  - a scan configuration table,
  - a full findings table with payload, HTTP code, timing, reflection flag,
    matched signals and evidence, color-coded by severity and print-ready.

### 2.4 Frontend (`templates/index.html`, `static/`)
Single-page UI organised as a friendly 4-step flow:
1. **Target** — URL, method, cookies, workers, delay, timeout, UA, toggles;
2. **Fields & payloads** — field list with live category suggestions, injection
   point checkboxes, advanced query/body/header editing, payload category cards
   with select-all / core-set shortcuts and a persisted selection;
3. **Run & results** — animated progress bar, terminal-style log, live summary
   cards, severity/text filtering, expandable result rows with evidence;
4. **Report** — one-click HTML report download built from current results.
`Ctrl+Enter` starts a scan. No front-end framework or build step is used.

## 3. Request / response lifecycle

```
 UI → POST /api/scan {url, method, fields, categories, ...}
        │  validate → start background thread
        ▼
 Fuzzer.run(): baseline probe → flatten jobs → worker pool
        │  each job: build_request(field, payload) → send()
        ▼
 analyze_response(payload, technique, response, timing)
        │  risk model → severity, evidence
        ▼
 results list sorted by severity (high → ok)
        │
        ▼
 UI polls GET /api/scan/<token>  →  live table
 POST /api/report {results, config}  →  downloadable .html
```

## 4. Configuration inputs

| Input              | Example                      | Notes |
|--------------------|------------------------------|-------|
| `url`              | `https://example.com/search` | http(s) only |
| `method`           | `GET / POST / PUT / …`       | affects where the body is injected |
| `fields`           | `q, name, id`                | comma/newline separated |
| `categories`       | `["sql","xss","cmd",…]`      | any subset of the payload library |
| `params` / `data`  | `category=tools&page=1`      | baseline request columns |
| `headers`          | `X-Forwarded-For: x` per line | optional extra headers |
| `cookies`          | `session=abc; lang=en`       | sent on every request |
| `threads`          | 1–12 (default 4)             | concurrency level |
| `delay`            | 0–3 s                         | between requests |
| `timeout`          | 2–120 s (default 15)          | per request |
| `verify_ssl` / `use_baseline` / `shuffle` | booleans | TLS, timing baseline, order |

## 5. Security & lifecycle
- Scans are stored **in memory only**; restarting the server clears them.
- Report generation is **server-side from the posted JSON** — no file binding
  to the user's machine; the client simply stores the downloaded file.
- The app binds to `127.0.0.1` by default (override with `HOST` env var).
- Payloads are **benign**; no destructive commands are included.

## 6. Design decisions
- **Plain Python + stdlib + `requests`** — zero build step, easy to read and
  audit, runs anywhere Python 3.10+ is available.
- **Thread pool instead of async** — the payload count is modest; threads keep
  the code simple and predictable on Windows.
- **Server-generated HTML report** — lets the report be independent of the
  frontend's current state and keeps the UI lightweight.
- **Weighted risk model** — every signal contributes a risk score so results can
  be sorted by *impact* rather than by payload order.

## 7. Extending
- **Add a category**: add an entry to `PAYLOADS` in `fuzzer.py` with
  `(payload, technique)` pairs, then (optionally) a semantic check branch in
  `analyze_response`, a `top_keywords` mapping in `app:api_suggest`, a note in
  `HELP_CATEGORY_NOTES`, and a card already renders automatically.
- **Add a signal**: extend `SQL_ERROR_SIGNATURES` / `GENERIC_ERROR_SIGNATURES`
  or add a weighted branch in `analyze_response`.