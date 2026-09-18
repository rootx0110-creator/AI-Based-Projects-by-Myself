====================================================================
 LOG ANONYMIZER & REDACTOR  v1.0.0
 For Safe Log Sharing
====================================================================

 WHAT IT DOES
 ------------
 Detects sensitive data inside log files and replaces it with safe
 placeholders so you can share logs with support teams, vendors, or
 AI assistants without leaking personal or secret information.

 Detected patterns:
   - IPv4 / IPv6 addresses
   - E-mail addresses
   - Phone numbers
   - Credit / debit card numbers (PAN)
   - Social Security numbers (SSN)
   - UUIDs
   - JWT tokens and bearer tokens
   - API keys & secrets (AWS, Stripe, GitHub, Slack, Google...)
   - Credentials in URLs (user:pass@)
   - Password literals (password=..., secret=..., token=...)
   - MAC addresses
   - Geo coordinates (lat= / lon=)
   - Usernames / user IDs
   - AWS ARNs

 Redaction strategies (choose one):
   [1] Partial Mask  -> jo***, 192***, jan***
   [2] Full Redact   -> {TAG-REDACTED}
   [3] SHA-256 Hash  -> {TAG-<digest>}  (same input => same token)
   [4] Pseudo Tokens -> {TAG:EM0001}    (sequential anonymized IDs)

 Security guarantees:
   - 100% local processing - nothing ever leaves your machine
   - No network calls, no telemetry, no hidden uploads
   - Original values are never written to disk
   - Deterministic output for mask / full / hash strategies

--------------------------------------------------------------------
 HOW TO USE
 ----------
 1. Redact tab:  paste or load (Open File) your log.
 2. Press [ Anonymize ].
 3. Copy the sanitized output, or save it as a .log/.txt file.
 4. Report tab:  [ Download HTML Report ] for an audit of what was
    redacted, with counts, samples and configuration used.

 Options tab: toggle which categories to redact, and pick a strategy.

--------------------------------------------------------------------
 HOW TO BUILD THE EXE
 --------------------
 1. python -m pip install -r requirements.txt
 2. python build_exe.py
 3. The exe appears in:  dist\LogAnonymizer.exe

 (optional) put an icon at assets\app.ico to brand the window.

--------------------------------------------------------------------
 PROJECT FILES
 -------------
 app.py           - main desktop application
 core/redactor.py       - detection + redaction engine
 core/html_report.py    - HTML report generator
 build_exe.py           - PyInstaller build wrapper
 requirements.txt       - python dependencies
 architecture.md        - system design documentation
 state.md               - behavioral contract / invariants
 memory.md              - design decisions & bug log
 sample\sample.log      - example log used for live testing

--------------------------------------------------------------------
 REQUIREMENTS
 ------------
 Python 3.9+  |  customtkinter>=5.2  |  PyInstaller>=6 (build only)

 Run from source:   python app.py
--------------------------------------------------------------------
 (c) 2026 - made for safe log sharing.
====================================================================