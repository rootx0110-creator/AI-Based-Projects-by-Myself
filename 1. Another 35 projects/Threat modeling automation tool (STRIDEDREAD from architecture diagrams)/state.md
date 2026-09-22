# STRIDEForge — Current State

_Updated each working session._

## Status: BUILD COMPLETE — v1.0.0

All v1 features implemented and smoke-tested (see "Verification").

## Delivered

- [x] Flask web app entry point (`app.py`, runs on http://127.0.0.1:1234)
- [x] STRIDE/DREAD rules engine (`threat_engine/rules.py`) with ~100 threat
      templates across processes, data stores, external entities and flows
- [x] Analysis pipeline (`threat_engine/analyzer.py`):
      zone resolution, rule merge, context modifiers, residual risk,
      DREAD totals, risk tiers, summary + recommendations
- [x] Standalone HTML report generator (`threat_engine/report.py`) with
      executive summary, charts, threat register, per-threat cards,
      methodology appendix; downloads with Content-Disposition attachment
- [x] Beautiful dark glass UI (`templates/index.html` + `static/css/style.css`):
      hero dashboard, stat cards, tabs, animated accents
- [x] SVG diagram canvas (`static/js/app.js`): drag-drop nodes, data flows,
      trust boundaries, upload-image tracing background, entry-point badges,
      internet/sensitivity/control flags
- [x] Analysis tab: STRIDE / risk / text filters, DREAD bars, context notes
- [x] Report tab: live preview (iframe) + "Download HTML Report" button
- [x] Sample models embedded (E-commerce, Microservices, 3-Tier Legacy)
- [x] JSON import/export
- [x] `run.bat`, `build_exe.bat` (PyInstaller one-file build)
- [x] `requirements.txt`

## Verification performed

- [x] Python engine unit smoke-check: analyzed sample e-commerce JSON (166
      threats), correct STRIDE keys, risk tiers, summary populated
- [x] Flask server test-client: GET / 200, POST /api/analyze 200 JSON,
      POST /api/report 200 HTML with `Content-Disposition: attachment`,
      empty-model returns clean 400 error
- [x] Live server: GET /, /static/css/style.css, /static/js/app.js all 200
- [x] Headless-browser E2E (Chrome DevTools Protocol, real UI clicks):
      dashboard renders 3 samples -> load e-commerce (11 nodes, 11 flows,
      4 boundaries) -> Analyze button -> 166 threat cards, grade Critical,
      7 STRIDE chips -> risk filter (Critical = 14) -> report preview 235KB ->
      /api/report download path valid. **Zero JS errors.**
- [x] PyInstaller one-file exe builds (16.5 MB) and runs: serves the app and
      answers /api/analyze on http://127.0.0.1:1234
- [ ] Manual on-screen visual review by human (automation verified rendering,
      but pixel-level polish deserves a human look)

## Known limitations

- Classic STRIDE is heuristic; scores are methodology-based, not from a
  vulnerability feed. They are *consistent*, *repeatable*, and *explainable*
  (context_notes), which is what audit-friendly modeling needs.
- Diagram image upload is a *tracing background* only; automatic ML inference
  from arbitrary images is on todo.txt (diagram import).
- Single-user local tool; no persistence beyond JSON export.

## Next in queue (full list in todo.txt)

1. Undo/redo + snap-to-grid + auto-layout for the canvas.
2. Editable DREAD sliders + hidden rules editor.
3. Word/PDF/XLSX export of the report.
4. CVE/NVD lookup enrichment (marks threats matched to real CVEs).

## How to verify a change
1. `python -c "from threat_engine.analyzer import analyze_architecture; r=analyze_architecture({'elements':[{'id':'e1','kind':'process','type':'web_application','label':'App','flags':{'internet':True,'pii':True}},'flows':[]}); print(r['summary'])"`
2. `python app.py` then hit `http://127.0.0.1:1234`.