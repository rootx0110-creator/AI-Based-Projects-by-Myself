# Wireless Network Auditor - Memory Model

**Document that describes how the application manages in-memory state, caches,
session memory, and long-term persistence.**

---

## 1. Overview

"Memory" in this application is split into layers with different lifetimes:

| Layer | Lifetime | Storage | Contents |
|-------|----------|---------|----------|
| Runtime process memory | Process lifetime | Python objects | Active capture session, scan cache, executed-command registry |
| HTTP session memory | Browser session | Flask `session` (signed cookie) | UI preferences, last selected target |
| Persistent memory | Forever (until deleted) | SQLite database |  Networks, capture sessions, reports |
| File memory | Forever (until deleted) | Filesystem | `.cap` files, generated `.html` reports, DB file itself |

---

## 2. Runtime Memory (in-process)

Managed by the modules in `capture/`.

### 2.1 Active capture registry

`capture/handshake.py` keeps a single global registry:

```python
ACTIVE = {
    "running": bool,
    "session_id": int | None,
    "ssid": str,
    "bssid": str,
    "channel": int,
    "state": str,            # IDLE|LISTENING|EAPOL_DETECTED|HANDSHAKE_COMPLETE
    "eapol_messages": int,   # 1..4 observed
    "packets": int,          # raw packet counter
    "deauth_sent": int,
    "started_at": datetime,
    "last_updated": datetime,
}
```

Only **one** capture runs at a time (deliberate: prevents interface contention
and keeps the simulation deterministic).

### 2.2 Scan cache

`capture/scanner.py` caches the last scan result:

```python
SCAN_CACHE = {"last_scan_at": t, "networks": [...]}
```

- Reused by `/api/networks` so repeated page loads do not rescan.
- In simulation mode the seed is fixed per lab, so repeated scans are stable.

### 2.3 Command registry (live mode)

`capture/*` modules record executed external commands:

```python
COMMAND_LOG = [...]  # {ts, cmd}, appended before subprocess.run
```

Exposed in readme/UI as the "Activity" audit trail - proves what ran against which target.

---

## 3. Session Memory (browser)

Flask signed-cookie sessions (`app.secret_key` from `config.py`) persist:

| Key | Type | Purpose |
|-----|------|---------|
| `last_target` | dict | Last selected {ssid, bssid, channel} |
| `scan_count` | int | Number of scans the user has run this browser session |
| `theme` | str | Reserved for future theme toggle |

Sessions are lightweight (no security-relevant data).

---

## 4. Persistent Memory (SQLite)

Single file: `database/settings.db` (tune via `AUDITOR_DB`).

### 4.1 networks
```sql
CREATE TABLE IF NOT EXISTS networks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ssid        TEXT NOT NULL,
  bssid       TEXT NOT NULL UNIQUE,
  channel     INTEGER,
  signal_dbm  INTEGER,
  encryption  TEXT,
  clients     INTEGER,
  first_seen  TEXT,
  last_seen   TEXT,
  capture_count INTEGER DEFAULT 0
);
```
Meant as the growing "seen networks" ledger.

### 4.2 sessions
```sql
CREATE TABLE IF NOT EXISTS sessions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ssid        TEXT,
  bssid       TEXT,
  channel     INTEGER,
  started_at  TEXT,
  ended_at    TEXT,
  duration_s  REAL,
  packets     INTEGER,
  eapol_messages INTEGER,
  status      TEXT,          -- COMPLETE | PARTIAL | ABORTED
  deauth_used INTEGER DEFAULT 0,
  seed        TEXT
);
```

### 4.3 reports
```sql
CREATE TABLE IF NOT EXISTS reports (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   INTEGER,
  ssid         TEXT,
  bssid        TEXT,
  title        TEXT,
  generated_at TEXT,
  score        INTEGER,
  file_name    TEXT
);
```

All timestamps are ISO-8601 UTC strings generated with `datetime.now(timezone.utc)`.

---

## 5. File Memory (filesystem)

```
captures/                      # captured pcap files (live mode)
  <ssid>-<tick>.cap
reports/out/                   # generated reports
  report-<id>-<ssid>.html
database/settings.db           # SQLite persistence
```

Kept inside the project root so the app stays portable and uninstalls cleanly.

---

## 6. Memory Budget & Cleanup

- Runtime: bounded - the active registry is a fixed dict; `COMMAND_LOG` is trimmed to last 500 entries.
- Cash/scan cache: replaced on every new scan, never grows.
- SQLite: designed for lab-scale data (hundreds of rows); no vacuum planned but `PRAGMA journal_mode=WAL` improves concurrency.

Maintenance commands:
```
python - <<'PY'
import database.db as db
db.prune_reports(older_than_days=90)
PY
```

---

## 7. Concurrency Notes

- SQLite connections are **per-request** in Flask (opened, used, closed with `contextlib.closing`) to avoid thread-safety issues.
- The capture thread writes to a Python-side registry only; it does **not** touch the DB directly. The Flask request thread persists the session when status is polled and the state reaches a terminal value.
- This avoids any cross-thread DB writes and keeps memory coherent.