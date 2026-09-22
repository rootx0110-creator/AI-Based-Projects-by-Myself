# Architecture — Bug Bounty Methodology Toolkit

**Scope policy:** recon → scan → report, OWN / AUTHORIZED targets only.

## 1. High-level overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Browser (SPA UI)                              │
│   Scope & Auth │ Recon Pipeline │ Findings │ Report │ Toolkit Guide    │
└───────────────┬─────────────────────────────────────────────────────────┘
                │  fetch (JSON API)
┌───────────────▼─────────────────────────────────────────────────────────┐
│                     app.py — ThreadingHTTPServer                       │
│  ┌──────────────┐ ┌──────────────────┐ ┌────────────────────────────┐  │
│  │ Scope Engine │ │ Authorization    │ │ Static file server        │  │
│  │ domain/ip/   │ │ Gate (403 unless │ │ (/ → index.html, /static) │  │
│  │ cidr/url     │ │ attested)        │ │                            │  │
│  └──────┬───────┘ └────────┬─────────┘ └────────────────────────────┘  │
│         │                  │                                            │
│  ┌──────▼──────────────────▼─────────────────────────────────────────┐ │
│  │                    Recon Pipeline (worker thread)                 │ │
│  │  1 validate-scope → 2 dns → 3 http-probe → 4 headers-audit        │ │
│  │  → 5 robots/sitemap/security.txt → 6 tls-inspect → 7 fingerprint  │ │
│  │  → 8 findings-consolidate                                         │ │
│  └──────┬────────────────────────────────────────────────────────────┘ │
│         │                                                               │
│  ┌──────▼───────────┐   ┌────────────────────┐   ┌───────────────────┐ │
│  │ Report Generator │◄──│ data/state.json    │──│ Findings store    │ │
│  │ (standalone HTML)│   │ (persistence)      │   │ (severity-ranked) │ │
│  └──────────────────┘   └────────────────────┘   └───────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Components

| Component | File | Responsibility |
|---|---|---|
| HTTP server | `app.py` | Routes, static assets, JSON API, threaded request handling |
| Scope engine | `app.py` (`ScopeEngine`) | Parses domain / wildcard / IP / CIDR / URL entries; in-scope & out-of-scope matching |
| Authorization gate | `app.py` | Stores attestation; blocks pipeline start (HTTP 403) until user confirms authorization |
| Recon pipeline | `app.py` (`Pipeline`) | Ordered stages executed in a background worker thread; progress + live log |
| Passive checks | `app.py` | DNS resolution, HTTP(S) probing, security-header audit, robots/sitemap/security.txt, TLS cert inspection, tech fingerprinting — GET/DNS only |
| Findings engine | `app.py` | Turns raw check output into severity-ranked findings (info/low/medium/high) |
| Report generator | `app.py` (`build_report_html`) | Self-contained styled HTML report with `Content-Disposition` download |
| Persistence | `data/state.json` | Scope, attestation, runs, findings, raw recon data (atomic writes) |
| UI | `static/` | Single-page app: tabs, glassmorphism design, live terminal log, report preview |
| Command cookbook | UI "Toolkit" tab | Pre-scoped command templates for external tools (subfinder, httpx, nuclei, nmap, feroxbuster…) — copy/paste only, never auto-executed |

## 3. Data flow

1. User adds **in-scope** and **out-of-scope** entries → persisted to `state.json`.
2. User signs the **authorization attestation** (checkbox + statement) → gate opens.
3. User starts a run → worker thread validates every target against the scope engine
   (out-of-scope always wins; unauthorized hosts are skipped and logged).
4. Stages 1–8 execute sequentially per host with rate limiting (inter-request delay,
   request caps, timeouts). All network I/O is DNS + HTTP(S) `GET`/`HEAD` — no
   exploitation, fuzzing, or auth-bypass attempts are performed by the app.
5. Findings are consolidated, ranked by severity, stored.
6. Report generator renders scope, attestation, methodology, findings and raw recon
   into a standalone HTML file → browser download.

## 4. Technology choices

| Choice | Rationale |
|---|---|
| Python 3 stdlib only (`http.server`, `ssl`, `socket`, `urllib`, `threading`, `json`) | Zero dependencies; runs anywhere Python exists; trivially packable to an `.exe` |
| Threaded HTTP server | Long-running recon must not block API/status polling |
| `data/state.json` (atomic tmp+rename writes) | Human-inspectable persistence, no DB dependency |
| SPA served as static files | Fast, no template engine, easy to restyle |
| PyInstaller (optional) | Single-file `.exe` distribution via `build_exe.bat` |

## 5. Safety architecture (authorized scope only)

- **Hard gate:** `/api/recon/start` returns `403` until attestation flag is set.
- **Double-key scope check:** every host is matched against out-of-scope rules first,
  then in-scope rules; no match ⇒ refused.
- **Passive-by-default:** built-in checks are DNS + `GET`/`HEAD` only, rate-limited
  (default 0.4 s inter-request delay, ≤ 50 hosts/run, 8 s timeouts, ≤ 200 KB body).
- **Explicit UA:** requests identify as `BBMToolkit/1.0 (authorized-testing)` so
  defenders can correlate traffic.
- **Active scanners external:** nuclei/nmap/sqlmap-style tooling is *never executed*
  by the app — only scoped command lines are generated for the operator to review
  and run manually inside their engagement rules.

## 6. API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | SPA |
| GET | `/api/state` | Full state snapshot |
| POST | `/api/scope` | add / remove / clear scope entries |
| POST | `/api/authorize` | set or revoke attestation |
| POST | `/api/recon/start` | start pipeline (gated) |
| POST | `/api/recon/stop` | cooperative cancel |
| GET | `/api/recon/status` | progress, stage, live log |
| GET | `/api/report/download` | HTML report attachment |
| DELETE | `/api/findings` | clear findings |

## 7. Report structure

Metadata → Authorization attestation → Scope → Methodology (recon→scan→report) →
Findings (severity-ranked table + detail cards) → Recon data per host (DNS, headers,
TLS, fingerprint, robots) → Remediation recommendations → Run log appendix.
