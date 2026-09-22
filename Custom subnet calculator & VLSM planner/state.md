# State — Custom Subnet Calculator & VLSM Planner

## Project identity

| Field              | Value                                          |
|--------------------|------------------------------------------------|
| App name           | SubnetPlanner                                  |
| Version            | 1.0.0                                          |
| Platform           | Windows x64 (also runs on any Python 3.14 box) |
| GUI                | Tkinter / ttk (Tk 9.0)                         |
| Packaging          | PyInstaller 6.22.3 (one-file, windowed)        |
| Python             | 3.14.7, 64-bit                                 |
| Workspace root     | `<project root>` (this directory)              |

## Build status (baseline stamp)

- [x] Core module (`app/core.py`) implemented and unit-tested.
- [x] HTML report generator (`app/report.py`) implemented.
- [x] GUI (`app/theme.py`, `app/widgets.py`, `app/pages.py`, `app/gui.py`).
- [x] Icon asset `assets/app.ico` generated.
- [x] Executable built and verified to launch.
- [x] Docs (`architecture.md`, `readme.txt`, `memory.md`, `todo.txt`).

Update the timestamps and checkboxes below as the project evolves.

```
Last verified build:  2026-09-19
Executable:           dist/SubnetPlanner.exe   (~12 MB, one file)
Window title:         "SubnetPlanner - Custom Subnet Calculator & VLSM Planner"
PyInstaller command:  python -m PyInstaller --noconfirm --clean --onefile
                      --windowed --name SubnetPlanner --icon assets/app.ico
                      main.py
```

## Current feature state

| Feature                            | Status |
|------------------------------------|--------|
| Subnet detail calculation          | done   |
| Mask ⇄ prefix ⇄ hosts ⇄ subnets    | done   |
| Derived-subnet table               | done   |
| 32-bit visual host/network map     | done   |
| VLSM allocation engine             | done   |
| VLSM segment editor (add/remove)   | done   |
| JSON import/export of VLSM plan    | done   |
| Overflow detection + warnings      | done   |
| HTML report export (single)        | done   |
| HTML combined report               | done   |
| Settings persistence (geometry)    | done   |
| Non-black friendly theme           | done   |

## Backlog / known limitations

- Subnet table caps on-screen rows at 256 (full list still in report).
- No printing; users "Print → Save as PDF" from the browser instead.
- Icon is programmatically generated; can be replaced anytime.
- RFC 3021 note: /31 and /32 show 2 and 1 usable hosts respectively.

## Test evidence

```
python -m unittest discover -s tests -v
=> Ran 22 tests, all OK (verified 2026-09-19).

Startup check on the frozen exe:
  - process stays alive, window title registers, no console window (--windowed).
  - Pixel-verified via PrintWindow (window renders white cards + #EAF0F6
    light-blue-grey background + #0F172A header — NOT black).

Smoke launch:
python -c "import app.gui; app.gui.MainWindow(smoke=True)"
=> window instantiated and destroyed cleanly.
```

## Artifacts on disk

| Path              | Purpose                                   |
|-------------------|-------------------------------------------|
| `main.py`         | entry point                               |
| `app/*.py`        | source modules (core, report, theme...)   |
| `tests/test_core.py` | unit tests                            |
| `assets/app.ico`  | application/exe icon                      |
| `dist/SubnetPlanner.exe` | the built executable              |

## How to poke at the app

```
python main.py                        # run from source
python -m unittest discover -s tests  # run tests
python -m PyInstaller ...             # rebuild (command above)
```