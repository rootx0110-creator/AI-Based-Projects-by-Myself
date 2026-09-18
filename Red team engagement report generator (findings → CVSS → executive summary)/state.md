# State — Red Team Engagement Report Generator

Updated: 2026-09-17

## Current status: DONE

### Done
- [x] CVSS v3.1 vector parser + base score + severity (`app/cvss.py`)
      - Verified against the official v3.1 equations (hand-checked):
        `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` -> 9.8 Critical
        `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:N/A:H` -> 6.5 Medium
        `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:H/A:N` -> 7.1 High
        `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:C/C:L/I:L/A:N` -> 5.0 Medium
        `CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:L/A:L` -> 3.5 Low
- [x] Findings model + JSON persistence (`app/data.py`)
- [x] Executive summary builder (severity-aware, deterministic) (`app/report.py`)
- [x] HTML report generator — self-contained styled doc with download (`app/report.py`)
- [x] GUI — 4 tabs (Findings / CVSS Calculator / Executive Summary / HTML Report)
      dark colorful theme, severity colour-coding, live CVSS bar (`app/gui.py`)
- [x] `main.py` entry point
- [x] Built-in sample data (`app/sample_data.py`) — auto-loads on first launch;
      green "Load Sample Data" button on Findings tab restores the demo dataset
- [x] PyInstaller build — `dist\RedTeamReportGenerator.exe` (12 MB, one-file,
      no console); smoke-tested: launches, auto-loads sample data, persists JSON
- [x] Source smoke tests pass (CVSS compliance, HTML generation, GUI lifecycle)

### Known limitations / notes
- Executive summary is deterministic (no LLM). Adding an optional LLM-backed
  narrator is a planned enhancement (see architecture.md).
- CVSS Temporal and Environmental vectors are not scored; base score only.
- `redteam_data.json` lives beside the exe; releases are not signed.
- tkinter `MouseWheel` binding is global to the toplevel; harmless but may
  co-scroll other scrollable areas on touchpads.
- No i18n; UI strings are English.
- First install already ships `dist\redteam_data.json` preloaded with the
  sample; if it is removed the app auto-loads the sample again on next start.

### Acceptance criteria (as agreed)
1. Launchable single-file exe on Windows.   — done (`dist\RedTeamReportGenerator.exe`)
2. Findings CRUD with live severity from CVSS vector.   — done
3. CVSS calculator produces correct v3.1 scores.   — done
4. Executive summary generated from stored findings.   — done
5. HTML report downloadable and visually polished/colorful.   — done
6. No data loss across restarts.   — done

## Roadmap (next)
1. Build exe, package with `build.bat`, verify startup + report download.
2. Optional: LLM executive narrative hook.
3. Optional: sample engagement loader for demos (add via Findings toolbar).
4. Optional: DOCX/PDF export.
5. Optional: code-signing and auto-update.