WINDOWS EVENT LOG CORRELATION TOOL — INTRUSION TIMELINE
========================================================
Build an executable desktop app that correlates Windows Event Logs into a
MITRE ATT&CK intrusion timeline and exports a downloadable HTML report.

FEATURES
--------
1. DATA SOURCES
   - Live Windows logs: Security, System, Application, PowerShell,
     Sysmon, Task Scheduler, Terminal Services, and a custom channel box.
   - Offline .evtx files (any Windows machine's exported logs).
   - Time-window filtering (1h / 24h / 7d / 30d / all).

2. CORRELATION ENGINE
   - ~20 MITRE ATT&CK detection rules (brute force, password spray,
     DCSync, Kerberoast, LSASS/SAM access, run keys, scheduled tasks,
     services, encoded PowerShell, certutil, LOLBins, Defender tampering,
     log clearing, RDP & lateral movement patterns, and more).
   - Sliding time windows, deduplication, kill-chain phase assignment,
     multi-stage incident chain grouping, cumulative severity scoring.

3. USER INTERFACE (tkinter, dark theme)
   - Dashboard (KPIs, tactic bars, top hosts/users)
   - Intrusion Timeline (color-coded by phase)
   - Alerts tab (rule breakdown + raw event drill-down)
   - Events tab (full raw event explorer with filters)
   - Threaded analysis with progress bar and cancel.

4. REPORT EXPORT
   - "Download HTML report" produces ONE self-contained .html file:
     KPI cards, MITRE coverage, vertical intrusion timeline, incident
     chains, alerts table, raw events. No internet needed to view.

HOW TO RUN
----------
Option A - Prebuilt EXE
  1. Open dist\IntrusionTimelineTool.exe (double-click).
  2. Click "Load Live Logs" (pick channels + time window), or
     "Load EVTX Files" to analyze a captured log.
  3. Press "Analyze". Browse Dashboard / Timeline / Alerts / Events.
  4. Press "Generate HTML Report", choose a filename, open it.

Option B - From source
  1. python -m pip install -r requirements.txt   (nothing needed at runtime)
  2. python main.py

BUILD THE EXE YOURSELF
----------------------
  1. Run build.bat (installs PyInstaller and packages the tool).
  2. Output: dist\IntrusionTimelineTool.exe

NOTES
-----
- No administrator rights are required for the app itself, but some log
  channels may need elevation to be readable on hardened hosts.
- All analysis is local. Nothing leaves the machine.
- Report files are plain HTML with inline CSS/JS; they can be stored
  alongside your lab evidence.

CONTENTS
--------
architecture.md   Design overview and data flow
memory.md         Architecture decision records and conventions
state.md          Current status and known limitations
todo.md           Backlog (P0/P1/P2)
app/              Application source modules
main.py           Entry point
build.bat         One-click PyInstaller packaging script
WECT.spec         PyInstaller spec file