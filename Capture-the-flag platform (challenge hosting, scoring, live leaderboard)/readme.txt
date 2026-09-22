==========================================================
 NEON//GRID CTF PLATFORM
 Capture the Flag — challenge hosting, scoring,
 live leaderboard + HTML report download
==========================================================

WHAT IS THIS
------------
A self-contained jeopardy-style CTF platform. Players register,
solve challenges, submit flags, and watch a live neon leaderboard.
Admins host challenges from a built-in console and download a
standalone HTML report of the competition. Everything is stored in
a local JSON file — no internet, no external database needed.

QUICK START (WEB APP)
---------------------
  py -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  .venv\Scripts\python run.py --seed
  open http://127.0.0.1:5000

Logins after seeding:
  admin  / admin123        (admin console)
  neo    / pass-neo-123    (demo player)

BUILD THE EXE (WINDOWS)
-----------------------
  .venv\Scripts\pip install pyinstaller
  powershell -ExecutionPolicy Bypass -File build_exe.ps1
  -> dist\NeonGridCTF.exe   (double-click, then open the URL it prints)

FEATURES
--------
  * Challenge hosting: create/edit/delete challenges from the admin
    console (categories, points, dynamic scoring, hide/show)
  * Scoring: static points or dynamic decay (500 -> -100/solve -> floor 50)
  * Live leaderboard: medals, progress bars, refreshes every 5 seconds,
    CTF-standard tiebreak (earlier last solve wins)
  * Real-time feed: WebSocket pushes solves/attempts/joins as they happen
  * Score-over-time chart + category breakdown (canvas, no CDN needed)
  * HTML report: /report shows it, /report/download saves a standalone
    timestamped .html file that opens in any browser
  * Awesome neon UI: matrix rain, scanlines, glow, toasts, animations

ADMIN TASKS
-----------
  1. Login as admin -> Admin console
  2. Create challenges (title, category, points, flag, description)
  3. Toggle registration / competition open or closed in settings
  4. Download the report any time from the nav or scoreboard page

FILES
-----
  run.py               entry point (python run.py [--seed])
  build_exe.ps1        PyInstaller EXE build script
  requirements.txt     dependencies
  architecture.md      system design and API map
  memory.md            engineering notes for future sessions
  state.md             current implementation status
  todo.txt             roadmap
  app\                 Flask package (routes, services, db, websocket)
  app\templates\       pages incl. standalone report template
  app\static\          neon theme CSS + live UI JavaScript
  data\                created at runtime — ctf_db.json lives here

SECURITY NOTES
--------------
  * Change the default admin password after first login.
  * Set CTF_SECRET_KEY env var for non-default session signing.
  * Passwords are PBKDF2-SHA256 hashed with per-user salts.

HACK RESPONSIBLY — this is a platform for hosting CTFs, not a hacking tool.
