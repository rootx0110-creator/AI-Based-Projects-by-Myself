COMPLIANCE AUTOMATION SUITE
ISO 27001:2022 | Bangladesh Bank ICT Security Guideline v2.0 | NIST CSF 2.0
============================================================================

WHAT IS THIS?
-------------
A local-first web application (and EXE) that lets a bank, NBFI or any
organization assess its security controls against three frameworks at once:

  * ISO/IEC 27001:2022 Annex A  - all 93 controls
  * Bangladesh Bank ICT Security Guideline v2.0 - 18 domains (B-01..B-18)
  * NIST Cybersecurity Framework 2.0 - 22 categories

It computes compliance scores and maturity levels, produces a prioritized
gap analysis with risk scores, maps any control to its equivalents in the
other frameworks, and generates a downloadable, auditor-ready HTML report.

QUICK START (WEB APP)
---------------------
Requirement: Python 3.10+ (no third-party packages needed)

  python run.py

The server starts on http://127.0.0.1:9999 and your browser opens
automatically. Other options:

  python run.py --port 9000
  python run.py --no-browser

BUILD THE WINDOWS EXE
---------------------
  powershell -ExecutionPolicy Bypass -File build_exe.ps1

Produces dist\ComplianceSuite.exe (single file, no Python needed on the
target machine). When run, it starts the server and opens the browser.
Assessment data is stored in %APPDATA%\ComplianceSuite.

USING THE APP
-------------
  Dashboard       - compliance % per framework, maturity level, status mix
  Control Register- set status (Implemented / Partially / Planned /
                    Not Implemented / N/A), owner and notes per control;
                    bulk-update selected rows
  Control Mapper  - pick any control and see its equivalents in the other
                    two frameworks (BB domains are the bridge)
  Gap Analysis    - open findings ranked by risk with recommendations
  Crosswalk       - BB ICT domain to ISO/NIST coverage matrix
  Reports         - preview and download the HTML report
                    (also: "Download HTML Report" button in the top bar,
                     or open http://127.0.0.1:9999/api/report)

Save the report with Ctrl+S / "Save as..." in the browser tab that opens.
The report is fully self-contained (inline CSS) and works offline.

WHERE YOUR DATA LIVES
---------------------
  Web app:   data\compliance_data.json   (next to run.py)
  EXE:       %APPDATA%\ComplianceSuite\compliance_data.json

Delete that file (or use POST /api/reset) to start a fresh assessment.

PROJECT FILES
-------------
  run.py            - dev entry point
  exe_start.py      - EXE entry point
  build_exe.ps1     - PyInstaller build script
  app\server.py     - HTTP server + JSON API
  app\services.py   - scoring, gaps, mapping logic
  app\report.py     - HTML report generator
  app\store.py      - JSON persistence + audit log
  app\data.py       - control catalogs + crosswalk (edit here to extend)
  app\web\          - the UI (index.html, app.css, app.js)
  architecture.md   - how it all fits together
  state.md          - current project status
  memory.md         - engineering notes for future sessions
  todo.txt          - roadmap

DISCLAIMER
----------
The bundled catalogs and crosswalks are practical audit-oriented mappings
for automation purposes and do not replace the official standards. Always
validate against the published ISO standard, Bangladesh Bank circulars and
NIST publications for formal certification or regulatory submissions.
