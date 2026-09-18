# SQLInspect — Architecture

A defensive-oriented SQL injection detection tool that **flags vulnerable parameters**.
Deployed as a local Flask web application (with an optional PyInstaller `.exe` wrapper).

## System overview

```
                     ┌───────────────────────────────────────────────┐
                     │                 Browser (UI)                  │
                     │   dark-cyber dashboard · transcript · gauge   │
                     └──────────────▲───────────────────┬────────────┘
                                    │ fetch/JSON        │ download
                     ┌──────────────┴───────────────────▼────────────┐
                     │                Flask app (app.py)             │
                     │  /api/scan  /api/history  /report/<id>        │
                     │  /api/report/<id>/download/{pdf,csv,json,html}│
                     └───────────┬──────────────────┬────────────────┘
                                 │                  │
              ┌──────────────────▼───┐    ┌─────────▼───────────┐
              │   core detection     │    │  reports (exports)  │
              │  payloads · parser   │    │  ReportGenerator     │
              │  analyzer  · scanner │    │  PDF/CSV/JSON/HTML   │
              └───────┬──────────────┘    └─────────────────────┘
                      │ (optional, ON only with consent)
              ┌───────▼──────────────┐
              │  LiveScanner (urllib)│  → target host probes
              │  bounded & consent   │
              └──────────────────────┘
```

## Modules

| Module | Responsibility |
|---|---|
| `core/payloads.py` | Static knowledge base: keyword weights, regex patterns, DBMS error signatures, canonical payload corpus, risk levels. Pure data + compiled regex. |
| `core/parser.py` | Normalises user input into *target* dicts: URLs (query params), raw HTTP requests (form/JSON/cookies), and log/list uploads. |
| `core/analyzer.py` | Detection + scoring engine. Runs offline `analyze_value()` per parameter, then augments with confirmed live findings. Produces JSON-serialisable scan results. |
| `core/scanner.py` | Optional live prober. Minimal urllib client; bounded probe budget; boolean / error / time-based confirmation; defensive guards. |
| `reports/generator.py` | Exports the same in-memory result dict as PDF (reportlab), CSV, JSON, and a self-contained HTML report. |
| `app.py` | Routes, scan orchestration (`run_scan`), in-memory report store, download endpoints, demo seed. |
| `templates/`, `static/` | Server-rendered pages + vanilla JS/CSS front end (no external CDNs — fully offline). |

## Detection pipeline

1. **Parse** — input → one or more `target` dicts, each with a param map
   `{name: [value,...]}` carrying origin (query/body/cookie).
2. **Offline scoring** (per parameter value):
   - canonical payload signature hits
   - syntax pattern regexes (UNION, error-based, boolean, time-based, stacked, comments)
   - SQL keyword density (weighted vocabulary)
   - meta-character context
   - DBMS error signatures captured in the value
   - DBMS fingerprint tokens and encoding obfuscation
3. **Weighted scoring**: each confirmed technique contributes a bounded weight
   (see `TECH_WEIGHTS`); total is clamped to 0–100. Risk label derived
   via `risk_level()` thresholds: Low <25, Medium <50, High <75, Critical ≥75.
4. **Live confirmation (optional)**: behavioural deltas — matching DBMS error text,
   boolean response divergence, latency spikes from `SLEEP/pg_sleep/WAITFOR DELAY`.
5. **Aggregation**: per-parameter findings sorted by score; per-target risk is the
   max parameter score; run summary aggregates across targets.

## Security & defensive posture

- Live probing is **opt-in** (checkbox) and **consent-gated**; default mode is fully offline.
- Probe budget bounded per target (200 `/scanner.py`); polices localhost-lab targets only — documented warning.
- No secrets stored; reports held only in process memory (`STORE`), tied to a random UUID.
- Server binds `127.0.0.1`; no external library/CDN dependencies at runtime.

## Persistence & lifecycle

- Reports: in-memory dict + per-browser session history (last 50 scans).
- Exports generated on demand and streamed to the client (no disk writes).
- Live scan results are never cached on disk.

See also `state.md` (runtime data flow) and `memory.md` (decision log).