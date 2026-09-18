# Memory — Web App Fuzzer for Input Validation Testing

> Persistent log of decisions, changes and rationale.

## 2026-09-16 · v1.0.0 — Initial release

### Why this tool exists
Requested as "a web app fuzzer for input validation testing" that ships with
`architecture.md`, `state.md`, `memory.md` and `readme.txt`, has a friendly UI,
and offers an **HTML report download**. Chose a local **web application** (not
a compiled EXE) because it runs anywhere Python is installed, needs no build
toolchain on Windows, and the browser UI is the friendliest surface to polish.

### Decisions taken (and why)

1. **Flask + vanilla JS, no front-end build step.**
   Keeps the project small, dependency-light and auditable. The environment
   already had Flask and `requests` installed. No Node build needed → the
   "EXE or web app" requirement is satisfied by a double-click launcher
   (`run.bat`) that starts the server.

2. **In-memory scan registry with background threads.**
   Scan = POST `/api/scan` → validator → daemon worker thread → client polls a
   token. Simpler to reason about than celery/async, fine for a local tool, and
   `threading.Event` gives a clean cancel path.

3. **Weighted risk model in `analyze_response`.**
   Instead of naive "did any signature match", each signal adds to a risk score
   that maps to severity. This lets results sort by impact and produces the
   friendly summary cards / security grade in the report.

4. **Time-based detection uses a baseline probe.**
   A benign request is timed first; delays are judged against that baseline and
   an absolute threshold (≈5 s) so slow networks don't produce false positives.

5. **HTML report generated server-side from posted JSON** (`POST /api/report`).
   This keeps one code path: whatever the UI currently shows (including filters)
   becomes the report. A token-based route (`GET /api/report/<token>`) also
   exposes the server's full copy for scripting.

6. **Safety-biased payload set.**
   No destructive commands, bounded sleeps, benign marker text
   (e.g. `ECHOED_PAYLOAD`). Rationale: the tool is for authorized testing of
   input *validation*, not exploitation.

7. **Bulk category shortcuts persisted to `localStorage`.**
   Testing UX detail: "enable all / core web set" plus remembering the last
   selection across page reloads.

### Known pitfalls recorded for future work
- Truly **blind** injection is hard to detect with pure response analysis;
  time-based probes are the main blind signal. (see `state.md` §3)
- Reflection is reported as a **lead**, never as confirmed exploitability.
- Everything is in-memory; a restart clears the scan registry.

### File map
```
app.py          Flask API + scanner orchestration + report endpoints
fuzzer.py       payloads, detection, runner
report.py       HTML report generator
templates/      index.html (single page UI)
static/         style.css, app.js
readme.txt      user guide
architecture.md technical design
state.md        status + limitations + backlog
memory.md       this log
run.bat         Windows launcher
requirements.txt  python deps
```

### Versioning
1.0.0 — initial release.