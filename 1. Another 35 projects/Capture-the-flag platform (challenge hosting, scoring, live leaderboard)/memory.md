# memory.md — NEON//GRID CTF platform

## What this is
A jeopardy-style Capture-the-Flag platform (challenge hosting, live scoring,
real-time leaderboard) built as a Flask web app that also packages into a
single Windows EXE. All data is stored in a local JSON file — no external
services, fully offline.

## Key facts
- Entry: `run.py` (dev server), admin seed `admin / admin123` on first boot.
- Data: `data/ctf_db.json` — atomic writes via `tmp + os.replace`, thread-locked.
- Scoring: static points or dynamic decay `max(50, base − 100×(solves−1))`.
- Tiebreak: equal score → earlier last-solve wins (CTF standard).
- Live feed: WebSocket `/ws/feed` via flask-sock + simple-websocket; scoreboard
  polls every 5 s as fallback; feed events: solve / attempt / user_join /
  user_login / admin.
- Report: `/report` renders standalone HTML (inline CSS, no JS);
  `/report/download` returns it as an attachment with timestamped filename.
- Secrets: passwords hashed with PBKDF2-SHA256 (100k iters, per-user salt).

## Environment notes
- Windows dev box, bash shell (Git Bash) — use POSIX syntax.
- Python must be invoked as `py` or `python`; venv at `.venv` if created.
- EXE build: `powershell -ExecutionPolicy Bypass -File build_exe.ps1`
  (PyInstaller, one-file, adds templates/static via --add-data).
- Frozen mode: config._base_dir() puts data/ next to the EXE (sys.executable);
  app_factory retargets template/static folders to sys._MEIPASS. run.py
  probes 10 ports so double-launching the EXE is safe.
- Bash quirk: launching the EXE (or any server) with `&` in a terminal tool
  call can hold handles until timeout even after the check succeeds — run
  checks in a separate call instead of waiting in the same command.
- Set `CTF_DATA_DIR` to relocate storage; `CTF_HOST/CTF_PORT/CTF_DEBUG` for serving.

## Gotchas
- If the UI looks dead, check that `data/` was created and `--seed` was used at
  least once for demo content (or POST `/_demo_seed`).
- Flags are compared case-insensitively but must match exactly otherwise.
- The websocket feed auto-reconnects with backoff; if sockets are blocked by a
  proxy, the UI silently degrades to polling.

## Ideas / backlog
- Hint unlock system (flag_hint column already exists).
- Team accounts (currently one user = one team).
- CSV export alongside the HTML report.
