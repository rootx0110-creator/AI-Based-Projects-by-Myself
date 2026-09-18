================================================================================
 ENDPOINT HARDENING & COMPLIANCE CHECKER
 CIS-style benchmark assessment for Windows endpoints (Linux/macOS optional)
 Version 1.0.0
================================================================================

WHAT IS THIS?
-------------
A desktop application that audits a Windows endpoint against CIS Benchmark
style hardening rules, shows the results in a modern dark dashboard, and
generates professional HTML and PDF compliance reports.

It is 100% READ-ONLY. It never changes a single setting on your machine.
It only READS registry values, runs inspection-only commands, and looks at
service states. Remediation steps shown in reports are suggestions for a
human to review - they are never executed by this tool.

--------------------------------------------------------------------------------
QUICK START (END USERS)
--------------------------------------------------------------------------------

1. Get the app
   - Prebuilt:  dist/HardeningChecker.exe   (single file, no install needed)
   - Or run from source:  python run.py      (requires Python 3.10+)

2. Run it
   - Double-click HardeningChecker.exe
   - Optional: right-click -> "Run as administrator" to unlock the few checks
     that need elevated privileges. Without elevation those checks are simply
     marked SKIPPED - nothing breaks.

3. Click "Run Scan" in the sidebar -> "Start scan"
   - Choose profile: Level 1 (essential) or Level 2 (strict, adds L2 rules)
   - Watch progress; typical scan takes 30-120 seconds.

4. Review results
   - DASHBOARD: score gauge, pass/fail tiles, status donut, category bars
   - FINDINGS:  filter by severity/status, free-text search, click a row to
                see description, rationale, evidence, and remediation guidance

5. Generate reports (Reports page)
   - HTML report: self-contained file, opens in any browser, includes
     live filtering and evidence sections
   - PDF report:  print-ready paginated document for auditors/management
   - JSON / CSV:  machine-readable exports for SIEM/GRC pipelines

--------------------------------------------------------------------------------
COMMAND LINE (CI / AUTOMATION)
--------------------------------------------------------------------------------

The same engine is available headless:

    HardeningChecker.exe --cli scan --json out.json --html out.html --pdf out.pdf
    HardeningChecker.exe --cli rules                 # list rules for this machine

From source the CLI is richer:

    python run.py --cli scan --profile l1 --json r.json --html r.html --pdf r.pdf
    python run.py --cli scan --profile l2 --no-info --quiet
    python run.py --cli rules --profile l1

Exit codes:  0 = fully compliant,  1 = failures/errors found,  2 = tool error.
This makes it safe to drop into CI or scheduled compliance jobs.

--------------------------------------------------------------------------------
WHAT GETS CHECKED (45+ WINDOWS RULES)
--------------------------------------------------------------------------------

  Account Policies ....... password length/history/age/complexity, lockout
                           thresholds, Guest account, local admin count
  User Account Control ... Admin Approval Mode, prompt behaviors, secure
                           desktop
  LSA Protection ......... RunAsPPL, LM compatibility (NTLMv2 only),
                           NTLM 128-bit session security
  BitLocker .............. OS volume protection, recovery-key escrow
  Windows Defender ....... real-time protection, behavior monitoring,
                           signature freshness, Tamper Protection
  Firewall ............... domain/private/public profiles, default inbound
                           action, dropped-packet logging
  Remote Desktop ......... NLA required, High encryption, disconnect timeout
  Audit Policy ........... logon/credential failures, process creation,
                           PowerShell script-block logging
  Network ................ SMBv1 disabled, SMB signing, anonymous
                           enumeration, LLMNR, WPAD
  Session Lock ........... machine inactivity limit, screen-saver lock
  Updates/Devices ........ auto-reboot behavior, CD/DVD allocation (L2)

Linux and macOS rule modules ship as optional extras and are picked
automatically when the tool runs on those platforms.

--------------------------------------------------------------------------------
SCORING MODEL
--------------------------------------------------------------------------------

Each rule carries a severity weight:
    critical=10, high=6, medium=3, low=1, info=0

    score = achieved_weight / applicable_weight * 100

where PASS earns full weight, ERROR earns half (unknown, not penalized), FAIL
earns none, and NOT-APPLICABLE / SKIPPED / MANUAL checks are excluded from the
denominator entirely.

Grades:  A+ >=95 | A >=90 | B >=80 | C >=70 | D >=60 | E >=50 | F <50

--------------------------------------------------------------------------------
SAFETY MODEL (PLEASE READ)
--------------------------------------------------------------------------------

- Registry access uses KEY_READ only. Nothing is ever written.
- Commands run are inspection-only: net accounts, auditpol /get,
  sshd -T, sysctl -n, Get-MpComputerStatus, Get-BitLockerVolume, etc.
- No services are started/stopped, no files are modified, no network
  connections are made beyond localhost probing for IP enumeration.
- Remediation scripts in reports are TEXT ONLY. The app never executes them.
- All scans stay on your machine. Nothing is uploaded anywhere.

--------------------------------------------------------------------------------
BUILDING THE EXE YOURSELF
--------------------------------------------------------------------------------

Prerequisites: Python 3.10+ on Windows, pip.

    pip install -r requirements.txt
    python -m PyInstaller --clean packaging/hardening-checker.spec

Output:  dist/HardeningChecker.exe  (onefile, windowed, ~59 MB)

Or use the helper scripts:
    packaging\build_exe.cmd        (double-click or run from cmd)
    bash packaging/build_exe.sh    (from Git Bash)

To sign the binary (recommended for enterprise distribution):
    signtool sign /fd SHA256 /tr http://timestamp.digicert.com ^
        /td SHA256 /a dist\HardeningChecker.exe

--------------------------------------------------------------------------------
RUNNING THE TEST SUITE
--------------------------------------------------------------------------------

    pip install pytest
    python -m pytest tests/ -q

26 unit + end-to-end tests cover the evaluator, scoring, rule integrity,
HTML/PDF rendering, CLI, and a full simulated scan.

--------------------------------------------------------------------------------
PROJECT LAYOUT
--------------------------------------------------------------------------------

    hardening_checker/            application package
      core/                       models, contexts, evaluator, scanner, scoring
      rules/                      windows_rules, linux_rules, macos_rules
      reporting/                  HTML (Jinja2) + PDF (ReportLab) generators
      gui/                        PySide6 UI (theme, widgets, main window)
      cli.py                      headless CLI
      __main__.py                 python -m hardening_checker
    packaging/                    PyInstaller spec + build scripts
    tests/                        pytest suite
    docs/                         METHODOLOGY, BUILDING, SAFETY, USAGE
    run.py                        convenience launcher
    README.md                     markdown version of this file

--------------------------------------------------------------------------------
TROUBLESHOOTING
--------------------------------------------------------------------------------

Q: The exe flashes a console window.
A: It should not (built windowed). If you built it yourself with console=True
   in the spec, rebuild with the provided spec file.

Q: Many checks show SKIPPED.
A: They need administrator rights. Re-run the app elevated to include them.

Q: A check shows ERROR.
A: The probe could not run (missing tool, access denied). Check the message in
   the findings detail pane; errors count as half-weight, not failures.

Q: SmartScreen warns about the exe.
A: Expected for unsigned binaries. Build and sign it yourself, or click
   "More info" -> "Run anyway".

Q: GUI does not start from source.
A: pip install PySide6

Q: Where are my reports?
A: You choose the location in the save dialog each time. Nothing is written
   anywhere without your explicit save.

--------------------------------------------------------------------------------
LICENSE
--------------------------------------------------------------------------------

MIT License. See LICENSE file. CIS Benchmark references are for mapping
purposes only; this tool ships its own independent rule set.

================================================================================
 Generated with Codebuff - https://freebuff.com
================================================================================
