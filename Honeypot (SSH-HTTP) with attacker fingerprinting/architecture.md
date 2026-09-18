# Honeypot (SSH-HTTP) with Attacker Fingerprinting — Architecture

## Overview

This system is a fully self-contained honeypot application that exposes two deceptive
services (SSH on TCP port 2222 and HTTP on TCP port 8080) to lure attackers, capture
their activity, and build a behavioral fingerprint of each offender. All intelligence is
stored locally and surfaced through a modern web dashboard with HTML report export.

```
                Internet / Network Segment
                          |
                          v
        +-----------------------------------------+
        |               HONEYPOT HOST             |
        |                                         |
   TCP:2222                                      TCP:8080
        |                                         |
        v                                         v
+------------------+                +-----------------------+
|  SSH Honeypot    |                |   HTTP Honeypot       |
|  (paramiko)      |                |   (raw socket)        |
|  - realistic     |                |   - fake web portal   |
|    OpenSSH server|                |   - trap files        |
|  - username/     |                |   - fake credentials  |
|    password auth |                |   - logging of full   |
|  - emulated      |                |     request headers   |
|    shell + files |                |   - 404 trap pages    |
+--------+---------+                +-----------+-----------+
         |                                      |
         |  events (auth attempts, commands,    |
         |        headers, user agents)         |
         v                                      v
+-------------------------------------------------------+
|              EVENT COLLECTOR / PIPELINE               |
|  - classify_event()  -> risk deltas                  |
|  - AttackerFingerprint.analyze()                     |
|       - tool detection (nmap, hydra, sqlmap, ...)    |
|       - user-agent heuristics                        |
|       - SSH client banner analysis                   |
|       - HTTP header analysis                         |
|       - behavioral risk scoring (0-100)              |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|                 SQLite PERSISTENCE                    |
|  tables: attackers, events, http_requests,           |
|          ssh_sessions, threat_intel                   |
|  - fingerprint_hash (sha256, unique per attacker)    |
|  - rolling risk_score per fingerprint                |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|              FLASK CONTROL PLANE (port 5001)          |
|  /                      -> dashboard UI              |
|  /api/status            -> honeypot service state     |
|  /api/start | /api/stop -> control services          |
|  /api/dashboard         -> aggregated stats           |
|  /api/events            -> live event stream          |
|  /api/attackers         -> fingerprinted attackers    |
|  /api/top/usernames     -> credential analysis        |
|  /api/top/passwords     -> credential analysis        |
|  /api/report/html       -> styled HTML report (DL)    |
|  /api/report/json       -> machine-readable export    |
+-------------------------------------------------------+
```

## Components

| Component | File | Responsibility |
|---|---|---|
| SSH honeypot | `honeypot/ssh_honeypot.py` | Accepts SSH connections, emulates authentication and a dummy Linux shell, logs every auth attempt and command |
| HTTP honeypot | `honeypot/http_honeypot.py` | Raw-socket HTTP server that mimics a corporate site, serves trap files and logs full request metadata |
| Fingerprinting | `honeypot/fingerprint.py` | Behavioral analysis engine: tool detection, header/UA heuristics, risk scoring, classifications |
| Persistence | `honeypot/database.py` | SQLite schema, all queries, stats aggregation, attacker upsert logic |
| Reporting | `honeypot/report.py` | Generates the styled HTML intelligence report and JSON export |
| Control plane | `app.py` | Flask application: dashboard, REST API, service start/stop |
| UI | `templates/index.html`, `static/` | Dashboard front end (vanilla JS, canvas charts, no CDN dependencies) |

## Data Flow

1. An attacker connects to TCP 2222 or TCP 8080.
2. The honeypot service parses the connection (HTTP request line + headers, or SSH
   transport + auth challenge) and emits a structured event dict.
3. `handle_event()` in `app.py` runs `AttackerFingerprint.analyze()` plus
   `classify_event()` to produce a risk delta and tool-tag list.
4. The opaque `fingerprint_hash` (sha256 over source IP + user agent + headers + SSH
   banner) is upserted into `attackers`; the event is inserted into `events` with the
   hash link.
5. The front end polls the REST API every 3 seconds and redraws charts/tables.

## Security & Ethics

- This tool is intended for defensive security research, network monitoring, and
  security education on networks you own or in sandbox/lab environments.
- All captured data stays local in `honeypot.db`; nothing is transmitted externally.
- The dummy shells and trap files contain fake credentials designed to keep attackers
  engaged long enough to fingerprint them — never place real credentials in trap files.
- Do not deploy against production services you do not control.

## Ports

| Port | Service | Purpose |
|---|---|---|
| 2222 | SSH honeypot | Fake OpenSSH (avoid conflict with real sshd on 22) |
| 8080 | HTTP honeypot | Fake corporate portal |
| 5001 | Flask dashboard | Administrative UI / REST API |

All are configurable by editing `app.py` constants or `server_state` dict.

## Dependencies

Python 3.9+ with `flask`, `paramiko`. Everything else is standard library. See
`requirements.txt`.