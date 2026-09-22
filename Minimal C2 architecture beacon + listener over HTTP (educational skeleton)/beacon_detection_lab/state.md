# State.md — Beacon Detection Lab

Last updated: 2026-09-19

## Current state

**Phase:** v1.0 complete and verified.

**What exists:**

| Component | Status | Notes |
|---|---|---|
| `analyzer.py` | ✅ done | log + pcap parsers, scoring engine, HTML report, CLI |
| `dashboard.py` | ✅ done | loopback web UI, upload, HTML/JSON report download |
| `make_sample_data.py` | ✅ done | synthetic benign + beacon-like log & pcap |
| `detections/` rules | ✅ done | 2 Sigma rules, 1 YARA rule (educational) |
| `architecture.md` | ✅ done | design, data flow, scoring model |
| `launcher.py` + `build.bat` | ✅ done | windowed exe entry point + PyInstaller rebuild script |
| `dist/BeaconDetectionLab.exe` | ✅ built & tested | dashboard exe: GET / 200, POST /analyze 200, /report HTML+JSON 200 |
| `dist/beacon-analyzer.exe` | ✅ built & tested | CLI exe: log 100/100 HIGH, pcap 90/100 HIGH |
| `readme.txt`, `todo.txt`, `memory.md` | ✅ done | project docs |

## Verified behavior (this session)

- `python make_sample_data.py` → `samples/access.log` (~460 lines),
  `samples/capture.pcap` (~30 KB)
- CLI: beacon at **100/100 high** (log, 203.0.113.66 → /wp-content/cache/refresh.php,
  60s interval) and **90/100 high** (pcap, 10.0.0.50 → 93.184.216.34:80, 30s interval);
  benign hosts stay low or absent.
- Dashboard: `POST /analyze` returns results table; `/report?id=1` downloads
  `access_beacon_report.html`; `&format=json` returns findings JSON.
- All modules compile under Python 3.14, stdlib only.

## Known limitations

- `dist/` exes are Windows builds; rebuild with `build.bat` after code changes
  (PyInstaller, ~9 MB each, onefile; first launch may be slow while unpacking).
- PCAP parser: Ethernet/IPv4/HTTP only, no stream reassembly, no pcapng, no IPv6.
- Report store is in-memory — dashboard restart clears generated reports.
- HTTPS content is invisible to the log/pcap parsers unless terminated at a proxy.

## Next candidate steps

See `todo.txt`.
