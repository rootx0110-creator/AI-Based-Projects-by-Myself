# Capture the Flag (CTF) Platform — Architecture

**NEON//GRID CTF** — a self-contained jeopardy-style CTF platform with challenge
hosting, dynamic scoring, a real-time leaderboard, and downloadable HTML reports.
Runs as a local web app and packages into a single Windows EXE.

## 1. High-level overview

```
┌──────────────────────────── Browser (client) ────────────────────────────┐
│  Jinja pages (base/challenges/scoreboard/admin/report)                   │
│  app.js — matrix rain · toasts · WebSocket feed · live scoreboard poll   │
│           canvas score-over-time chart · flag submit modal               │
└───────────────▲──────────────────────────────▲───────────────────────────┘
        HTTP (JSON/HTML)               WebSocket /ws/feed
┌───────────────┴──────────────────────────────┴───────────────────────────┐
│                        Flask app (app/app_factory.py)                    │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────────────┐  │
│  │ routes.py   │   │ services.py  │   │ websocket.py (flask-sock hub) │  │
│  │ thin HTTP   │──▶│ business     │   │ broadcasts solve/join events  │  │
│  │ controllers │   │ rules        │   └───────────────────────────────┘  │
│  └─────────────┘   └──────┬───────┘                                      │
│                           ▼                                              │
│                   ┌──────────────┐                                       │
│                   │ db.py        │  JSON file store (atomic writes,      │
│                   │ JSONDatabase │  thread lock, seed data)              │
│                   └──────┬───────┘                                       │
│                          ▼                                               │
│              data/ctf_db.json  (single source of truth)                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## 2. Modules

| Path | Responsibility |
|---|---|
| `run.py` | Entry point (CLI: `--seed`), starts dev server |
| `app/config.py` | Env-driven config: host/port, data dir, scoring rules |
| `app/app_factory.py` | Flask factory, wiring db + sockets + blueprint |
| `app/routes.py` | HTTP endpoints (auth, challenges, scoreboard, admin, report) |
| `app/services.py` | Scoring, stats, auth rules, submission validation, feed events |
| `app/db.py` | JSON persistence, password hashing (PBKDF2), scoreboard math |
| `app/websocket.py` | `/ws/feed` WebSocket hub, live event broadcast |
| `app/features/demo.py` | Demo data seeder (users, solves, failed attempts) |
| `app/features/extract.py` | Report payload extraction (shared by future exports) |
| `app/templates/*` | Jinja pages incl. standalone `report.html` (inline CSS) |
| `app/static/*` | `css/style.css` (neon theme), `js/app.js` (live UI runtime) |

## 3. Key design decisions

- **JSON file DB, not SQL** — zero external dependencies, survives copy/paste of
  the folder, trivially embeddable in a PyInstaller EXE. Writes are atomic
  (`tmp` + `os.replace`) and guarded by an `RLock`.
- **Dynamic scoring** — `points = max(minimum, base − slope × (solves−1))`
  computed at read time, so the leaderboard is always fair without migrations.
- **Live updates** — WebSocket hub (`/ws/feed`) pushes `solve/attempt/join`
  events; scoreboard also polls every 5 s as a fallback, so the UI stays live
  even if sockets are blocked.
- **Report as server-rendered HTML** — `/report` renders a standalone page
  (inline CSS, no JS) that downloads via `/report/download` and opens anywhere.

## 4. API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Landing page + live stats |
| GET/POST | `/login`, `/register` | Auth |
| GET | `/challenges` | Mission board (login required) |
| POST | `/api/submit` | Flag submission (JSON) |
| GET | `/api/scoreboard` | Ranked board (poll target) |
| GET | `/api/stats`, `/api/graph` | KPIs, score-over-time series |
| GET | `/api/solves/<id>` | Solve list per challenge |
| WS | `/ws/feed` | Live event feed |
| GET | `/report`, `/report/download` | HTML report / download |
| GET/POST/DELETE | `/admin/api/...` | Admin CRUD + platform config |

## 5. Scoring rules

- Static challenges pay their point value.
- Dynamic challenges decay: `base 500 → −100/solve → floor 50`.
- Ranking: score desc, then **earliest last solve** wins ties (CTF standard).

## 6. Packaging

`build_exe.ps1` runs PyInstaller with `--add-data` for templates/static,
producing `dist/NeonGridCTF.exe` (server + UI in one file; data folder is
created next to the EXE at first run).
