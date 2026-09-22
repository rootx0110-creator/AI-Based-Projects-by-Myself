# Memory — Mobile Device Forensic Workflow

Project memory: decisions, conventions, and gotchas for future sessions.

## Identity

- App: **Mobile Device Forensic Workflow (MFW)** — Android logical-acquisition
  lab toolkit with HTML report download.
- Deliverable: single-file Windows exe (`dist/MobileForensicWorkflow.exe`)
  built with PyInstaller; source lives beside it.
- Docs live in the repo root: `architecture.md`, `memory.md`, `state.md`,
  `todo.txt`, `readme.txt`.

## Key Decisions

| Decision | Rationale |
|---|---|
| PySide6 + QSS, not Electron/web UI | Native window, single exe, no Node toolchain; QSS gives the gradient "eye-catchy" look without images. |
| Indigo/violet gradient + teal accent (explicitly **not** black or white background) | User requirement; also matches forensic-lab "console" aesthetics. |
| PyInstaller `--onefile --windowed` | User asked for "an exe application"; onefile is the simplest hand-off. Data dir resolves next to the exe (`sys.frozen` check), never to `_MEIPASS`. |
| ADB via external `adb.exe` subprocess | Keeps the exe small; lab machines already have platform-tools. `find_adb()` checks PATH + common SDK locations and the app degrades gracefully. |
| 4 extraction methods: `adb_backup`, `packages`, `screenshot`, `demo` | `adb backup` is the classic *logical* acquisition; package list & screencap are quick lab wins; demo mode makes the whole workflow demonstrable without hardware. |
| Evidence hashing (SHA-256) + chain-of-custody CSV at acquisition time | Core forensic requirement; rows append-only. |
| HTML report fully self-contained (inline CSS, html-escaped) | "Download report capability in HTML format"; opens anywhere, prints cleanly, no external assets. |
| Deterministic demo dataset (`demo.py`, seeded by case number) | Repeatable screenshots/demos; same seed -> same data. |
| `extraction.py` holds device-independent logic; `extraction_view.py` only threads | Core pipeline is testable headless (offscreen smoke test). |

## Conventions

- Python 3.10+ compatible typing (`from __future__ import annotations`).
- One class per view, each view exposes `refresh()`; shell calls it on show.
- All store mutations go through `CaseStore` (single JSON index + per-case files).
- Log lines in the UI and audit files use `"ts | case | event | detail"`.
- QSS selectors use dynamic properties: `[card="true"]`, `[cssClass="primary"]`.
  Call `style().unpolish/polish` if changing properties after show.
- Human timestamps: `%Y-%m-%d %H:%M:%S`; filename stamps: `%Y%m%d_%H%M%S`.

## Pitfalls (learned/known)

- `adb backup` blocks until the user taps *Back up my data* on the device —
  run it in a QThread with a generous timeout and print on-screen instructions.
- Android `.ab` = 4 header lines + zlib stream + tar; parse manually
  (`ANDROID BACKUP` magic, `zlib.decompress`, `tarfile.open(mode="r:")`).
- `adb backup` on many modern devices is deprecated/restricted; when empty or
  cancelled, keep the evidence entry and warn — never crash.
- SQLite DBs must be opened read-only (`mode=ro` URI) on evidence copies.
- PySide6 enums: use fully-qualified names (`Qt.ItemDataRole.UserRole`).
- QFrame subclasses need `WA_StyledBackground` for QSS backgrounds to apply.
- When frozen, `data/` must be beside the exe, not the temp extraction dir.
- Windows bash (Git Bash): use `taskkill //F //IM name.exe` (double slashes).
- Python 3.14 needs a recent PySide6/PyInstaller; if wheels are missing, fall
  back to the machine's Python 3.10/3.13 interpreters.

## Rebuild / Verify

```
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MobileForensicWorkflow main.py
QT_QPA_PLATFORM=offscreen python smoke_test.py   # headless pipeline check
```

(`pyinstaller` is not on PATH on this machine — always `python -m PyInstaller`.)
After a launch test, delete `dist/data/` so end users get a clean first run.
