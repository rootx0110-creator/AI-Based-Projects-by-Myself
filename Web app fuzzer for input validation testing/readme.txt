============================================================
 WEB APP FUZZER - INPUT VALIDATION TESTING
 Version 1.0.0
============================================================

WHAT IT IS
----------
A desktop-style web tool that automatically sends security
payloads to the inputs of a web application and analyzes the
responses, so you can quickly see how well your input
validation is holding up.

It covers the most common web input-validation attack classes:

  SQL Injection          - boolean, union, error and time-based
  Cross-Site Scripting   - reflected XSS probes
  Command Injection      - separators, markers and timing sleeps
  Path Traversal (LFI)   - encoded + plain traversal sequences
  LDAP Injection         - search filter structure probes
  Server-Side Template Injection - {{7*7}} style evaluation
  SSRF                   - internal + cloud metadata addresses
  XXE / XML              - external entity extraction payloads
  Open Redirect          - redirect handling probes
  Format String          - crash probes for naive parsers
  JWT / Auth Tampering   - algorithm confusion, role spoofing

QUICK START
-----------
1. Install Python 3.10+ (https://python.org).
2. Install dependencies once:
     pip install -r requirements.txt
3. Start the application:
     run.bat       (Windows)  --or--
     python app.py
4. Open the printed URL in your browser (default http://127.0.0.1:5000).

HOW TO RUN A SCAN
------------------
1. TARGET: enter the full URL of the endpoint you want to test,
   choose the HTTP method, and add any cookies/session values.
2. SETTINGS: keep values sensible - start with 1-2 workers and
   a small delay on real systems.
3. FIELDS: list the parameter names to fuzz, e.g. "q, name, id".
   Suggestions appear automatically based on the field name.
4. PAYLOADS: pick the categories you care about, then press
   START FUZZING (or Ctrl+Enter).
5. Watch the live progress. Findings stream in sorted by
   severity. Click any row to see the full payload and evidence.
6. Download the report in HTML format from the "Report" section.

RESULTS - WHAT TO LOOK FOR
--------------------------
  High     Strong evidence: SQL errors, file disclosure,
           time-based delays, evaluated templates.
  Medium   Likely issues: unencoded reflection, server 500s,
           exception leaks.
  Low      Suspicious behaviour worth a manual look.
  OK       Payload rejected - validation looks solid.

REPORT DOWNLOAD
---------------
The whole scan (or your current severity/text filter) can be
exported as a single self-contained HTML file. It opens in any
browser, prints cleanly, and includes the severity breakdown,
category volume, scan configuration and full evidence table.

FILES
-----
  app.py             Flask server + REST API + report endpoint
  fuzzer.py          Payload library, detection engine, runner
  report.py          Self-contained HTML report generator
  templates/         UI template (friendly single-page layout)
  static/            CSS + front-end JavaScript
  architecture.md    Technical design and data flow
  state.md           Current capabilities and known limitations
  memory.md          Change log and historical decisions
  readme.txt         This file
  requirements.txt   Python dependencies
  run.bat            One-click launcher (Windows)

INTENDED USE
------------
For evaluating applications you own or are explicitly authorized
to test. All payloads are benign by design - nothing destructive
is executed. In many cases a "finding" is a lead that needs
manual verification, not proof of exploitability.

-----------------------------------------------------------------
Author: Built with opencode
License: For internal/authorized security testing only
-----------------------------------------------------------------