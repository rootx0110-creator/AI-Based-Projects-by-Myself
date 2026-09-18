# Red Team Engagement Report Generator

A self-contained Windows desktop application that turns red team engagement
**findings** into structured CVSS v3.1 scores and a polished, colorful
**HTML report** with an auto-generated **executive summary**.

## Pipeline

```
findings  ──►  CVSS v3.1 scoring  ──►  executive summary  ──►  HTML report
  (GUI)          (app/cvss.py)          (app/report.py)         (download)
  JSON store     live calculator         severity-aware prose
  (app/data.py)  metric dashboard        + stats breakdown
```

## Feature overview

| Area | Description |
|------|-------------|
| Findings | Add / edit / duplicate / delete findings with title, CVSS vector, assets, description, impact, evidence, remediation, references and status. Sorted live by severity. |
| CVSS Calculator | Visual CVSS v3.1 metric selector (AV/AC/PR/UI/S/C/I/A) with live score, severity color band bar, generated vector string, and one-click apply to a selected finding. |
| Executive Summary | Engagement metadata (client, dates, scope, assessor, notes) drives an auto-generated, severity-aware executive narrative plus recommendation priorities. |
| HTML Report | Generates a fully self-contained styled HTML document with hero header, overall risk pill, severity stat cards, executive summary, CVSS metric tables and detailed findings. Save to disk or open directly in the browser. |
| Persistence | All data stored in `redteam_data.json` next to the executable; survives restarts. |
| Sample Data | First launch auto-loads the built-in Acme Corporation sample engagement (8 realistic findings across all severities); the green **Load Sample Data** button restores it anytime. |

## Architecture

```
main.py                 entry point (bootstraps sys.path, launches GUI)
app/
  __init__.py           package marker
  cvss.py               CVSS v3.1 vector parser + base score + severity
  data.py               Finding model, ReportStore, JSON persistence, app dir
  report.py             executive summary builder + HTML report generator
  gui.py                tkinter application (4-tab notebook UI)
  sample_data.py        built-in Acme Corporation sample engagement + findings
build.bat               PyInstaller one-file --noconsole build script
architecture.md         this living architecture document
state.md                current development / acceptance state
memory.md               development journal / persistent memory
```

## Key design decisions

1. **No heavy dependencies.** tkinter ships with CPython, so the exe is small
   and self-contained via PyInstaller (`onefile`). No numpy / pandas / web runtime.
2. **Deterministic executive summary.** Rather than requiring an LLM or cloud
   API, the summary is rule-based and derived from severity distribution,
   posture grading and prioritized recommendations. Output is reproducible.
3. **CVSS v3.1 exact math.** `app/cvss.py` implements the official v3.1 base
   metric equations (ISS, scope-adjusted impact, exploitability, `ceil` to
   one decimal). Severity bands follow the spec: >=9.0 Critical, >=7.0 High,
   >=4.0 Medium, >0 Low.
4. **Single JSON datastore.** `redteam_data.json` stores the engagement object
   and findings list; written on every mutation so nothing is lost on exit.
5. **Dark colorful UI.** Custom tkinter palette with severity colour-coding
   (red/orange/yellow/green) used consistently across list, badges, calculator
   and report.

## Build & run

```powershell
python main.py          # run from source
.\build.bat             # build RedTeamReportGenerator.exe
```

## Report contents (HTML)

- Hero header: engagement title, client, assessor, dates, reference id
- Overall Risk Rating pill (Critical/High/Medium/Low)
- Severity stat cards (Critical / High / Medium / Low counts)
- Executive Summary (auto prose + priorities)
- Severity breakdown table
- Detailed findings: CVSS metric table, description, assets, impact,
  evidence, remediation, references — each card tinted by severity

## Data flow

`app/gui.py` is the only controller. It owns a `ReportStore`; user actions
mutate findings / engagement; every change triggers `ReportStore.save()`,
list re-population and refresh of summary + report previews. `app/report.py`
reads only the store, so it can be reused by future CLI/batch paths.