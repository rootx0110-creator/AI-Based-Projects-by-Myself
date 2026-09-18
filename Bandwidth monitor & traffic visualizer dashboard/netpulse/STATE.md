# NetPulse — Project State

![version](https://img.shields.io/badge/version-1.0.0-blue) ![status](https://img.shields.io/badge/status-beta-orange) ![python](https://img.shields.io/badge/python-3.11%20%7C%203.12-informational) ![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)

## Implemented features

- [x] Live per-interface up/down throughput (psutil, 100 ms–1 s configurable)
- [x] Global aggregate across interfaces
- [x] PDH fallback for frozen counters; WMI/registry link-speed lookup
- [x] Per-process breakdown (connections → PID → name), top-25 table
- [x] Connection drill-down (remote IP:port, state)
- [x] 60 s rolling line graph, 10 FPS redraw cap
- [x] Animated gauge vs. link capacity
- [x] Sparkline cards, top-process donut, 24-hour heatmap
- [x] SQLite storage (samples, process_samples, rollups, quotas) with batched writes + WAL
- [x] Hour/day/month rollups; 24 h heatmap query
- [x] Top talkers over range
- [x] Quota tracking (daily/monthly) with 80/95/100% alerts
- [x] Sustained-speed alerts; watched-process new-connection alerts
- [x] Toasts + tray balloon notifications
- [x] Tabs: Dashboard · Processes · Interfaces · History · Settings
- [x] Dark/light theme
- [x] System tray (mini-speed tooltip, menu, balloon)
- [x] Floating always-on-top HUD (draggable)
- [x] CSV/JSON export (+ PNG grab helper)
- [x] Config persistence in `%APPDATA%/NetPulse/config.json`
- [x] Single-instance lock (stale-lock recovery)
- [x] Graceful shutdown (flush DB, join threads, release lock)
- [x] Demo mode (`--demo`) + 7-day DB seeder script
- [x] PyInstaller build (onefile, windowed, icon) via build.bat/build.spec
- [ ] Stacked per-interface area chart (currently single-series selection) — v1.1
- [ ] Process icons in tables — v1.1
- [ ] Scapy protocol donut — v1.2

## Known issues / limitations

- **Admin rights**: `psutil.net_connections` may return fewer rows without
  elevation on some Windows builds; per-process rates are share-based
  approximations, not byte-exact attribution (Windows lacks a cheap
  per-PID network byte counter without ETW).
- **VPN interfaces**: some adapters report zero via psutil; PDH rescue
  covers the common cases (OpenVPN/WireGuard) but not all.
- **IPv6**: counter aggregation includes IPv6, but the connection list
  filters to `kind="inet"` (v4-mapped v6 shows truncated addresses).
- **Loopback**: loopback pseudo-interface traffic is excluded; app-local
  traffic is therefore counted once (not twice).
- **Link capacity** on some USB/VPN adapters is unknown (gauge falls back
  to a 1 Gbps dial maximum).
- **HUD position** persists only for the session (not saved to config yet).

## Roadmap

- **v1.1** — stacked per-interface area chart, process icons, HUD position
  persistence, per-interface exclusions UI, PNG chart-snapshot buttons
- **v1.2** — scapy-backed protocol attribution, per-host top talkers,
  speed-test integration, DB auto-prune policy in Settings
- **v1.3** — Windows PDH/ETW per-process byte counters (elevated mode),
  multiple simultaneous quotas, alert log view

## Test coverage summary

| Suite | Focus | Status |
|---|---|---|
| `tests/test_sampler.py` | ring buffer semantics, Sample math, loopback filter | ✅ |
| `tests/test_process_mapper.py` | conn formatting, share scaling, top-N | ✅ |
| `tests/test_rollups.py` | bucket boundaries, aggregation, heatmap | ✅ |
| `tests/test_quota.py` | levels, dedupe, windows | ✅ |

GUI code is exercised manually / via `--demo` (Qt widget tests are planned
for v1.1 with `pytest-qt`).

## Changelog

### [1.0.0] — 2026-09-12
- Initial release: live dashboard, per-process view, interfaces, history,
  settings, tray + HUD, alerts, SQLite analytics, PyInstaller build.
- Added demo mode and demo DB seeder.

### [0.9.0] — 2026-09-10 (internal)
- Capture pipeline, ring buffers, scheduler wiring.
- Dark theme QSS + custom gauge/donut/heatmap widgets.

### [0.8.0] — 2026-09-08 (internal)
- Project scaffold, config module, DB schema + migrations.

## Environment matrix

| | Win10 22H2 | Win11 23H2+ |
|---|---|---|
| Python 3.11, non-admin | ✅ | ✅ |
| Python 3.11, admin | ✅ (full conn list) | ✅ (full conn list) |
| Python 3.12, non-admin | ✅ | ✅ |
| PyInstaller onefile exe | ✅ | ✅ |
| Wi-Fi only | ✅ | ✅ |
| VPN (WireGuard/OpenVPN) | ✅ (PDH fallback may engage) | ✅ (PDH fallback may engage) |
