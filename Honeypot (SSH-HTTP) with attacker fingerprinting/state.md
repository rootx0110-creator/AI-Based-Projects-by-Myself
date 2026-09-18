# State

This document tracks the runtime state model of the application.

## System State

| Key | Type | Initial | Updated by | Meaning |
|---|---|---|---|---|
| `server_state.ssh.running` | bool | `false` | `/api/start`, `/api/stop` | Whether the SSH honeypot listener thread is active |
| `server_state.ssh.port` | int | `2222` | startup | TCP port the SSH honeypot binds |
| `server_state.ssh.started_at` | float | `null` | `/api/start` | `time.time()` when last started |
| `server_state.http.running` | bool | `false` | `/api/start`, `/api/stop` | Whether the HTTP honeypot listener thread is active |
| `server_state.http.port` | int | `8080` | startup | TCP port the HTTP honeypot binds |
| `server_state.http.started_at` | float | `null` | `/api/start` | `time.time()` when last started |
| `server_state.db_initialized` | bool | `false` | first startup | Whether the SQLite schema is created |

## Persisted State (SQLite: `honeypot.db`)

### `attackers`
| Column | Type | Notes |
|---|---|---|
| `fingerprint_hash` | TEXT (unique, pk via auto id) | sha256 fingerprint of attacker behavior |
| `first_seen` / `last_seen` | TEXT (ISO) | activity window |
| `total_attacks` | INTEGER | cumulative count |
| `risk_score` | REAL | rolling 0–100 score |
| `tags` | TEXT (JSON array) | detected tool names, e.g. `["nmap"]` |

### `events`
| Column | Type | Notes |
|---|---|---|
| `protocol` | TEXT | `ssh` or `http` |
| `src_ip`, `src_port`, `dst_port` | TEXT/INT | network coordinates |
| `event_type` | TEXT | `ssh_auth`, `ssh_command`, `http_probe` |
| `username`, `password` | TEXT | credential attempts (SSH) |
| `user_agent`, `headers` | TEXT | HTTP fingerprinting material |
| `raw_data` | TEXT | request line / command body |
| `fingerprint_hash` | TEXT (FK) | link to `attackers` |
| `geo_*`, `asn`, `isp` | TEXT/REAL | reserved for GeoIP enrichment |

### `http_requests` / `ssh_sessions`
Rich payloads for each event (full headers, executed command list, session duration).

### `threat_intel`
Optional known-as labeling and malware-family history per fingerprint hash.

## Front-End State (browser)

| Variable | Purpose |
|---|---|
| `state.dashboard` | last `/api/dashboard` payload |
| `state.events` | last `/api/events` payload |
| `state.attackers` | last `/api/attackers` payload |
| `state.protocolFilter`, `state.typeFilter` | applied event filters |
| `state.interval` | poll cadence (3 s) |
| `activeSection` | currently visible nav section (drives polling) |

## State Transitions

```
app starts
   -> database.init_db()
   -> server_state.db_initialized = true
   -> Flask serves dashboard on :5001
        |
  POST /api/start
        |
        v
   server_state.ssh.running = true   (SSHListener thread)
   server_state.http.running = true  (HTTPServer thread)
        |
  attacker connects
        |
        v
   event emitted -> db persisted -> UI refreshed (3s poll)
        |
  POST /api/stop
        |
        v
   server_state.*.running = false (listener sockets closed)
```

## Persistence Properties

- WAL journal mode enabled for concurrent read/write.
- All event writers (`app.py`/listeners) run on separate threads; SQLite access is
  serialized by the connection context manager.
- Reports (`/api/report/html`, `/api/report/json`) are generated on demand from the
  current persisted state — they always reflect the latest captured data.