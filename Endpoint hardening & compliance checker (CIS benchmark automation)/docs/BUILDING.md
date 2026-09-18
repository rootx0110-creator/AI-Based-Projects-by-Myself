# Building & Development

## Prerequisites

- **Python 3.10+** (developed and tested on 3.14)
- Windows to build the Windows `.exe` (PyInstaller does not cross-compile)
- pip packages: `pip install -r requirements.txt`
  - Runtime: `PySide6`, `Jinja2`, `reportlab`
  - Build: `pyinstaller`
  - Dev: `pip install -e .[dev]` adds `pytest`

## Dev workflow

```bash
# run the GUI from source
python run.py

# headless scan
python run.py --cli scan --json out.json --quiet

# tests (26 tests, no OS access needed)
python -m pytest tests/ -q

# quick smoke of the GUI without a display (Windows: use a real session
# or the offscreen platform plugin)
QT_QPA_PLATFORM=offscreen python run.py
```

## Building HardeningChecker.exe

```bash
python -m PyInstaller --clean packaging/hardening-checker.spec
```

Output: `dist/HardeningChecker.exe` — a **onefile windowed** executable
(~59 MB) bundling Python, PySide6, Jinja2, ReportLab, all rule modules and the
HTML templates.

Helper scripts:

```cmd
packaging\build_exe.cmd
```
```bash
bash packaging/build_exe.sh
```

### What the spec does

- Entry point is `run.py`; `console=False` so no terminal flashes on launch
- `datas` bundles `hardening_checker/reporting/templates/*.j2`
- `hiddenimports` pins every `hardening_checker.rules.*` module — required
  because the scanner discovers them dynamically via `pkgutil`
- Excludes `tkinter`, `matplotlib`, `numpy`, `PyQt5/6` to keep size down

### Code signing (recommended for distribution)

```cmd
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist\HardeningChecker.exe
```

Unsigned builds trigger SmartScreen's "unknown publisher" warning.

### Optional icon

Drop `assets/icon.ico` before building; the spec picks it up automatically.

## Cross-platform notes

- The scanner runs on Linux/macOS with the matching rule modules
  (`linux_rules.py`, `macos_rules.py`), selected automatically by
  `PlatformContext`.
- Building a Linux binary: run PyInstaller on Linux with the same spec
  (remove the `icon=` line or supply a platform-appropriate icon).
- GUI dependencies are identical; `QT_QPA_PLATFORM=offscreen` enables headless
  CI smoke tests.

## Release checklist

1. `python -m pytest tests/ -q` — all green
2. Real-machine CLI scan: `python run.py --cli scan --quiet` — 0 unexpected errors
3. GUI smoke: scan → dashboard → findings → export HTML + PDF
4. `python -m PyInstaller --clean packaging/hardening-checker.spec`
5. `dist/HardeningChecker.exe --cli scan --quiet` — works from the bundle
6. Sign the exe, update `__version__` in `hardening_checker/__init__.py`
