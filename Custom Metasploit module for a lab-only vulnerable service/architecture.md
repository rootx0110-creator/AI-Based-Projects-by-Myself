# Architecture — MSF Lab Module Studio

A desktop tool that helps a defensive trainer **build, verify and document** a
*Custom Metasploit module* for a deliberately vulnerable, **lab-only** HTTP
service.

## 1. Context / problem

Metasploit development is normally a command-line job: write Ruby, copy to
`~/.msf4/modules/`, `reload_all`, run `check`, iterate. This studio wraps that
loop in a friendly GUI so a trainee can:

1. Pick a **lab vulnerability template** and point at a lab target
   (RHOSTS / RPORT / TARGETURI).
2. Pick payload + style options and generate a ready-to-use Ruby module
   (Exploit for RCE, auxiliary/scanner for disclosure bugs).
3. **Auto-detect** which lab vulnerabilities are live, port-scan the box,
   verify the endpoint and reproduce the module's `check` verdict.
4. Download a shareable HTML security report **and** a JSON twin.

## 2. High-level components

```
┌────────────────────────── consumable (PyInstaller --onefile) ──────────────┐
│                                                                             │
│   app.py  (GUI, tkinter/ttk)                                               │
│      │  ┌──────────────────────────┐     ┌────────────────────────────┐   │
│      │  │ Setup        / Setup     │     │  Builder / Generator        │  │
│      │  │ Builder      / Builder   │────▶│  module_builder.py ──────┐  │  │
│      │  │ Live Test    / Test      │     │  VULN_TEMPLATES (catalog)│  │  │
│      │  │ Report       / Report    │     │  MetasploitModuleGenerator│  │  │
│      │  │ + profile.json (opt-in)  │     │  LabServiceProbe (detect) │  │  │
│      │  └──────────────────────────┘     │  scan_tcp_ports           │  │  │
│      │      persistence:                 │  LabHtmlReport (+to_json) │  │  │
│      │      %LOCALAPPDATA%\MSFLabStudio  └────────────────────────────┼──┘  │
│      └───────────────┬────────────────────└──────────────────────────┼──┘    │
└──────────────────────┼────────────────────────────────────────────────┘    │
                       │                    │
         ┌─────────────▼─────────┐   ┌──────▼───────────────────────────────┐
         │       (network)       │   │         (on disk / browser)          │
         │  vuln_service.py      │   │  HTML report + JSON (download)       │
         │  lab-only HTTP service│   │  vulnlab_exec.rb (saved module)      │
         └───────────────────────┘   └──────────────────────────────────────┘
```

## 3. Data flow

1. **Setup** reads target fields + template choice → `config` dictionary
   (single source of truth). Template switching auto-adopts module class,
   name, TARGETURI and CVE via `MetasploitModuleGenerator.adopt_template()`.
2. **Builder** → `MetasploitModuleGenerator.generate()` renders the Ruby
   module from `@@TOKEN@@` placeholders; the source is also emitted into the
   report.
3. **Live Test** → `LabServiceProbe` opens raw sockets:
   - `probe()` calls `GET /health` and matches the `VulnLab-Service v1.0`
     banner → `check()` verdict (`Vulnerable` / `Safe` / `Unknown`).
   - `detect_all()` runs every template check
     (`check_cmd_injection`, `check_path_traversal`, `check_config_leak`) and
     returns per-vuln verdicts + evidence + an open-vuln list.
   - `scan_tcp_ports()` sweeps `COMMON_PORTS` with plain TCP connects.
   - Each UI call runs on a daemon worker; results go through a
     `queue.Queue` to a main-thread poller (Tk stays on one thread).
4. **Report** → `LabHtmlReport.to_html()` renders a self-contained HTML doc
   (verdict, detection table, timeline, port scan, module source, safety
   sheet); `to_json()` yields the machine-readable twin. The GUI can download
   either or open the HTML in the browser.

## 4. Files

| File               | Role                                                              |
|--------------------|-------------------------------------------------------------------|
| `app.py`           | GUI entry point, view switching, status bar, detection/scan/timeline/advisor/report actions, profile persistence. |
| `module_builder.py`| Pure-logic backend: vuln template catalog, Ruby generator, HTTP probes/detection, TCP scanner, HTML + JSON report. |
| `vuln_service.py`  | Lab-only vulnerable HTTP service (`/health`, `/exec`, `/file`, `/backup`, `/flag`). |
| `build_exe.ps1`    | PyInstaller one-file build script → `dist/`.                      |
| `requirements.txt` | Runtime/build dependencies (PyInstaller is the only optional one).|
| `architecture.md`  | This document.                                                    |
| `memory.md`        | Session / learned-context notes.                                  |
| `state.md`         | Application state snapshot (defaults, current values).            |
| `todo.txt`         | Plain-text task list / backlog.                                   |
| `readme.txt`       | Quick-start manual.                                               |

## 5. Key decisions

- **tkinter only** → zero GUI dependencies, trivial to freeze with PyInstaller.
- **Template catalog** (`VULN_TEMPLATES`) keeps the three lab bug classes as
  data: module class, path, URI, CVE, detection probe + human explanation.
  Adding a vulnerability = adding one catalog entry + one `@@TOKEN@@` Ruby
  template + one probe method.
- **`@@TOKEN@@` placeholder rendering** (not `str.format`/`%`) so Ruby `%q{}`,
  `#{...}` and `%d` survive untouched in the generated module.
- **`config` dictionary owns all state** → UI reads/writes one object, so the
  report always reflects exactly what the user configured.
- **Raw-socket probe** in `LabServiceProbe` keeps the tool independent of the
  vulnerable service and works with any HTTP fingerprint; query strings are
  URL-encoded before sending.
- **Threading for network I/O** — probe/check/detect/scan run on daemon worker
  threads so the UI never freezes. Tk is *never* touched from a worker:
  results are posted to a `queue.Queue` and drained by a main-thread idle
  poller (`after(80, ...)`).
- **Error log for frozen builds** — a `--windowed` exe has no console, so all
  exceptions are appended to `%TEMP%\msf_lab_studio_error.log`
  (`sys.excepthook`, tkinter `report_callback_exception`, worker + profile
  failures).
- **HTML report is self-contained** — inline CSS, no external assets; the JSON
  twin can feed other tooling.
- **Profile persistence is opt-in** ("Remember settings") → saved to
  `%LOCALAPPDATA%\MSFLabStudio\profile.json`, never silently; nothing is
  written to disk without the toggle.

## 6. Safety boundaries

- Everything in this project is scoped to **authorized labs / CTFs**.
- The vulnerable service only binds to a host the operator chooses and prints a
  loud "LAB ONLY" banner.
- The report carries an explicit usage-and-safety notice and a unique Report ID.

## 7. Build pipeline

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File build_exe.ps1
# -> dist/MSF-Lab-Module-Studio.exe
```

Verify the frozen binary headlessly before sharing:

```powershell
$env:MSF_STUDIO_SELFTEST="1"; .\dist\MSF-Lab-Module-Studio.exe
Get-Content "$env:TEMP\msf_studio_selftest.out"   # expect 10 PASS lines
```