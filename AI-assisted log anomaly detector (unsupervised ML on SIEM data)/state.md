# State — current status snapshot

## Build status
| Item                                        | Status |
|---------------------------------------------|--------|
| Diagnostic docs (architecture/memory/readme)| done   |
| Ingestion (CSV/JSON/JSONL/Syslog/CEF/raw)   | done   |
| Feature engineering (behavioural+text)      | done   |
| Detector ensemble (IF, LOF, OCSVM, AE)      | done   |
| Burst component + ensemble blend            | done   |
| Cluster-confidence bonus + capped flags     | done   |
| Incidents + feature explanations            | done   |
| HTML report generator (standalone)          | done   |
| Flask API (analyze/report/sample/health)    | done   |
| Classy navy/gold/turd UI                    | done   |
| Sample generator (5 planted behaviours)     | done   |
| requirements.txt, EXE build bat             | done   |
| Bundled EXE (dist\SentinelForge.exe)        | done   |

## Verification
- Inline pipeline `generate -> normalize -> build_feature_matrix ->
  run_detection` runs clean on the seed=42 sample (1904 events).
- All five planted behaviours recovered and ranked above normal traffic.
- Live-server smoke test passed on 127.0.0.1:8600: /api/health OK, index OK,
  sample analyze (1904 ev / 95 flagged / 15 incidents / 3 models / 275
  features), report endpoint returned self-contained HTML verified by content
  grep (no stray `params.get`, no double-escaped `&middot;`, text features
  explain as "unusual term/blend signature", format card populated with CSV).
- Uploaded CSV path verified end-to-end with curl (multipart upload of
  /api/sample download -> /api/analyze -> summary.format=CSV -> /api/report).
- Remaining manual steps: JSON/Syslog/CEF upload paths, double-click report
  render, EXE build via build_exe.bat.

## Electron/edit highlights
- 2026-09-21: initial scaffold, pipeline tuned (D1–D4 in memory.md).
- 2026-09-21: live smoke test; fixed report footer literal `{params.get}`,
  double-escaped `&middot;` in incidents, meaningless `text.*` reasons,
  and missing default format label (`Synthetic CSV (bundled sample)`).

## Next steps (see todo.txt)
- Nothing pending; optional ideas in todo.txt backlog (SSE streaming, JSON
  explanation export, baseline comparison).