==============================================================
 SQLInspect - SQL Injection Detection Tool
 Defensive-oriented: flags vulnerable parameters
==============================================================

QUICK START (web app)
--------------------------------------------------------------
 1. install:      pip install -r requirements.txt
 2. run:          python app.py
 3. open:         http://127.0.0.1:5000

QUICK START (standalone exe)
--------------------------------------------------------------
 Run build.bat to produce a single-file "SQLInspect.exe" using
 PyInstaller, then run the exe and open http://127.0.0.1:5000
 (your browser is launched automatically).

WHAT IT DOES
--------------------------------------------------------------
 Input modes:
  - URL / endpoint:     paste a URL (or several), query-string
                        parameters are extracted and scored.
  - Raw HTTP request:   paste a Fiddler / ZAP / curl-style request.
                        Handles query, POST form bodies, JSON bodies
                        and cookies.
  - Log / list upload:  drop a web-server access log or a list of
                        URLs (one per line, # for comments).

 Detection engine (10 techniques):
  payload signature, syntax pattern, DBMS error signature, keyword
  density, meta-character context, boolean-blind condition, time-
  based probe, stacked queries, DBMS fingerprint, encoding
  obfuscation.

 Live probing (OPTIONAL, default OFF):
  Confirms error-based / boolean-blind / time-based injection by
  sending a small, bounded set of canonical probes to the target.
  Requires explicit consent checkbox. ONLY scan systems you are
  authorised to test.

 Output:
  - score per parameter (0-100) + risk level
    (Safe / Low / Medium / High / Critical)
  - evidence and matched technique for every flag
  - per-target and overall assessment, DBMS hints, recommendations
  - scan history (in-memory, current session)

 REPORT DOWNLOAD
   Every scan can be exported from the results panel as:
    PDF, CSV, JSON, standalone HTML
   The "Open full report" view also offers all four downloads.

DEFENSIVE GUARDRAILS
--------------------------------------------------------------
 * Live probing is off by default and requires consent.
 * Offline mode makes zero network requests.
 * Probe count is bounded per target (default 200).
 * Reports are kept in memory only (never written to disk).
 * Runs on 127.0.0.1 only.

PROJECT FILES
--------------------------------------------------------------
 app.py                Flask application + API routes
 core/                 detection engine (payloads, parser,
                       analyzer, scanner)
 reports/              export generators (PDF/CSV/JSON/HTML)
 templates/ static/    web UI
 architecture.md       architecture overview
 state.md              runtime state & data flow
 memory.md             decision log / working notes
 readme.txt            this file

Disclaimer: for security labs and authorised testing only.