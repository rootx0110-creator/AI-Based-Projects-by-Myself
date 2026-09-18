# Memory — persistent notes for this project

This file records decisions, corrections and gotchas so future sessions can
pick up without re-discovering them.

## 2026-09-17 — Initial build

### Requirements (user)
- Deliver an **exe** application: "Red Team Engagement Report Generator
  (findings → CVSS → executive summary)".
- Must ship with `architecture.md`, `state.md`, `memory.md`.
- Must support **HTML report download**.
- Must have a **nice and colorful UI**.

### Stack decision
- **Python 3.14 + tkinter + PyInstaller 6.22**. Rationale: zero runtime deps,
  standard-library GUI packages into a single small exe, no web runtime needed.
- CVSS engine implemented from the official v3.1 spec (not a pip package) to
  keep the bundle dependency-free.

### Project layout (final)
```
main.py  app/{__init__,cvss,data,report,gui}.py  build.bat
architecture.md  state.md  memory.md
```

## 2026-09-17 — Sample data feature added

- Request: "add a test data so that i can understand it easily".
- Added `app/sample_data.py` with a realistic Acme Corporation engagement:
  8 findings covering every severity band (Critical/High/Medium/Low) whose CVSS
  vectors were hand-verified against the v3.1 equations.
- UX decisions:
  - **Auto-load on first run** only when the store is empty; never overwrites
    existing data. Implemented by calling `load_sample_data()` at the end of
    `App.__init__` (UI must exist first) wrapped in `self.silent = True` to
    suppress dialogs.
  - Green **"Load Sample Data"** button under the findings list restores the
    demo dataset any time (with a confirm dialog if data exists).
  - Popups are routable: `load_sample_data` checks `self.silent` so headless
    smoke tests don't hang on modal dialogs. Modal `messagebox` calls MUST go
    through a `self.silent` guard for future tests.
- Gotcha: PyInstaller rebuild failed with `PermissionError: Access denied` on
  `dist\RedTeamReportGenerator.exe` because a leftover instance was running —
  always `Stop-Process -Name RedTeamReportGenerator` before rebuilding.

### Key corrections made during dev
1. `data.py:app_dir()` must use `sys.executable` when frozen (PyInstaller),
   else the store would be written to the ephemeral `_MEIPASS` temp dir.
2. `gui.py` duplicate-finding initially reused `from_dict` dict id — must
   regenerate the id, else two findings share one identity.
3. Engagement form fields were read from `store.engagement` for the summary
   preview; now the form is always synced into the store via
   `_sync_engagement_from_form()` before rendering so previews stay current.
4. CVSS score-bar drawn with fixed 800px segments broke on resize — now uses
   `canvas.winfo_width()`.
5. ttk `clam` theme styled for the default (light) dialogs and notebook tabs;
   all custom widgets use plain tk for full color control.

### Roadmap notes / ideas
- Keep `report.build_html_report(store)` free of GUI imports so a future
  CLI (`python -m app.cli input.json -o report.html`) is trivial.
- LLM-backed executive narrative: add optional hook in `report.py`.
- Sample data loader button to demo quickly (suggested).

### Gotchas for future sessions
- CVSS v3.1 formula: impact for scope=Changed uses the `7.52*(ISS-0.029)-...`
  branch; scope unchanged uses `6.42*ISS`. PR weights differ by scope too.
- `_roundup` must post-ceil (`math.ceil(x*10)/10`) then clamp to 10.
- tkinter `Listbox` per-row colours via `itemconfig(index, foreground=...)`.
- PyInstaller onefile: data file next to exe; avoid `cwd`-relative paths.

## Environment
- OS: Windows, PowerShell 5.1 shell.
- Python 3.14.7 at `C:\Python314`, pip 26.2.1, PyInstaller 6.22.2.
- Project dir contains non-ASCII characters — always quote paths in shell and
  in the PyInstaller spec arguments.