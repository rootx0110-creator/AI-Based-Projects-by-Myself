# STATE.md — current feature/release state

## What is implemented (v1.0)

Interview / wizard
  [x] Multi-step guided interview (6 pages)
  [x] Sector + geography + company-size branching
  [x] Compliance intent picker (multi-select frameworks)
  [x] 12 security-domain posture ratings + explanation autosave
  [x] Risk-appetite sliders (CIA triad)
  [x] Autosave of all answers to localStorage

Policy engine
  [x] Adaptive chapter composer (12 domain chapters)
  [x] Regulator detection (GDPR/NIS2/SOC2/PCI-DSS/HIPAA + sector-specific)
  [x] Control-gap scoring per domain (posture vs target assurance)
  [x] Executive summary + board talking points generation
  [x] Risk heat-map table (probability x impact) with key risks
  [x] KPIs/metrics table for ongoing board reporting
  [x] 0-90-180-365 day implementation roadmap
  [x] Roles & responsibilities (governance) chapter
  [x] Sign-off / approval block + version-history table
  [x] Freely editable report before export (contenteditable textarea)

Report / export
  [x] In-app board-ready document preview with table of contents
  [x] Download standalone HTML report (self-contained, printable)
  [x] Print / Save-as-PDF flow through native print dialog
  [x] Filename includes company name + date

EXE packaging
  [x] pywebview wrapper (run_app.py) bundled to Windows .exe
  [x] build_exe.ps1 one-command build script
  [ ] Verified on Windows 10 only (expect minor window-icon issues
      on 7/8; recommend 10/11)

## Known limitations
  - Report is English-only (localization architecture is ready).
  - No real-time collaborative editing (offline single user).
  - Word-count of a full policy varies with interview depth
    (approx 25-45 pages A4).
  - Charts on the cover are styled divs/SVG, not a charting lib
    (keeps export dependency-free and printer-safe).

## Tested
  [x] Chrome 120+, Edge, Firefox
  [x] Print preview A4 / Letter page-break sanity
  [x] localStorage persistence across reloads
  [x] EXE launch from cold boot (no browser installed)

## Release state
  status  : STABLE v1.0
  date    : 2026-09-22
  next    : see todo.txt roadmap