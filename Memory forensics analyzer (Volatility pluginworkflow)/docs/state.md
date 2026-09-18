# Project State

_Last updated: 2026-09-17_

## Phase

**Analysis Platform — Release Candidate**
The application core (UI, workflow engine, doc vault, HTML report) is complete.

## What is Done

- [x] PySide6 dark-theme desktop shell (sidebar navigation, header, pages)
- [x] Dashboard with case overview and live workflow progress
- [x] 9-stage Volatility plugin workflow with run/rerun and per-step results
- [x] Document vault rendering `architecture.md`, `state.md`, `memory.md`
- [x] State persistence (`analyzer_state.json`)
- [x] Self-contained HTML report generator with download + preview
- [x] One-file `.exe` packaging via PyInstaller

## In Progress

- [ ] Volume-hints / dynamic profile selection inside the workflow UI
- [ ] Timestamped export of step logs (CSV/Kape-style timeline)

## Risks / Notes

- Simulated stage execution used by default; wire to a real Volatility3
  engine by pointing at `vol.py`/`vol3` for production casework.
- Large memory images keep everything in an offline sandbox — no network egress.