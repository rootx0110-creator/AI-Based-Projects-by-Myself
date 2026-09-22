# Purple Team Capstone

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
.\dist\PurpleTeamCapstone.exe
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
