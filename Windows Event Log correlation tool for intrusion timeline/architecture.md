# Architecture — Windows Event Log Correlation Tool for Intrusion Timeline

## 1. Overview

A standalone Windows desktop application that collects Windows Event Logs
(live or from `.evtx` files), correlates raw events against MITRE ATT&CK
detection rules, reconstructs an intrusion timeline / kill chain, and exports
a self-contained HTML report.

Tech stack:
* Language: Python 3.9+
* GUI: tkinter / ttk (dark custom theme, no external UI deps)
* Log access: `wevtutil` (system tool, always present on Windows)
* Packaging: PyInstaller single-file `.exe` (no runtime reinstall)

No privileged service, no persistence, no network services. Everything runs
locally and on-demand.

## 2. Module Map

```
main.py                 Entry point (creates Tk app, starts GUI)
app/
  models.py             EventRecord, Alert, Rule, Panels, Severity, Phase enums
  parser.py             wevtutil ingestion (live channels + .evtx), XML -> EventRecord
  rules.py              MITRE ATT&CK detection rule definitions + evaluators
  correlator.py         Runs rules, builds alerts, kill-chain phases, incident chains
  report.py             Single-file HTML report generator (dark UI, CSS timeline)
  gui.py                tkinter user interface (dashboard/timeline/alerts/events)
```

Directory (project root):
* `architecture.md`, `memory.md`, `state.md`, `todo.md`, `readme.txt`
* `requirements.txt`, `build.bat`, `WECT.spec` (PyInstaller)

## 3. Data Flow

```
                    +------------------+
                    | wevtutil qe XML  |
                    +--------+---------+
                             |
                             v
  live channel / .evtx -> parser.events_from_target() -> [EventRecord]
                             |
                             v
                    correlator.run()  -------------------+
                       |  index by EventID                |
                       +-> rules.evaluate (time windows)  |
                       |     produce alerts               |
                       +-> phase assignment (kill chain)  |
                       +-> chain builder (group by key)   |
                             |
                             v
                Alerts (+ linked raw events) sorted
                             |
              +--------------+--------------+
              |                             |
              v                             v
        GUI tabs                    report.html (self-contained)
```

## 4. Ingestion (parser.py)

* Uses `wevtutil qe` with `/f:xml /rd:true /c:<n>`.
* Live targets: named channels (`Security`, `System`, `Application`, plus
  optional channels such as `Microsoft-Windows-PowerShell/Operational`,
  `Microsoft-Windows-Sysmon/Operational`, `Microsoft-Windows-TaskScheduler/
  Operational`, ...).
* File targets: path to a `.evtx` file (wevtutil treats a path as a log).
* Optional time filter is injected as an XPath:
  `*[System[TimeCreated[@SystemTime>='...UTC...']]]`
  (always compared in UTC).
* Streaming parse: XML is split per `</Event>`, parsed with ElementTree,
  namespace-stripped, producing `EventRecord`s with a `data` dict keyed by
  `<Data Name=...>` (fallback: `Data0`, `Data1`, ...).
* The rendering of messages is handled by wevtutil itself, so English/other
  system-installed formats are preserved in the raw output.

## 5. Detection (rules.py / correlator.py)

Each rule = {id, name, tactic, technique, severity, description, evaluator}.

Evaluator kinds:
* `excess`   — group events by a key attribute; flag if N matches inside a
               sliding time window (brute force, spray, enumeration).
* `sequence` — flag when event A (trigger) is followed by event B with a
               matching key inside a window (logon-after-bruteforce).
* `single`   — flag each matching event individually (lsass access, run keys).

Rules cover MITRE ATT&CK tactics: Initial Access, Execution, Persistence,
Privilege Escalation, Credential Access, Discovery, Lateral Movement,
Defense Evasion, Impact.
See `todo.md` / `rules.py` docstring for the full list.

Kill-chain phases assigned to events: Reconnaissance, Initial Access,
Execution, Persistence, Privilege Escalation, Credential Access,
Lateral Movement, Defense Evasion, Exfiltration, Impact, Unknown.

Incident chains: alerts sharing a subject user / source IP / target within a
configurable adjacency window are grouped into a single multi-stage intrusion
chain (`stage 1..n`), and each chain gets a cumulative severity score.

## 6. Report (report.py)

Generates ONE self-contained HTML file (inline CSS + small JS):
* Dark themed, MITRE-inspired dashboard
* KPI cards (events, alerts by severity, hosts, users, timespan)
* Tactic/technique coverage bars
* Vertical intrusion timeline colored by phase with alert expanders
* Incident chain cards (stage-by-stage walkthrough)
* Full alerts table with raw-event drill down
* Raw events table (capped)

All HTML is escaped; artifacts count is capped to keep files manageable.

## 7. GUI (gui.py)

tkinter with a custom dark `ttk.Style` (clam base):
* Banner header + status pills
* Sidebar: Load Live Logs, Load EVTX Files, Analyze, Generate HTML Report, Clear
* Notebook tabs: Dashboard | Timeline | Alerts | Events
* All heavy work (ingest + correlation) runs on a worker thread with progress
  bar and cancel support; UI is updated via `root.after()`.
* Dashboards and tables render inline (Treeview with severity tag colors).

## 8. Build & Packaging

`build.bat`:
1. `pip install pyinstaller`
2. `pyinstaller --onefile --windowed --name IntrusionTimelineTool main.py`

Runtime requires only Windows + wevtutil. tcl/tk is bundled by PyInstaller.

## 9. Security & Privacy

* The system never sends data off the machine.
* `wevtutil` may require elevation for some channels on hardened hosts;
  failure per channel is reported instead of aborting the run.
* Report export path is user-selected via a save dialog.