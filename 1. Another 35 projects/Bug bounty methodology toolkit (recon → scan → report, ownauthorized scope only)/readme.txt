================================================================================
 BUG BOUNTY METHODOLOGY TOOLKIT  —  recon -> scan -> report
 OWN / AUTHORIZED SCOPE ONLY
================================================================================

WHAT IT IS
----------
A local web application that structures a bug-bounty engagement into three
phases — Recon, Scan (passive checks), Report — with two hard safety rails:

  1. AUTHORIZATION GATE : the pipeline refuses to start until you sign an
                          attestation that you are authorized to test the
                          listed targets.
  2. SCOPE ENGINE       : every target is checked against your in-scope and
                          out-of-scope list (out-of-scope always wins).
                          Anything else is refused and logged.

Built-in checks are PASSIVE ONLY (DNS lookups + HTTP GET/HEAD):
  DNS records (A/AAAA/MX/NS/TXT/CNAME), HTTP probing, security-header audit,
  robots.txt / sitemap.xml / security.txt discovery, TLS certificate
  inspection, technology fingerprinting.

Aggressive tools (nuclei, nmap, feroxbuster, sqlmap, subfinder, ...) are
NEVER executed by the app. The "Toolkit" tab generates pre-scoped command
lines that you review and run manually under your engagement rules.


REQUIREMENTS
------------
  Python 3.10+ (tested on 3.14). No pip packages needed for normal use.


HOW TO RUN (web application)
----------------------------
  1. Open a terminal in this directory.
  2. Run:   python app.py
  3. Your browser opens http://127.0.0.1:8765
     (use  python app.py --no-browser  to skip auto-open;
      use  python app.py --port 9000  for another port)


HOW TO BUILD AN .EXE (optional)
-------------------------------
  1. pip install pyinstaller
  2. Run:   build_exe.bat
  3. Find dist\BBMToolkit.exe — distribute that single file.
  (The exe behaves exactly like `python app.py`.)


QUICK START (in the UI)
-----------------------
  1. SCOPE tab  -> add your authorized targets (domain, *.wildcard, IP,
                   CIDR, or URL). Add out-of-scope entries too.
  2. Check the attestation box, type the confirmation statement, submit.
  3. PIPELINE tab -> "Start recon run". Watch the live terminal log.
  4. FINDINGS tab -> review severity-ranked findings.
  5. REPORT tab   -> "Download HTML report" (self-contained file, ready to
                     attach to a submission or share with the program).


DIRECTORY LAYOUT
----------------
  app.py               backend: server, scope engine, pipeline, report gen
  static/              frontend SPA (index.html, css, js)
  data/state.json      persisted scope, attestation, runs, findings
  reports/             generated HTML reports
  architecture.md      system architecture
  memory.md            project decisions / context for future sessions
  state.md             current build/runtime state
  todo.txt             checklist / future work
  readme.txt           this file
  build_exe.bat        PyInstaller packaging script


SAFETY / ETHICS
---------------
  Use ONLY on targets you own or are explicitly authorized to test
  (bug bounty programs, written scope agreements, your own lab).
  The tool identifies itself with User-Agent:
      BBMToolkit/1.0 (authorized-testing; +local)
  so target defenders can correlate traffic. Respect program rules:
  rate limits, testing windows, and prohibited techniques supersede
  anything this toolkit does.


TROUBLESHOOTING
---------------
  - Port in use         : python app.py --port 8888
  - "403 not authorized": complete the attestation on the Scope tab first
  - Target skipped      : it did not match in-scope (or matched out-of-scope)
  - Nothing on port 443 : TLS stage logs a warning, run continues
  - Reset everything    : stop the app, delete data\state.json, restart

================================================================================
