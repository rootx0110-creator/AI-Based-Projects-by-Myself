================================================================================
  SeaSim - Social Engineering Awareness Simulator
  Internal phishing simulation & awareness training platform
  Version 1.0.0
================================================================================

WHAT IT IS
----------
SeaSim is a desktop application for AUTHORIZED security teams to run
simulated phishing awareness campaigns against their OWN organization.
It measures employee susceptibility (open / click / report / dismiss)
and delivers just-in-time training the moment someone interacts with a
simulation.

ETHICS & SAFETY BY DESIGN
-------------------------
SeaSim is built so that misuse is technically prevented, not just
discouraged:

  * NO CREDENTIAL HARVESTING  - there are no password fields anywhere.
    Clicking a simulated email opens an educational "training moment",
    never a login page. Nothing typed anywhere is collected.
  * NO EXTERNAL TARGETING     - recipients must be internal staff you
    add yourself. Delivery runs through a local SMTP stub bound to
    127.0.0.1 only; no message ever leaves your machine, and no real
    mail server is contacted.
  * FULL CONSENT WORKFLOW     - every launch requires a 3-step
    authorization: scope confirmation, a read-and-agree policy
    acknowledgement (tick-box), and an operator sign-off. All
    authorizations are written to a consent log.
  * BOUNDED BLAST RADIUS      - max 500 recipients per launch, max
    60 emails/minute, safe mode permanently on.
  * DATA MINIMIZATION         - only coarse outcomes are recorded
    (opened / clicked / reported / dismissed + timestamps). Results
    are for training, never for discipline.

GETTING STARTED
---------------
1. Launch the app:
       FAST:  double-click  dist\SeaSim\SeaSim.exe   (opens in ~3 s)
       PORTABLE single file:  dist\SeaSim.exe          (slow first open,
       10-30 s - it unpacks itself every launch; nothing is wrong)
   (or run from source:  python -m seasim)
2. Go to PARTICIPANTS and add your internal staff, or import a CSV:
       name,email,department,location
3. Skim the built-in email TEMPLATES (8 included, incl. 2 AI-themed).
4. Open NEW CAMPAIGN and follow the 7-step wizard:
       Name -> Template -> Recipients -> Mode -> Schedule -> Review
       -> Authorize (policy + signature)
5. Launch. Watch INBOX SIMULATION to see delivery and try the
   participant actions yourself (open / click / report / dismiss).
   A click immediately opens the just-in-time training window.
6. Open REPORTS for the text report, a downloadable HTML report,
   CSV exports, and program JSON backup.

WHERE YOUR DATA LIVES
---------------------
Everything is one file:
       %LOCALAPPDATA%\SeaSim\seasim_data.json
Backup = copy that file (or use Reports -> "Export program JSON").
Portable/dev runs: set the SEASIM_DATA_DIR environment variable.
Uninstall = delete dist\SeaSim.exe and that data folder. Nothing else
is touched.

THE SEVEN RULES (SHOWN AT EVERY LAUNCH)
---------------------------------------
 1. SCOPE          - own organization only.
 2. AUTHORIZATION  - written approval exists before launching.
 3. NO REAL CREDENTIALS - no password fields, ever (enforced by code).
 4. NO EXTERNAL TARGETING - no personal or third-party addresses.
 5. DATA MINIMIZATION - coarse interaction data only.
 6. JUST-IN-TIME TRAINING - education on interaction, no shaming.
 7. CONFIDENTIALITY - training purposes only, not discipline.

TESTING
-------
Run the built-in self-test (17 checks: engine, safety, GUI, SMTP,
persistence). It uses a throwaway data folder, so your real data is
never touched:

    python tools/selftest.py

BUILDING FROM SOURCE
--------------------
Requires Python 3.10+ with Tkinter and PyInstaller:

    pip install pyinstaller
    python build/icon.py                  # regenerate icon (optional)
    python -m PyInstaller SeaSim.spec --noconfirm
    -> dist\SeaSim.exe

Run from source without building:
    python -m seasim

TROUBLESHOOTING
---------------
* "Windows protected your PC" on first run: the exe is unsigned.
  Click "More info" -> "Run anyway", or build from source yourself.
* Launch blocked: every campaign needs its authorization completed.
  Re-open the campaign and finish the consent steps.
* Status bar shows smtp-stub errors: the local sink could not bind
  port 8025 (rare). Delivery and events still work; the sink is
  best-effort only.
* Data looks wrong: use Settings -> "Import program JSON..." to
  restore a backup, or "Reset all data..." to start clean (built-in
  templates are restored automatically).

FILE OVERVIEW
-------------
    dist\SeaSim\SeaSim.exe   the application (folder build, fast start)
    dist\SeaSim.exe           portable single-file build (slow start)
    seasim\                   full source code (documented)
    SeaSim.spec          PyInstaller build recipe
    build\icon.py        icon generator (pure stdlib)
    ARCHITECTURE.md      technical design & data flow
    MEMORY.md            project memory: decisions, status, roadmap
    STATE.md             current build/verification snapshot

RESPONSIBLE USE REMINDER
------------------------
Run simulations only where you have explicit authorization. Tell staff
that simulations happen (not when). Never use results punitively. When
in doubt, involve HR and legal before your first campaign.

================================================================================
  SeaSim 1.0.0 - for internal authorized awareness programs only
================================================================================
