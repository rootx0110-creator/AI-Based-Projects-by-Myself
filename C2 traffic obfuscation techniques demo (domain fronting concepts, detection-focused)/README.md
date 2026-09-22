# C2 Traffic Obfuscation Techniques Demo
### Domain fronting concepts — detection focused

An offline, **defensive security training** application that simulates and
analyses how command-and-control (C2) traffic is obfuscated — and how a
detection engineer would spot it. Ships as a standalone Windows EXE with a
dark-themed GUI and a one-click **HTML report** exporter.

> All payloads and timestamps are synthetic. Nothing here talks to a network.

---

## Features

| Module | What it does |
|---|---|
| **Techniques** | Encodes a command through Base64, XOR Stream, RC4 and AES-128-CBC — stage-by-stage or chained round-trip with entropy metrics |
| **Beacon Lab** | Simulates check-in schedules with configurable interval + jitter; computes CoV and a regularity severity verdict |
| **Domain Fronting** | Interactive SNI-vs-Host-header mismatch walkthrough with detector notes and controls |
| **Detection Lab** | Scores payloads by entropy, non-printability, framework signatures and compactness; merges beacon regularity |
| **HTML Report** | Exports the whole session as a self-contained styled HTML file (inline SVG charts, zero dependencies) |

## Quick start

```powershell
# run from source
python launcher.py

# build the EXE
.\build.ps1
# -> dist\C2TrafficObfuscationLab.exe
```

## What the report contains

1. Session summary + risk badges
2. Obfuscation technique catalogue
3. Encoded payload versions (hex + entropy)
4. Beacon schedule chart, stats and verdict timeline
5. Domain fronting SNI/Host discovery-layer view
6. Detection findings and signature matches

Open any generated `.html` file in a browser — it is fully self-contained
(inline CSS/SVG, no CDN links), so it works offline forever.

## Related opencode skills (in `skills/`)

- **c2-beacon-lab** — run and interpret beacon jitter/regularity simulations
- **domain-fronting-lab** — walk the SNI vs Host-header detection exercise
- **html-report-generator** — turn an analysis into the styled offline report

## Dependencies

- Python 3.10+ (stdlib + `cryptography` for AES; degrades gracefully without it)
- PyInstaller (build only)

## Disclaimer

Educational material on attacker tradecraft for the purpose of defending
networks. Use only in environments you own or are authorized to test.