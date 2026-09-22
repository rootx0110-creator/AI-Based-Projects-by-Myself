# Purple Team Capstone — red builds, blue detects, both document MITRE ATT&CK

A self-contained Windows **purple team lab application** (shipped as a single
`.exe`) where:

* **Red builds** — simulates 10 MITRE ATT&CK techniques against a sandboxed lab target.
* **Blue detects** — scans the target with 9 sigma-style detection rules mapped to ATT&CK data sources.
* **Both document MITRE ATT&CK** — every artifact and every finding carries its technique id, and an exercise-wide **coverage matrix** (technique × rule) is rendered and reported.
* **Reports download as HTML** — one self-contained, printable file (executive summary, timeline, findings, coverage matrix, gap analysis).

Everything is **simulated/lab-only**: red modules write files under
`outputs/lab_target` and use one ephemeral loopback socket for the exfiltration
technique. Nothing modifies the real OS, registry, services or remote hosts.

## Quick start

```powershell
# look at the code first, then either build, or…
python main.py              # GUI
python main.py --cli        # headless full exercise + HTML report
```

```powershell
# build the executable
powershell -ExecutionPolicy Bypass -File build_exe.ps1
.\dist\PurpleTeamCapstone.exe
```

## Contents

| Path | Purpose |
| --- | --- |
| `purpleteam/` | source package (GUI, engine, HTML report, docs) |
| `main.py` | entry point (GUI + `--cli`/`--docs`/`--selftest`) |
| `purpleteam/mitre.py` | MITRE ATT&CK + detection-rule registry (single source of truth) |
| `purpleteam/redteam.py` | red build modules (simulated techniques) |
| `purpleteam/blueteam.py` | blue detection rules + scan engine |
| `purpleteam/report.py` | HTML report builder + download/open helpers |
| `purpleteam/app.py` | tkinter GUI (Dashboard / Red / Blue / MITRE / Report) |
| `docs/` | generated docs (architecture, coverage, run instructions) |
| `tools/make_icon.py` | regenerates `assets/purpleteam.ico` |
| `build_exe.ps1`, `PurpleTeamCapstone.spec` | one-file windowed EXE build |
| `dist/` | built executable + its `outputs/` (after first run) |

## The exercise

1. **Dashboard** — pick techniques, click *Build (RED)* then *Detect (BLUE)*.
2. **Red Build** tab — watch artifacts land (task XML, lure doc, Run-key exports,
   PS transcripts, recon report, dropped/renamed binaries, exfil chunk, API trace).
3. **Blue Detect** tab — findings with severity + fidelity (dedicated rule vs catch-all).
4. **MITRE Coverage** tab — technique × rule matrix, live.
5. **Report / Export** tab — **Download HTML report…**, then open or print it.

## MITRE mapping preview

| Technique (red builds) | Tactic | Dedicated rule (blue) |
| --- | --- | --- |
| T1053.005 Scheduled Task | Persistence | RULE-SCHTASK |
| T1566.001 Spearphishing Attachment | Initial Access | RULE-DL-ATTACHMENT |
| T1547.001 Registry Run Keys / Startup | Persistence | RULE-AUTOSTART |
| T1059.001 PowerShell | Execution | RULE-PS-OBFUSC |
| T1027 Obfuscated Files or Information | Defense Evasion | RULE-PS-OBFUSC |
| T1082 System Information Discovery | Discovery | RULE-DISCOVERY |
| T1105 Ingress Tool Transfer | Command and Control | RULE-TOOL-DROP |
| T1036.005 Masquerading | Defense Evasion | RULE-TOOL-DROP |
| T1041 Exfiltration Over C2 Channel | Exfiltration | RULE-EXFIL |
| T1106 Native API | Execution | RULE-API-CALL |

## Verify

```powershell
python -m purpleteam.selftest     # engine + report invariant checks (exit 0 = OK)
python -m purpleteam.docs         # regenerate docs/*.md from the registry
```

**Legal/ethics:** for authorized labs and defensive education only.