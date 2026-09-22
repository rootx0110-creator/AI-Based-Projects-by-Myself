# State — Mobile Device Forensic Workflow

Snapshot of the current build status. Update this file whenever the app changes.

## Status: WORKING / BUILT

Last updated: 2026-09-19 (v1.0.1 hotfix: window was never shown from the exe)

### Hotfix 2026-09-19 — "exe starts but no window"
- Cause: `main.py` created `MainWindow()` but never called `win.show()`
  (lost when the entry point was simplified), so the process hung invisibly.
- Fix: restored `win.show()`; added `data/startup_error.log` writing on any
  startup/runtime exception so windowed-build failures are never silent.
- Verified: exe launch test shows process + seeded data + no error log;
  smoke test re-passed; rebuilt `dist/MobileForensicWorkflow.exe`.

## Environment

- Windows (bash shell), Python 3.14.7 at `C:\Python314`
- PySide6 6.11.2 (user-site install)
- PyInstaller 6.22.3 — NOTE: not on PATH; invoke as `python -m PyInstaller`

## What Works

- [x] Self-help guide `how_to_check_your_mobile.txt` (shipped in dist/)
      walking a user through examining their own phone end to end
- [x] Themed UI shell: sidebar navigation, gradient background (indigo/teal),
      header chips (ADB status, active case)
- [x] Case Manager: create case, case table, activate case
- [x] Extraction view: ADB device detection, device-info read, 4 methods
      (adb backup / package inventory / screenshot / demo dataset), threaded
      worker with live log and progress bar
- [x] Evidence handling: SHA-256 hashing, chain-of-custody CSV, per-case audit
- [x] Artifact parsing: .ab unpack (zlib+tar), calls/SMS/contacts via SQLite,
      package inventory, deterministic demo dataset
- [x] Artifacts browser: type filter, search, CSV export
- [x] Reports: metadata form, in-app preview, **Download HTML Report**
      (save dialog, defaults to case `reports/` folder), open last report
- [x] Audit Log viewer
- [x] PyInstaller build -> `dist/MobileForensicWorkflow.exe` (onefile, windowed)

## Verification Performed This Session

- Headless smoke test (QT_QPA_PLATFORM=offscreen): app + case creation +
  demo extraction (158 artifacts) + SHA-256 hashing + HTML report build
  (21 KB) all pass. See `smoke_test.py`.
- `dist/MobileForensicWorkflow.exe` (~50 MB, onefile, windowed) rebuilt
  after the show() hotfix and launch-tested: window shown, `data/` created
  beside the exe, no startup_error.log, processes exit cleanly.
- `dist/data` removed after the launch test so end users get a clean
  first run (the exe re-seeds DEMO-001 automatically).

## Known Limitations

- `adb backup` requires user confirmation on the device and is restricted on
  newer Android builds; when it fails, evidence is kept and a warning is logged.
- Contacts parsing depends on the standard contacts2.db schema.
- No icon resource bundled (default PyInstaller icon).
- `pyinstaller` command not on PATH on this machine — always use
  `python -m PyInstaller ...`.
- Report preview widget supports only basic CSS (saved HTML is the source of
  truth for look-and-feel).
