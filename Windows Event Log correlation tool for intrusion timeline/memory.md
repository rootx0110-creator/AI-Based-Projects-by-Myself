# Memory — Project Decisions & Knowledge

Persistent notes for agents working on this repository.

## Environment
- OS: Windows, PowerShell 5.1 shell.
- Python 3.14.7 with tkinter available.
- `wevtutil` is available and used for all event log access.
- Git: NOT initialized in the project dir (do not assume commit workflows).

## Decisions (ADRs)

### ADR-001: Log access via wevtutil (not python-evtx / pywin32)
- Reason: wevtutil ships with every Windows install, performs message
  rendering, requires zero packaged binaries, and simplifies PyInstaller
  builds. python-evtx/lxml bloats the exe and needs native wheels.
- Trade-off: wevtutil is slower on very large files and yields raw XPath
  results (message strings still render inside Data/RenderingInfo).

### ADR-002: tkinter for the GUI
- Reason: bundled by default, packages cleanly with PyInstaller, no
  npm/Python GUI wheel cross-dependencies.
- Trade-off: fewer "modern" widgets; we compensate with a dark custom ttk
  style, flat cards, and consistent color tokens.

### ADR-003: Single-file HTML report
- Reason: one file is easy to download/share/email and open anywhere.
- Trade-off: larger file for big datasets; capped by MAX_RAW_EVENTS.

### ADR-004: Threading model
- All ingest/correlate work runs in a worker thread; UI refreshes via
  `root.after()`. Never touch widgets from non-main threads.
- Global `working` flag + `cancel_requested` for clean shutdown of long runs.

### ADR-005: Timestamps
- Windows event SystemTime is UTC. Records keep UTC `datetime`; the UI and
  report print local time (display-localized) with offsets.
- XPath time filters are always expressed in UTC (ISO + 'Z').

## Conventions
- Python files under `app/`; entry point `main.py`.
- Dataclasses for models; enums for Severity / Phase.
- Rule modules are declarative (metadata + evaluators), added in `RULES`.
- Keep report HTML self-contained: no external CDN links.

## Gotchas
- `wevtutil qe` XML uses the win%20event namespace; always strip namespace
  tags before parsing.
- `<Data>` without a `Name` attribute is indexed `Data<n>`.
- Huge event dumps: cap `qe /c` and cap correlation windows reasonably.
- Python 3.14: avoid removed stdlib modules (distutils, etc.).

## Validation commands
- `python -c "import app"`  (import sanity)
- `python -c "from app import parser, correlator, report"` (module smoke test)
- `python -m PyInstaller ...` via `build.bat`
- Run `main.py` interactively to check GUI.