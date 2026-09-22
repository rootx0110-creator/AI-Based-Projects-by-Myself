"""Regenerates the docs/*.md files from a single source of truth
(the MITRE registry + config). Run with:  python -m purpleteam.docs
"""

from __future__ import annotations

from pathlib import Path

from . import APP_NAME, __version__
from .config import DOCS_DIR, ensure_dirs
from .mitre import BLUE_RULES, RED_TECHNIQUES

APP_VERSION = __version__


def _technique_table() -> str:
    rows = ["| ID | Technique | Tactic | Module | Detected by |",
            "| --- | --- | --- | --- | --- |"]
    from .mitre import rules_for_technique
    for t in RED_TECHNIQUES:
        rules = ", ".join(r.id for r in rules_for_technique(t.id)) or "-"
        rows.append(f"| {t.id} | {t.name} | {t.tactic} | `{t.module}` | {rules} |")
    return "\n".join(rows)


def _rule_table() -> str:
    rows = ["| Rule | Name | Data Source | Detects |",
            "| --- | --- | --- | --- |"]
    for r in BLUE_RULES:
        rows.append(f"| {r.id} | {r.name} | {r.data_source} | {', '.join(r.detects)} |")
    return "\n".join(rows)


def render_readme() -> str:
    return f"""# {APP_NAME}

**Red builds. Blue detects. Both document MITRE ATT&CK.**

A self-contained purple-team lab app shipped as a single Windows executable.
All "red team" activity is **simulated inside a sandboxed lab target directory**
under `outputs/lab_target` plus one loopback socket for the exfiltration
technique - nothing touches the real system, registry, services or network.

## Feature checklist

| Capability | Where |
| --- | --- |
| Red team builds techniques (9 ATT&CK techniques) | Red tab / `purpleteam/redteam.py` |
| Blue team detection rules (9 sigma-style rules) | Blue tab / `purpleteam/blueteam.py` |
| MITRE ATT&CK coverage matrix (technique × rule) | MITRE tab / `purpleteam/mitre.py` |
| Exercise timeline + scoring | `purpleteam/exercise.py` |
| **HTML report download** + open in browser | Report tab / `purpleteam/report.py` |

## Run from source

```powershell
pip install -r requirements.txt
python main.py            # GUI
python main.py --cli      # headless exercise + report
python -m purpleteam.selftest
```

## Build the EXE

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\\dist\\PurpleTeamCapstone.exe
```

## Layout

```
purpleteam/
  config.py      paths (exe-dir aware for frozen builds)
  mitre.py       technique + rule registry (single source of truth)
  redteam.py     attack simulation modules
  blueteam.py    detection rules + scan engine
  exercise.py    orchestration, scoring, persistence
  report.py      self-contained HTML report (download/open)
  app.py         tkinter GUI
  docs.py        regenerates docs/*.md
  selftest.py    headless verification
  util.py        helpers
tools/make_icon.py   generates assets/purpleteam.ico
```

> **Legal/ethics:** authorized labs and defensive use only.
"""


def render_architecture() -> str:
    return f"""# Architecture

## Data flow

```
┌──────────────┐  selects techniques  ┌───────────────────────┐
│  GUI / CLI   │ ───────────────────► │   Exercise (session)   │
└──────────────┘                      │  exercise.py           │
                                      └───────────┬─────────────┘
                       red build                 │        blue detect
                                      ┌──────────▼──────────┐
                                      │   lab_target/        │
                                      │   outputs/lab_target │
                                      │   + sidecar index    │
                                      └──────────┬───────────┘
                                                 │
      .purpleteam_index.json  (artifacts) ───────┘
                                                 │ findings
                                      ┌──────────▼──────────┐
                                      │  score + coverage    │
                                      │  matrix (mitre.py)   │
                                      └──────────┬───────────┘
                                                 ▼
                                    report.py → HTML report (one file)
```

## Design decisions

1. **Single source of truth** - `mitre.py` holds both the technique library and
   the detection-rule library. `report.py`, `docs.py` and the GUI all render
   from it, so a technique added once appears everywhere.
2. **Artifact index** - red modules write files and also append JSON artifact
   records to `.purpleteam_index.json`. Blue rules scan that index
   (deterministic, fast), while the files remain on disk as evidence.
3. **Many-to-many mapping** - one rule (RULE-TOOL-DROP) surfaces T1105 and
   T1036.005; one technique (T1027) is surfaced by RULE-PS-OBFUSC. The coverage
   matrix shows the full relationship.
4. **Fidelity grades** - findings are tagged `high` (dedicated data source) or
   `low` (generic catch-all). The report separates *detection rate* from
   *dedicated coverage* so a catch-all can't mask weak signatures.
5. **Frozen-safe paths** - `config.py` picks the executable folder when running
   as a PyInstaller one-file build and falls back to LocalAppData when the
   exe folder is not writable. Reports/session/lab always land somewhere.
"""


def render_mitre_coverage() -> str:
    return f"""# MITRE ATT&CK mapping (generated)

## Techniques available to red

{_technique_table()}

## Detection rules (blue)

{_rule_table()}

## Data-source notes

* File + Windows Event Log keep persistence & execution covered (high fidelity).
* Network exfiltration (T1041) relies on entropy/base64 heuristics over a local
  port - a real lab should add Zeek/Suricata.
* RULE-CHANGE is the intentional low-fidelity catch-all; it is *not* proof a
  dedicated signature exists.
"""


def render_run_instructions() -> str:
    return f"""# Run instructions

## GUI mode (recommended)

1. Double-click `dist\\PurpleTeamCapstone.exe` (or run `python main.py`).
2. **Dashboard** - check the techniques you want red to build, click
   *Build (Red)*, then *Detect (Blue)*.
3. **Red tab** - watch each technique's artifacts land in the lab target.
4. **Blue tab** - inspect findings and severities after the scan.
5. **MITRE tab** - study the technique × rule coverage matrix.
6. **Report tab** - *Download HTML report*, pick a location, then *Open report*.

## CLI / headless

```powershell
python main.py --cli            # full exercise, all techniques, HTML report
python main.py --cli T1053.005,T1041
python -m purpleteam.selftest   # engine self check, returns 0 on success
```

## Data locations

| Item | Path |
| --- | --- |
| Lab sandbox (red artifacts) | `outputs/lab_target/` |
| Last session (JSON) | `outputs/last_session.json` |
| Reports | `outputs/reports/*.html` |

When running the frozen EXE these land next to the executable (or in
`%LOCALAPPDATA%\\PurpleTeamCapstone` if the exe folder is read-only).

## Troubleshooting

* **AV flags the EXE** - PyInstaller one-file apps are commonly flagged by
  heuristic AV. Use an allow-listed lab machine; build from source if needed.
* **Report download in the menu is disabled** - run at least one exercise so a
  downloadable session exists.
* **Ports blocked** - the exfiltration module binds an ephemeral loopback port
  only; firewall policy targeting 127.0.0.1 may still interfere.
"""


def render_state() -> str:
    return f"""# State & limitations

## What is simulated (not real)

- Scheduled-task XML drops into `lab_target/tasks/` - real Task Scheduler is never touched.
- Run-key autostart is a `.reg` text file. PowerShell "runs" are log lines.
- The exfiltration channel is a loopback socket bound to an ephemeral port.
- No host, registry, service, firewall or remote host is modified.

## Known limitations

- Detection engine inspects the artifact index + files; it is a *simulator* of
  a SOC toolchain, not EDR/AV. No real runtime inspection.
- T1041 fidelity depends on entropy/base64 heuristics; a passive network sensor
  (Zeek/Suricata/NIDS) is recommended in a production lab.
- RULE-CHANGE (catch-all) intentionally detects broadly at low fidelity.
- Scores reset each exercise; archive `outputs/reports/*.html` for trend data.
"""


def main() -> None:
    ensure_dirs()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "README.md": render_readme(),
        "architecture.md": render_architecture(),
        "MITRE_COVERAGE.md": render_mitre_coverage(),
        "RUN_INSTRUCTIONS.md": render_run_instructions(),
        "state.md": render_state(),
    }
    for name, text in files.items():
        (DOCS_DIR / name).write_text(text, encoding="utf-8")
    print(f"Wrote {len(files)} docs to {DOCS_DIR}")


if __name__ == "__main__":
    main()