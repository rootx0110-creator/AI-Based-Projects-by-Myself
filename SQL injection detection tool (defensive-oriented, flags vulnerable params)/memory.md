# SQLInspect — Memory / Decision Log

Running notes on design decisions, trade-offs and open items.

## Decisions

### 1. Skew: defensive scanner, not an attack tool
Violation distance is large on purpose. The tool's job is to *flag vulnerable
parameters* and export a report, not to exfiltrate. Live probing therefore:
- is OFF by default,
- requires a consent checkbox enforced server-side,
- uses a bounded probe budget (200/target),
- injects only canonical, benign test payloads (small `SLEEP` delays, harmless
  boolean probes, read-only error text probes).

### 2. Stack: Flask + HTML/CSS/JS, offline-friendly
- Chosen because `flask` is already installed; a single-process local tool needs no
  build step.
- **No CDN dependencies**: every asset is local, so the UI, the report and even the
  downloadable HTML export work on an air-gapped workstation (the use case for a
  defensive tool). Charts (gauge, bars) are hand-rolled SVG/CSS rather than a chart lib.
- `reportlab` chosen for the PDF export (already available) to avoid heavyweight
  HTML-to-PDF engines.

### 3. Scoring model
- Each confirmed technique contributes a fixed weight, capped per technique
  (`MAX_TECH_CONTRIB`) so no single signal dominates.
- Score clamped 0–100 → risk levels: Low <25, Medium <50, High <75, Critical ≥75.
- Target risk = max over parameters (worst-case), which is the honest reading for
  a defensive tool ("one bad param = one vulnerability to fix").

### 4. Raw request parser scope
Supports the 90% case: GET/POST/PUT/DELETE/PATCH, urlencoded bodies, JSON bodies,
cookie pairs, Fiddler/ZAP-style request lines. Multipart is best-effort (regex).
Fragmented/incomplete requests are rejected with a clear error rather than guessed at.

### 5. Report as in-memory + streamed
No files are persisted to disk (`state.md`). This keeps the tool's footprint
invisible and avoids writing potentially sensitive findings to the filesystem.

## Open items / future work
- [ ] Persist report store to SQLite with TTL if multi-user use is ever needed.
- [ ] Add WAF fingerprint / evasion-ratio analysis to the evidence panel.
- [ ] Export findings as a Splunk/Elastic-friendly JSON line format.
- [ ] Add configurable custom payload lists (user-supplied `.txt` corpus).
- [ ] HTTP/2 + TLS fingerprinting for more precise DBMS detection in live mode.

## Known limitations
- Offline mode cannot confirm a *confirmed-explainable* injection; it flags risk.
  High scores mean "review now", not "proof".
- Boolean/time live tests assume a consistent target; noisy networks can cause
  false negatives on time-based probes (latency threshold 1500 ms).
- Multipart body fields are extracted via regex and truncate file payloads.
- The app binds an unauthenticated local web server; do not expose it beyond
  127.0.0.1.