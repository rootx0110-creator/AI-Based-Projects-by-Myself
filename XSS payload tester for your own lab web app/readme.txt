# ============================================================
#  XSS PAYLOAD TESTER - for your own lab web app
#  Authorized use only. Test only resources you own or have
#  permission to scan.
# ============================================================

WHAT THIS IS
------------
A local web tool that fires a library of XSS payloads at a
target web application (your lab app), watches the responses,
and tells you whether each payload was reflected, whether it
landed in a dangerous context (script block, event handler),
and whether the payload appears executable.

It also lets you download the whole scan as a standalone HTML
report, so you can attach findings to your lab notes or exams.

FEATURES
--------
* 29 built-in XSS payloads across 6 categories:
    Basic, Tag/Event, JS Context, Encoding, Polyglot, Scanner
* Custom payloads (one per line)
* Injection via:
    GET query string
    POST form body
    POST JSON body
* Configurable timeout, concurrency, redirect following,
  extra headers (e.g. Cookie)
* Smart detection:
    - URL/HTML/JS-unicode decoding of payloads AND responses
    - reflection point + context analysis (script block / tag /
      after event-handler sink)
    - marker-based verdicts: Executable XSS, Reflected in
      event-sink, Reflected, Partial reflection, Filtered
* Downloadable HTML scan report (self-contained file)
* Colored UI (teal->violet gradient, amber accents) - not black/white

QUICK START (run as web app)
----------------------------
1. Install Python 3.10+ (https://python.org)
2. In this folder run:

       pip install -r requirements.txt
       python app.py

3. Browser opens http://127.0.0.1:5173  (or open it manually)
4. Enter your lab app URL (e.g. http://127.0.0.1:5000/search)
5. Choose the parameter to inject, method, and optional custom
   payloads, then click "Run XSS Scan"
6. Review the KPI cards and the results table
7. Click "Download HTML Report" to get xss-report-<timestamp>.html

BUILD A STANDALONE EXE (optional)
----------------------------------
1. Install PyInstaller:  pip install pyinstaller
2. PowerShell (in this folder):

       powershell -ExecutionPolicy Bypass -File build_exe.ps1

3. The EXE appears at  dist\XSS-Payload-Tester.exe
4. Double-click it. The console prints the URL; open it in a
   browser. (Auto-open is disabled in frozen EXE mode so the
   console stays visible.)

SAMPLE LAB APP (try it immediately)
-----------------------------------
A tiny intentionally-vulnerable Flask app is included so you can
verify the tool works before pointing it at your own lab:

    python lab_app.py          # runs on http://127.0.0.1:5987

Then test the URL:
    http://127.0.0.1:5987/search?er=1&aaa=2     (param: q, GET)

FILES IN THIS FOLDER
--------------------
  app.py         Flask app: UI + API endpoints
  engine.py      Request building + XSS detection engine
  payloads.py    Built-in payload library
  report.py      Self-contained HTML report generator
  lab_app.py     Sample vulnerable lab app (for verification)
  templates/     UI template (index.html)
  static/        UI styles + client JS
  requirements.txt
  build_exe.ps1  PyInstaller one-file EXE build
  architecture.md
  memory.md
  state.md
  todo.txt
  readme.txt     (this file)

API ENDPOINTS
-------------
  GET  /                 UI
  GET  /api/payloads     payload catalog (JSON)
  POST /api/test         run a scan (JSON config) -> JSON results
  POST /api/report       generate + download HTML report (JSON run)
  GET  /api/report/<token>  re-download last report by token

EXAMPLE /api/test REQUEST
-------------------------
{
  "url": "http://127.0.0.1:5987/search?er=1&aaa=2",
  "param": "q",
  "method": "GET",
  "location": "query",
  "custom_payloads": ["<script>alert(1)</script>"],
  "headers": ["Cookie: session=abc"],
  "timeout": 10,
  "concurrency": 4,
  "follow_redirects": true
}

LEGAL & SAFETY
--------------
* This tool is for testing applications YOU own or are explicitly
  authorized to test. Scanning systems without permission may
  violate laws.
* The engine never renders/executes returned HTML; response
  snippets in the UI and report are shown as escaped text, and
  any <script> blocks found are redacted in reports.
* Verdicts are heuristic. Always confirm a finding in a browser
  within your lab environment before drawing conclusions.