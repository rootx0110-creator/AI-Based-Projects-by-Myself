# Wireless Network Auditor - System Architecture

**Version:** 1.0.0
**Purpose:** Capture and analyze WPA/WPA2 4-way handshakes against your own lab access point for authorized security education.

---

## 1. Overview

The Wireless Network Auditor is a self-contained web application that:

1. Scans the 2.4/5 GHz spectrum for access points in range.
2. Targets a selected lab access point (SSID/BSSID).
3. Captures the WPA/WPA2 4-way EAPOL handshake (optionally triggered with deauthentication frames).
4. Records session metadata and captures into a local SQLite database.
5. Generates and downloads self-contained HTML audit reports.

The application is **fully offline** after installation. No external CDN assets are required.

> **Important:** This tool is designed for authorized testing only - run it against your own lab AP with explicit permission. Deauthentication can disrupt networks.

---

## 2. Architecture Diagram

```
                         +------------------------------------------------------+
                         |                     BROWSER (Client)                  |
                         |   Dashboard | Scanner | Capture | Reports             |
                         +--------------------------+---------------------------+
                                                    |  HTTP (JSON / HTML)
                         +--------------------------v---------------------------+
                         |                   FLASK WEB SERVER                   |
                         |   app.py  (routes, session, REST API)                |
                         |                                                      |
                         |  +-------------+   +-----------------------------+    |
                         |  | capture/     |   | reports/                    |    |
                         |  |  scanner     |   |  generator.py               |    |
                         |  |  handshake   |-->|  templates/report.html      |    |
                         |  |  deauth      |   +-----------------------------+    |
                         |  |  analyzer    |                                     |
                         |  +-------------+                                       |
                         +---------------------+--------------+------------------+
                                               |              |
                         +---------------------v------+       v-------------------------+
                         |   SQLITE (settings.db)     |    |   FILESYSTEM (captures/)    |
                         |   tables: networks,         |    |   .cap files, report .html  |
                         |   sessions, reports         |    +-----------------------------+
                         +----------------------------+
```

---

## 3. Components

### 3.1 Frontend Layer (templates/ + static/)

| File | Purpose |
|------|---------|
| `templates/base.html` | Shared layout: sidebar, topbar, page shell |
| `templates/index.html` | Dashboard - statistics, live status, recent sessions |
| `templates/scanner.html` | Network discovery table with signal bars |
| `templates/capture.html` | Handshake capture console for selected target |
| `templates/reports.html` | Report index list with HTML download |
| `templates/report_view.html` | Rendered report preview page |
| `static/css/style.css` | All styling (dark cybersecurity theme, no CDN) |
| `static/js/app.js` | API client, polling, dynamic DOM updates |

**Design principles**
- Dark theme with green/teal accent (audit console aesthetic).
- Mobile responsive (sidebar collapses).
- No external fonts/icons; inline SVG icons keep it usable offline.

### 3.2 Backend API Layer (app.py)

Flask exposes both HTML routes and a JSON REST API:

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Dashboard page |
| GET | `/scanner` | Scanner page |
| POST | `/api/scan` | Run a scan (simulated or live) |
| GET | `/api/networks` | List discovered networks |
| GET | `/capture` | Capture page |
| POST | `/api/capture/start` | Begin handshake capture on a target |
| POST | `/api/capture/stop` | Stop current capture |
| GET | `/api/capture/status` | Poll capture progress |
| POST | `/api/deauth` | Trigger deauth burst |
| GET | `/reports` | Reports index page |
| GET | `/api/reports` | JSON list of reports |
| GET | `/reports/<id>/html` | Full HTML report (target for download) |
| GET | `/api/reports/<id>/download` | Forced-download `.html` attachment |
| POST | `/api/reports/<id>/delete` | Delete a report |
| GET | `/api/system` | Engine mode, adapter status, uptime |

### 3.3 Capture Engine Layer (capture/)

`capture/scanner.py`
- `scan()` → returns list of AP records (SSID, BSSID, channel, signal, encryption, probes, handshake flag).
- **Simulation mode (default):** generates deterministic, realistic lab data so the UI/flow is fully demonstrable on any machine (Windows/Mac/Linux without a monitor-mode adapter).
- **Live mode (`AUDITOR_ENGINE=live`):** executes `airodump-ng` for real scanning on Linux, parses its CSV output.

`capture/handshake.py`
- `start_capture(ssid, bssid, channel, deauth)` → spawns capture thread.
- Uses EAPOL state machine: `IDLE → LISTENING → EAPOL_DETECTED → HANDSHAKE_COMPLETE`.
- **Simulation mode:** state advances on a timer with realistic packet counts.
- **Live mode:** monitors `airodump-ng` output file for EAPOL traffic (mesg 1-4) and writes `.cap` file to `captures/`.

`capture/deauth.py`
- `send_deauth(bssid, count)` → simulated or real `aireplay-ng --deauth`.
- Deauth bursts accelerate handshake acquisition.

`capture/analyzer.py`
- Computes security score, packet integrity, and recommendation text from capture metadata.
- Feed the report generator.

### 3.4 Data Layer (database/)

`database/db.py` - thin SQLite wrapper (stdlib `sqlite3`, no ORM dependency).

| Table | Columns | Purpose |
|-------|---------|---------|
| `networks` | id, ssid, bssid, channel, signal_dbm, encryption, clients, seed | Discovered APs (lifetime record) |
| `sessions` | id, ssid, bssid, channel, started_at, ended_at, duration_s, packets, eapol_messages, status, deauth_used, engine | One row per capture attempt |
| `reports` | id, session_id, ssid, bssid, title, generated_at, score, file_name | Generated HTML reports |

### 3.5 Report Layer (reports/)

`reports/generator.py`
- `build_report(session_id) → dict` gathers session + metadata.
- `render_report_html(report_data) → str` renders standalone, self-contained HTML (inline CSS, no external refs).
- Writes file to `reports/out/<name>.html` and registers it in the `reports` table.

---

## 4. Data Flow

### Scan flow
```
UI "Scan Networks"  → POST /api/scan → scanner.scan()
                    → networks stored in DB → GET /api/networks
                    → scanner.html table rendered
```

### Capture flow
```
UI "Start Capture"  → POST /api/capture/start   {ssid,bssid,channel,deauth}
                    → handshake.start_capture()  (background thread)
                    → POST /api/deauth (optional, repeated)
                    → GET /api/capture/status  ← every 1s (UI polling)
                    → on HANDSHAKE_COMPLETE → session saved to DB
                    → report_prompt shown → build report
```

### Report flow
```
UI "Generate Report / Download" → POST /api/reports/generate{session_id}
                               → reports/generator.build_report()
                               → GET /reports/<id>/html   (preview)
                               → GET /api/reports/<id>/download (attachment)
```

---

## 5. State Management

See `state.md` for the full state machine.

Core capture states:

```
                 +----------+
                 |  IDLE    |<------------------+
                 +-----+----+                    |
                       | start capture          |
                       v                         |
                 +----------+                   |
                 | LISTENING|                   |
                 +-----+----+                   |
                       | EAPOL msg1 seen        |
                       v                         |
                 +--------------+                |
                 | EAPOL_DETECT |                |
                 +-----+--------+                |
                       | msg2-4 complete        |
                       v                         |
                 +-----------------+             |
                 | HANDSHAKE_COMPl |-------------> stop/reset
                 +-----------------+
```

Application-level memory and caches are described in `memory.md`.

---

## 6. Security Considerations

- **Authorized lab use only.** The report header and UI include an educational-purpose banner.
- No passwords, keys, or capture payloads are ever stored - only EAPOL metadata (message counts, hashes of identities).
- The web server binds to `127.0.0.1` by default (`AUDITOR_HOST`).
- All writes stay inside the project directory; report download uses `send_file` with `as_attachment`.
- Simulated mode is safe to run anywhere; never point live mode at networks you do not own.

---

## 7. Engine Modes

| Mode | `AUDITOR_ENGINE` | Platform | Behavior |
|------|------------------|----------|----------|
| Simulation | `simulation` | Any | Generates realistic lab data + timed handshake simulation. No adapter required. |
| Live | `live` | Windows + Npcap | Real scan via `netsh wlan show networks`; capture is a Scapy EAPOL (`0x888e`) passive sniff on the selected Wi-Fi adapter; sockets `.cap` written to `captures/`. No monitor mode required for the connected AP. |
| Live | `live` | Linux + libpcap | Real scan via `airodump-ng` (CSV parse) or Scapy beacon/probe sniff; capture via Scapy EAPOL sniff or `airodump-ng`; `aireplay-ng --deauth` for injection. |

Live capture interface discovery, Npcap/libpcap detection and selection are
exposed through `/api/system`, `/api/system/interfaces` and
`/api/system/iface`, and surfaced in the Scanner/Capture pages. If no live
backend is available the API returns a clear JSON error instead of a 500.

The active engine is exported via `/api/system` and shown as a badge in the UI.

---

## 8. Configuration

Environment variables read by `config.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUDITOR_HOST` | `127.0.0.1` | Bind address |
| `AUDITOR_PORT` | `5001` | Bind port |
| `AUDITOR_ENGINE` | `simulation` | Engine mode |
| `AUDITOR_IFACE` | `wlan0` | Wireless interface (live mode) |
| `AUDITOR_DB` | `database/settings.db` | SQLite path |
| `AUDITOR_CAPTURE_DIR` | `captures` | Capture file directory |
| `AUDITOR_OUT_DIR` | `reports/out` | Generated report directory |