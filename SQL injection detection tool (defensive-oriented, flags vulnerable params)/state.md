# SQLInspect — Runtime State

Describes what state the tool holds, where it lives, and how it flows.

## State inventory

| State | Location | Lifetime | Notes |
|---|---|---|---|
| Scan results | `STORE` dict in `app.py` | Process lifetime | Keyed by report UUID `rid` (12 hex chars) |
| Scan history | Flask `session` cookie | Browser session | Last 50 entries, per-browser |
| Live toggle / consent | Browser DOM | Page lifetime | Never sent to server as truth — enforced server-side too |
| Detection profile knobs (timeout, delay) | DOM → JSON body | per request | Mirrored into `live_settings` |
| Generated exports | In-memory `BytesIO` | Request lifetime | Streamed to client, never written to disk |
| Detection signatures | `core/payloads.py` | Static | Compiled regex on import |

## Data flow (a scan)

```
User input (URL | raw request | log/list)
        │
        ▼
POST /api/scan  {mode, data, live{enabled,consent,timeout,delay_ms}}
        │
        ▼
core.parser.build_targets(mode, data)
   └── target = {method, url, host, path, params{name:[values]}, source}
        │
        ▼
core.analyzer.run_scan(...)
   ├── for each target:
   │     for each (name, value):
   │        │  analyze_value(value)      → offline score, techniques, dbms_hints
   │        │  (optional, live & consent)→ LiveScanner.probe_parameter(...)
   │        └── result finding:  {name, location, value, score, risk,
   │                              dbms, techniques[], flagged, recommendation}
   └── payload = {id, summary{...}, targets[...]}
        │
        ▼
STORE[rid] = payload  ;  session.history.append({...})
        │
        ▼
#results rendered client-side (gauge, stat cards, technique bars, findings
#  table with expandable detail rows)
        │
        ▼
/api/report/<rid>/download/<fmt>  →  ReportGenerator → PDF|CSV|JSON|HTML
/report/<rid>                    →  full report page view
```

## State rules

- The engine is **pure/stateless**: `run_scan` accepts input + settings and returns a
  serialisable dict. No module-level mutable state affects scoring.
- `LiveScanner` carries the only mutable session-scoped state (probe budget counter,
  last error, request latency measurements) and is discarded after each scan.
- History is cosmetic (UX aid); rebuildable from `STORE` at any time.

## Session / concurrency

- Flask `threaded=True`; `STORE` is a plain dict.
- For a local defensive tool this is acceptable; if shared use is ever required,
  swap `STORE` for `flask-caching` or SQLite with a TTL (decision in `memory.md`).

## Failure states

| Failure | Behaviour |
|---|---|
| Parse error (bad URL / malformed request) | HTTP 400 with `{error}` surfaced as toast |
| Live probe network failure | Finding marked `unreachable`; run continues; no crash |
| Live probing without consent | HTTP 400; run refused server-side |
| Probe budget exhausted | ScannerError → finding `unreachable`, run completes |
| Unknown report id | HTTP 404 → page not found |