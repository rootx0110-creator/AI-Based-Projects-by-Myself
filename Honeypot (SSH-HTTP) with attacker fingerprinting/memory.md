# Memory

This file records operational memory for this project: how to run it, known behavior,
common issues, and maintenance notes.

## How to Run

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5001> in a browser.

The honeypot listeners will **not** start automatically — press **Start Honeypots** in
the dashboard (or POST `/api/start`). This is intentional so you control when the bait
is live.

## What the App Remembers

| Item | Where | Purpose |
|---|---|---|
| Every attacker fingerprint | `attackers` table | causal identity, risk score, attack count |
| Every event (auth, command, probe) | `events` table | full audit trail per source IP |
| HTTP request payloads | `http_requests` table | headers/body of every probe |
| SSH session command lists | `ssh_sessions` table | what commands attackers ran in the fake shell |
| Tool identifications | `threat_intel` table | known tool families per fingerprint |

## Fingerprinting Heuristics (current implementation)

- **Tool detection** via signature list in `fingerprint.py`: `nmap`, `masscan`,
  `gobuster`, `nikto`, `sqlmap`, `hydra`, `medusa`, `curl`, `python-requests`,
  `metasploit`, `cobaltStrike`, `mirai`, `cowrie`.
- **Risk weighting**: tool match (+15 each, up to +35 for worm families),
  suspicious headers (+8 each), no-UA (+10), known aggressive paths (+15),
  common usernames like `root`/`admin` (+10), short passwords (+5).
- **Classification**: 0–24 UNKNOWN/LOW · 25–49 MEDIUM · 50–69 HIGH · 70+ CRITICAL.

## Traps & Decoys (fake content served)

- SSH shell emulates Ubuntu 22.04. Dummy files: `/etc/passwd`, `/root/credentials.txt`,
  `.bash_history`. Fake passwords in `<script type="application/json">credentials.txt`:
  `admin:SuperSecret2024!`, `root:h4ckedPassw0rd`, `db_admin:dbPass12345`.
- HTTP trap endpoints: `/login` (fake login form), `/admin` (302), `.env`/`.git`
  (fake DB credentials), `*.zip/*.tar` (fake backup), everything else 404 portal.

## Known Limitations

1. SSH key exchange uses a freshly generated RSA key on each start — sessions persist
   within one run but transported keys are not persisted.
2. GeoIP columns exist in the schema but are **not** currently populated (no GeoIP DB
   bundled by default). Add `geoip2` data files and an enrichment hook in
   `handle_event()` to fill them.
3. HTTP honeypot is plain HTTP only (no TLS) — expect `/something` probes, not https.
4. `events` table is unbounded; for long-running deployments add a retention/trim
   job (e.g. delete events older than 90 days) to keep `honeypot.db` small.
5. Fake shell is a syntax-level emulator, not a real PTY — sophisticated attackers will
   notice. Good enough for fingerprinting bots/credential-stuffing.

## Maintenance Notes

- `honeypot.db` is created next to `app.py` on first run. Delete it to start fresh.
- `reports/` directory is reserved for future scheduled report exports.
- Logging goes to the console (INFO level); set
  `logging.basicConfig(level=logging.DEBUG)` for more verbose listener output.
- Ports 2222/8080/5001 must be free. Change them in `app.py` / `server_state` if busy.
- WAL mode is on; you can safely copy `honeypot.db` while the app runs (copy
  `honeypot.db` + `-wal` + `-shm` together for consistency).

## Roadmap Ideas

- Add GeoIP enrichment with MaxMind GeoLite2.
- Add OS detection from SSH banners / TCP fingerprints.
- Add per-fingerprint session replay (see the exact commands run).
- Add automated blocking rules export (iptables / Firewall rules from top IPs).
- Scheduled daily HTML report generation into `reports/`.
- Optional pushing of incidents to Slack/Telegram webhooks.