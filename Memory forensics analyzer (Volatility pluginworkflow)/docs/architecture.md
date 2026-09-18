# Memory Forensics Analyzer — Architecture

## Overview

The **Memory Forensics Analyzer** is a local, desktop-first application that guides an
analyst through a structured **Volatility plugin workflow** for Windows memory images.
It combines documentation, workflow orchestration, artifact collection and report
generation into a single offline tool.

## High-Level Design

```
                          ┌──────────────────────────────┐
                          │      Desktop UI (PySide6)    │
                          │  Dashboard | Workflow | Docs │
                          │  Report Preview | Download   │
                          └──────────────┬───────────────┘
                                         │
                              ┌──────────▼───────────┐
                              │   Workflow Engine    │
                              │  step model + state  │
                              └──────────┬───────────┘
                       ┌──────────────────┼──────────────────┐
                       │                  │                  │
              ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼───────┐
              │  Capture Stage  │ │ Analysis Stage │ │ Report Stage  │
              └─────────────────┘ └───────────────┘ └───────────────┘
```

## Components

| Component            | Responsibility                                                    |
|----------------------|-------------------------------------------------------------------|
| `Dashboard`          | Case overview, progress summary, engine/volatility detection      |
| `Workflow Engine`    | Ordered execution of Volatility stages; tracks step status/results|
| `Document Vault`     | Reads `architecture.md`, `state.md`, `memory.md`              |
| `Report Generator`   | Builds a self-contained HTML report from state + results          |
| `State Store`        | Persists workflow progress to `analyzer_state.json`               |

## Volatility Plugin Stages

1. **Acquisition & Verification** — `crashinfo`, `memmap`, hash verification
2. **Profile Identification** — `imageinfo`, `kdbgscan`, `banner`
3. **Process Analysis** — `pslist`, `pstree`, `psscan`, `psxview`
4. **Network Analysis** — `netscan`, `connections`, `sockscan`
5. **Malware Triaging** — `malfind`, `dlllist`, `apihooks`, `handles`
6. **Kernel & Drivers** — `modules`, `modscan`, `driverscan`, `ssdt`
7. **Registry & Artifacts** — `hivelist`, `printkey`, `dumpregistry`, `shellbags`
8. **Memory Extraction** — `memdump`, `procdump`, `dumpfiles`
9. **Reporting** — timeline synthesis + export

## Tech Stack

- **Python 3.14** application code
- **PySide6 (Qt 6)** for the desktop UI
- **PyInstaller** for single-file `.exe` distribution
- **Volatility3** (optional external engine, detected at runtime)

## Build / Run

- Dev:      `python main.py`
- Build:    `pyinstaller MemoryForensicsAnalyzer.spec`