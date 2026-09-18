================================================================================
                  PHISHING EMAIL ANALYZER  -  README
              Header / URL / Attachment Triage Tool
================================================================================

OVERVIEW
--------
A desktop Windows application that triages suspicious emails by examining three
primary vectors:

    1. EMAIL HEADERS  - sender spoofing, SPF/DKIM/DMARC, reply-to abuse
    2. EMBEDDED URLS  - obfuscation, phishing lookalike domains, dangerous TLDs
    3. ATTACHMENTS    - dangerous extensions, double-extensions, SHA-256/MD5
                        fingerprints for malware-hash lookups

The tool produces a risk score (0-100) with a verdict and can export a complete,
style-styled HTML report for incident documentation.


================================================================================
REQUIREMENTS
================================================================================
- Windows 7 / 10 / 11
- Python 3.9+ (only needed if running from source; the .exe needs no runtime)

Dependencies (auto-bundled into the .exe):
    customtkinter      -> modern dark-themed GUI
    pyinstaller        -> packaging (build-time only)


================================================================================
RUNNING THE APPLICATION
================================================================================
Option A - Pre-built executable
    dist/PhishingEmailAnalyzer.exe
    Just double-click. No installation required; single portable file.

Option B - From source
    python main.py

Input email formats:
    - .eml  (most mail clients: export from Outlook, Thunderbird, Gmail, ...)
    - Paste raw source / MIME text directly into the input area.


================================================================================
USING THE TOOL
================================================================================
1. Launch the application.
2. Click "Load Email" and pick a .eml file (or paste email source into the box).
3. Click "Analyze Email".
4. The DASHBOARD shows:
      - Risk gauge (SAFE -> CRITICAL)
      - Verdict badge + score
      - Summary cards for Headers / URLs / Attachments
5. Switch tabs for forensic detail:
      - HEADERS  : normalized + raw headers, spoofing indicators
      - URLS     : every URL with classification (benign/suspicious/malicious)
      - ATTACHMENTS : filename, size, extension analysis, SHA-256 & MD5
6. Click "Export HTML Report" to save a styled, standalone report for evidence.


================================================================================
REPORT EXPORT
================================================================================
- Reports are saved as HTML files (by default to ./reports/).
- Every report contains:
      * Analysis meta (timestamp, source filename)
      * Risk summary with score + verdict
      * Header findings table
      * URL table with per-URL classification
      * Attachment table with hashes
      * Raw header block (read-only view)
- The report is a single self-contained file (CSS embedded) that opens in any
  browser and can be printed to PDF.


================================================================================
RISK SCORING MODEL
================================================================================
Signals and weights (see architecture.md for details):

    Spoofed sender indicator      +40
    Dangerous URL detected        +35
    Malicious attachment          +40
    Suspicious attachment         +20
    Missing SPF/DKIM/DMARC        +15
    Suspicious header anomaly     +10

Scores are capped at 100.

Verdict mapping:
    0-14   -> SAFE
    15-39  -> LOW RISK
    40-69  -> MODERATE
    70-89  -> HIGH RISK
    90+    -> CRITICAL


================================================================================
PROJECT LAYOUT
================================================================================
    main.py                  Entry point
    app.py                   GUI application (CustomTkinter)
    engine/
        email_parser.py      .eml / MIME parsing
        header_analyzer.py   header forensics
        url_analyzer.py      URL extraction + classification
        attachment_analyzer.py attachment metadata + hashing
        risk_scorer.py       weighted scoring + verdict
    utils/
        report_generator.py  HTML report builder
        state.py             persistent app state / history
    assets/                  icons / fonts
    architecture.md          system design document
    state.md                 application state machine
    memory.md                resource & memory usage document


================================================================================
PRIVACY & SAFETY
================================================================================
- 100% OFFLINE : zero network calls. URL analysis is heuristic, local only.
- Attachments are NEVER executed or opened. Only metadata and hashes are read.
- No email body is persisted to disk by the tool (only optional HTML reports,
  which are created explicitly by the user).


================================================================================
BUILDING THE EXECUTABLE (for developers)
================================================================================
    pip install -r requirements.txt
    python build.py            # runs PyInstaller with the bundled spec

Output:  dist/PhishingEmailAnalyzer.exe


================================================================================
TROUBLESHOOTING
================================================================================
- ".msg" (Outlook) files are not natively MIME; export to .eml first.
- Very large emails (>20 MB) parse slowly; consider trimming the source.
- If SmartScreen warns on the .exe, it is unsigned; click "More info -> Run
  anyway" on devices you trust.

================================================================================
Version 1.0.0  |  License: MIT  |  For educational / defensive security use.
================================================================================