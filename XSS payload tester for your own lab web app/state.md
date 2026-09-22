# State

## Project status: COMPLETE (v1.0.0)

## Current functionality
- [x] Flask web app + colored UI (teal->violet gradient, amber accents)
- [x] 29 built-in XSS payloads, 6 categories
- [x] Custom payloads (one per line)
- [x] GET / POST form / POST JSON injection
- [x] Concurrent scanning with timeout + redirect control
- [x] Extra headers / cookies via header lines
- [x] Reflection detection with 5x5 decode variants
- [x] Context analysis (script block / tag / event-sink)
- [x] Verdicts & confidence + KPI summary cards
- [x] Baseline reachability probe per scan
- [x] HTML report download (self-contained file) + token re-download
- [x] Sample vulnerable lab app (lab_app.py)
- [x] PyInstaller one-file EXE build script (build_exe.ps1)
- [x] Docs: readme.txt, architecture.md, memory.md, state.md, todo.txt

## Verification performed (Windows, Python 3.14)
- Engine unit-test vs. sample lab `/search`: 27 Executable XSS,
  2 Reflected (info scanners), 0 filtered. Correct.
- POST form vs. sample lab `/form`: reflections detected.
- POST JSON / query-on-form target: correctly reports filtered
  (no reflection path) - false positives avoided.
- GET, /api/version, /api/payloads, /api/test, /api/report (HTML
  ~27.7 KB, Content-Disposition ok), /api/report/<token> all 200.
- Index page serves CSS + JS + download button.
- Report no longer aborts on CSS `%` (escaped as `%%`).

## Known limitation
- Verdicts are heuristic (no headless browser). A "Not reflected"
  result could still be DOM-based XSS on the client; a "Reflected"
  result should be confirmed manually in a browser. Lab tools only.

## How to run
```
python app.py                 # UI at http://127.0.0.1:5173
python lab_app.py             # sample target at http://127.0.0.1:5987
```

## To package the EXE
```
powershell -ExecutionPolicy Bypass -File build_exe.ps1
# -> dist\XSS-Payload-Tester.exe
```