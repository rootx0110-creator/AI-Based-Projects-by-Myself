AI-Driven CTF Hint Engine for Training Platforms
=================================================

What it is
----------
A web app (and optionally a standalone EXE) that coaches trainees through CTF
challenges on a training platform. Instead of dumping solutions, it serves
ESCALATING hints:

  Level 1..N   -> prepared hints authored by the trainer (nudge -> approach -> path)
  Afterwards   -> an AI coach (OpenAI-compatible or Anthropic/Claude) takes over
  No API key?  -> the built-in per-category engine hints keep working offline.

Features
--------
* Challenge library with Web / Crypto / Forensics / Reversing / OSINT / Pwn / Misc
* Hint engine with progressive disclosure; every hint is time-stamped and logged
* Flag verification (case-insensitive) to close out a challenge
* Trainer tools: add challenges, mark as solved manually, configure the AI provider
* HTML report download + in-app report preview (stats, per-challenge status, hint timeline)
* 9 seeded training challenges so the app runs out of the box

Run (Python)
------------
  1. Install deps:  pip install -r requirements.txt
  2. Start:         double-click start.bat   (or: python app.py)
  3. The browser opens at http://127.0.0.1:<port> automatically.
     Progress is stored in data\hintengine.db

Run (EXE)
---------
  1. Build:         python build_exe.py
  2. Run:           CTFHintEngine.exe   (single file, no Python required)
     Progress is stored in a data\ folder created next to the EXE.

Configure the AI Coach
----------------------
Open Settings -> AI Coach Provider:
  * Enable the coach, pick "OpenAI compatible" or "Anthropic".
  * Base URL defaults to the official endpoints (https://api.openai.com/v1,
    https://api.anthropic.com). Any OpenAI-compatible local proxy works too.
  * Enter your API key + model, click "Test Connection", then Save.
If the AI call fails (offline, bad key, timeout) the engine silently falls back
to its prepared + local category hints.

Notes on flags
--------------
Seeded flags are stored in plaintext so lab trainers can verify immediately.
For real production platforms, hash flags (SHA-256) and compare hashes instead.

Files
-----
  app.py          Flask server + routes
  database.py     SQLite models, seeding, queries
  ai_engine.py    AI providers (OpenAI / Anthropic) + local fallback hints
  report.py       Self-contained HTML report generator
  templates/      Jinja2 pages (dashboard, challenges, challenge, settings, report)
  static/         style.css + app.js
  build_exe.py    PyInstaller one-file EXE builder
  start.bat       Windows launcher (Python mode)