# Architecture

## Overview
`xss-payload-tester` is a self-contained Python (Flask) web
application for probing your own lab web app with XSS payloads.
It ships with a colored web UI, a detection engine, a built-in
payload library, and an HTML report generator. It can also be
packaged into a single Windows EXE via PyInstaller.

## Components

```
browser (colored UI)
   |
   |  fetch()  JSON
   v
Flask app  (app.py)
   |                     serves /api/* and index.html
   +-- /api/test   -> engine.run_test(config)      (scanning)
   +-- /api/payloads (-) payloads.payload_catalog() (library)
   +-- /api/report  -> report.build_html_report(run) (download)
   |
   +-- engine.py   requests session, URL builder, detection heuristics
   +-- payloads.py payload data (29 payloads, 6 categories)
   +-- report.py   standalone HTML report builder
   +-- templates/ + static/  UI (Jinja template, CSS, JS)
```

## Data flow (one scan)

1. Front-end collects the form: target URL, param name, method,
   injection location, timeout, concurrency, headers, custom
   payloads. POSTs JSON to `/api/test`.
2. `engine.run_test(config)`:
   - builds a `requests.Session` (custom UA + extra headers/cookies)
   - fetches a baseline GET of the URL (reachability + size/type)
   - builds the payload list: built-ins (optionally filtered by
     `payload_ids`) + user custom payloads
   - runs each payload concurrently (ThreadPoolExecutor, bounded)
   - each request is either GET (payload injected into query via
     `inject_query_param`) or POST (query string / form / JSON body)
3. Per-response analysis in `engine.finalize()`:
   - payload decode variants: raw, unquote-1x, unquote-2x,
     html-unescaped, html-unescaped+unquote
   - response body decode variants: raw, url-1x, url-2x,
     html-unescaped, js-unicode-unescaped (\uXXXX / \xXX)
   - reflection point located (smallest index) + context sniffing:
     inside `<script>` block? inside a tag? preceded by an
     event-handler sink (onerror=, onload=, onfocus=, ...)?
   - verdict table:
       marker_hits + alert( + dangerous sink  -> Executable XSS
       reflected + script-context + markers    -> Executable XSS (script context)
       reflected + event-sink                 -> Reflected in event-sink
       reflected (or markers found decoded)   -> Reflected
       only markers decoded                   -> Partial reflection
       otherwise                              -> Not reflected / filtered
4. Results sorted back into payload order, bundled with summary
   KPI counters + baseline info, returned as JSON. A `run_id`
   and `app_version` are stamped on the run object.
5. Report: front-end POSTs the *same run object* back to
   `/api/report`; `report.build_html_report()` renders a fully
   self-contained HTML page (inline CSS, escaped payloads, KPI
   cards, verdict pills, highlighted evidence snippets, legal
   note) and serves it as an attachment. The last report + token
   are cached in memory so `/api/report/<token>` can re-download.

## Detection philosophy
No browsers/JS execution is used. "Verdict" = heuristic triage for
*a lab*, not a PoC guarantee. Snippets are shown escaped; script
blocks are redacted (`[executable block omitted for safety]`) in
the baseline and page-head evidence.

## UI theme
Teal -> violet gradient background with amber accent, glassmorphism
cards, responsive (grid collapses to single column on narrow
screens; table flips to stacked cards under 720px).

## Directory layout
```
templates/index.html      UI markup
static/style.css          theme (variables, components)
static/app.js             fetch /reports /ws logic
app.py                    Flask routes + process entry point
engine.py                 scanning engine
payloads.py               payload catalog
report.py                 HTML report
lab_app.py                optional sample vulnerable target
requirements.txt          flask + requests
build_exe.ps1             PyInstaller one-file build
```
## How to run
```
pip install -r requirements.txt
python app.py --port 5173
# or
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```