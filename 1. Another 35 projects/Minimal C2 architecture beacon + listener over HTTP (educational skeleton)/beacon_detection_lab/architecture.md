# Beacon Detection Lab — Architecture

**Purpose:** defensive, educational tool that detects HTTP beaconing (periodic
callback) patterns in traffic captures and web-server logs — the *analysis* side
of the technique, not the technique itself.

**Out of scope by design:** anything that beacons, implants, remote control,
command distribution, payload delivery, or executable packaging. This project
analyzes evidence; it never generates it.

---

## 1. High-level design

```
                 ┌──────────────────────┐
  input sources  │                      │  findings (JSON)
  ──────────────►│     analyzer.py      │──────────────► CLI stdout
  • access.log   │  parse → group →     │
  • capture.pcap │  score → render      │──────────────► report.html
                 └──────────▲───────────┘                (self-contained)
                            │ import
                 ┌──────────┴───────────┐
                 │     dashboard.py     │   browser @ 127.0.0.1:8000
                 │  upload → analyze →  │──────────────► results table
                 │  serve → download    │──────────────► /report?id=N (HTML)
                 └──────────▲───────────┘──────────────► /report?id=N&format=json
                            │ writes
                 ┌──────────┴───────────┐
                 │  make_sample_data.py │   synthetic, safe test data
                 │  → samples/*.log/pcap│   (no sockets used)
                 └──────────────────────┘
```

## 2. Modules

| Module | Responsibility |
|---|---|
| `analyzer.py` | Parsers (combined access log, classic PCAP), grouping, scoring, HTML report, CLI |
| `dashboard.py` | `http.server`-based loopback UI: multipart upload, results table, report download |
| `make_sample_data.py` | Deterministic synthetic traffic (benign + beacon-like) as log text and raw PCAP bytes |
| `detections/` | Educational Sigma + YARA rules expressing the same logic for SIEM/EDR teams |

## 3. Data flow (analyzer)

1. **Ingest** — `parse_access_log()` (regex over combined log format) or
   `parse_pcap()` (struct-based classic pcap reader; Ethernet → IPv4 → TCP →
   HTTP request line / response status). Events normalize to:
   `{src, ts, method, path, status, size, ua, dst?}`.
2. **Group** — events bucketed by `(source, destination)`.
3. **Score** — `score_group()` computes, per group:
   - `interval` — median gap between consecutive requests
   - `jitter` — coefficient of variation (stdev/mean) of gaps
   - `gini` — Gini impurity of the gap distribution (0 = perfectly periodic)
   - path-repetition bonus when one URI dominates
   - score 0–100; verdict: **high ≥ 70**, **medium ≥ 45**, **low < 45**
4. **Render** — `render_report()` emits a single-file HTML report
   (inline CSS, summary cards, candidates table, methodology note).

## 4. Dashboard internals

- `ThreadingHTTPServer` bound to **127.0.0.1**, first free port 8000–8029
  (loopback only; `dashboard.start_server()` is also the exe entry).
- `GET /` — upload form (threshold selector, auto-download toggle).
- `POST /analyze` — minimal stdlib multipart parser; file → temp file →
  parser → `analyzer.analyze()`; results rendered server-side.
- `GET /report?id=N` — downloaded attachment (`..._beacon_report.html`),
  `&format=json` returns machine-readable findings.
- Reports held in an in-memory store (cleared on restart).

## 4b. Executable packaging (Windows)

| Artifact | Entry point | Build |
|---|---|---|
| `dist/BeaconDetectionLab.exe` | `launcher.py` (windowed; opens browser, logs fatal errors to `%TEMP%/BeaconDetectionLab.log`) | `pyinstaller --onefile --windowed --name BeaconDetectionLab launcher.py` |
| `dist/beacon-analyzer.exe` | `analyzer.py` CLI | `pyinstaller --onefile --name beacon-analyzer analyzer.py` |

`build.bat` runs both plus a compile check. The exes bundle the same stdlib-
only code; no behavior differs from `python dashboard.py` / `python analyzer.py`.

## 5. Scoring rationale

Real beaconing leaves a fingerprint that humans can't fake accidentally:
machine-regular gaps, near-identical request shapes, and stable response sizes.
Benign traffic (browsing, updates) is bursty and heterogeneous. The three
statistics (median interval, jitter CV, Gini) are cheap, robust, and easy to
explain in a report — which is the point of a teaching tool.

## 6. Limitations (deliberate, documented)

- PCAP path does no TCP stream reassembly; very segmented or encrypted flows
  are out of reach. Good enough for lab captures.
- HTTPS hides paths/sizes unless you proxy-terminate; interval/jitter logic
  still works on connection-level logs (e.g., netflow-style).
- IPv6, link types other than Ethernet, and pcapng are not parsed.

## 7. Extension points

- New input formats: add a `parse_*()` returning the same event dict.
- New signals (e.g., user-agent rarity, response-size variance, dead-hour
  activity): extend `score_group()`; the report picks fields up automatically.
- SIEM export: `--json` findings are one dict per candidate, ISO timestamps.
