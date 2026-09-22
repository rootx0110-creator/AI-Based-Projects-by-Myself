# State — Compliance Automation Suite

_Last updated: 2026-09-22_

## Current status: MVP complete — running and verified

### Done
- [x] Backend: stdlib HTTP server (`app/server.py`) with JSON API
- [x] Datasets: ISO 27001:2022 Annex A (93 controls), BB ICT Guideline
      v2.0 (18 domains), NIST CSF 2.0 (22 categories) + explicit crosswalk
- [x] Services: scoring, maturity levels, gap analysis with risk scores,
      control mapper, crosswalk matrix
- [x] Persistence: JSON store, atomic writes, audit log, corrupt-file recovery
- [x] Web UI: dark SPA — Dashboard, Control Register (assess/bulk edit),
      Control Mapper, Gap Analysis, Crosswalk, Reports view
- [x] HTML report: self-contained, downloadable at `/api/report`
- [x] EXE build: `build_exe.ps1` (PyInstaller onefile) + `exe_start.py`
- [x] Docs: architecture.md, readme.txt, memory.md, state.md, todo.txt
- [x] Smoke-tested server + all API endpoints (see "Verification" below)

### Verified
- `python run.py --no-browser --port 9999` serves the SPA and API
- `/api/summary`, `/api/catalog`, `/api/gaps`, `/api/matrix`, `/api/map`,
  `/api/report` all return 200
- POST `/api/status`, `/api/bulk`, `/api/organization` persist to
  `data/compliance_data.json`
- Report downloads as valid HTML with inline CSS

### Not started / known limits
- [ ] EXE not yet compiled on this machine (needs `pip install pyinstaller`,
      then `powershell -ExecutionPolicy Bypass -File build_exe.ps1`)
- [ ] Crosswalk is a curated subset — a fuller public mapping (e.g. ISO to
      BB clause-level) can replace `app/data.py` without touching other code
- [ ] No authentication (local-only by design; binds 127.0.0.1)
- [ ] No CSV/PDF export (HTML report covers the download requirement)

### Quick commands
```bash
python run.py                    # dev server, opens browser at :9999
python run.py --port 9000        # custom port
powershell -ExecutionPolicy Bypass -File build_exe.ps1   # build EXE
dist/ComplianceSuite.exe         # run the EXE
```
