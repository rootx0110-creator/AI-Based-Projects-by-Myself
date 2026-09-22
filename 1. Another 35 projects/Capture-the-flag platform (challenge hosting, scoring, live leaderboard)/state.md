# state.md — NEON//GRID CTF platform

## Current state (2026-09-22)

**Status: v1.1 complete — web app + verified EXE build.**

### EXE build (verified 2026-09-22)
- `dist/NeonGridCTF.exe` (≈17.5 MB, PyInstaller 6.22.3 onefile).
- Verified from a scratch dir: boots, seeds with `--seed`, serves pages,
  login works, `/report/download` returns attachment, WS handshake = 101.
- `data/ctf_db.json` is created **next to the EXE** (config._base_dir handles
  the frozen case via `sys.executable`; templates/static resolve from
  `sys._MEIPASS` in app_factory).
- run.py probes ports 5000–5009, so double-launching never crashes.
- Rebuild: `powershell -ExecutionPolicy Bypass -File build_exe.ps1`
  (or run the PyInstaller command directly — see git history/transcript).

### Working
- [x] Flask app factory + JSON database (atomic, seeded)
- [x] PyInstaller one-file EXE (`dist/NeonGridCTF.exe`) — built & smoke-tested
- [x] Auth: register / login / logout, PBKDF2-hashed passwords, session
- [x] Challenge board: categories, dynamic scoring badges, solved markers
- [x] Flag submission API with live feedback (toasts + feed)
- [x] Live scoreboard: 5 s polling, medals, progress bars, tiebreak by time
- [x] WebSocket live feed (`/ws/feed`) with auto-reconnect
- [x] Canvas score-over-time chart + category breakdown
- [x] Admin console: challenge CRUD, platform settings (name, open/close)
- [x] HTML report: server-rendered, downloadable with timestamped filename
- [x] Demo seeder (10 users, solves, failed attempts) via `python run.py --seed`
- [x] Neon hacker UI: matrix rain, scanlines, glow, animations

### Bugfixes (2026-09-22, late)
- Challenge cards now open the flag modal from ANY category grid — JS uses
  document-level event delegation (the old code bound to a non-existent
  `#ch-grid` id, so clicks did nothing).
- `/report` is now an in-app page (nav stays visible) with live iframe preview
  + download button; the nav-less doc moved to `/report/standalone`.
- EXE rebuilt and template/static contents verified inside the bundle.

### Not done yet
- [ ] Hint unlock flow (column exists, UI pending)
- [ ] Team model (multi-user teams)
- [ ] CSV/PDF export
- [ ] Rate limiting on submissions

### Verified
- `py -m compileall` passes on all modules (see transcript)
- Manual smoke test: server boots on 127.0.0.1:5000, pages render,
  `/report/download` returns `text/html` attachment.

### Quick start (for next session)
```bash
py -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python run.py --seed
# open http://127.0.0.1:5000 — login: neo / pass-neo-123 or admin / admin123
```
