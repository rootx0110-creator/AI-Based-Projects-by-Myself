# NetPulse — Project Memory

Conventions, decisions, constants, glossary and gotchas for anyone (human or
AI) picking up this codebase.

## Conventions

- **Naming**: modules `snake_case.py`; classes `PascalCase`; constants
  `UPPER_SNAKE`; private attrs `_leading_underscore`.
- **Imports**: absolute from `src/` root (`from capture.ring_buffer import ...`).
  `src/main.py` and `tests/conftest.py` insert `src/` into `sys.path`.
- **Docstrings**: every module/class/function (one line minimum).
- **Type hints**: on all public functions.
- **Log levels**: `DEBUG` per-tick diagnostics · `INFO` lifecycle events
  (start/stop/build) · `WARNING` degraded behavior (access denied, PDH
  rescue) · `ERROR` failed operations with context · `CRITICAL` unused.
- **Error codes / exit codes**: 0 ok · 1 single-instance conflict ·
  2 database open failure.
- **Qt style**: signals connect via `bridge.*`; no business logic in
  `paintEvent` beyond drawing.

## Design decisions (ADR-style)

### ADR-001: psutil over scapy for default capture
- **Context**: we need per-interface byte counters, cheaply, every 500 ms.
- **Decision**: poll `psutil.net_io_counters(pernic=True, nowrap=True)`;
  keep scapy behind an optional `Sniffer`.
- **Why**: psutil reads OS counters with zero elevation and <1 ms cost;
  scapy needs Npcap + admin and burns CPU on every packet. Counter *diffing*
  gives identical throughput numbers for the dashboard.

### ADR-002: SQLite over Parquet for v1
- **Context**: history analytics (range sums, rollups, top talkers) with
  concurrent writes from the sampler and reads from the GUI.
- **Decision**: single-file SQLite in WAL mode with a batched writer queue.
- **Why**: indexed range queries (ts, iface) are exactly our access pattern;
  Parquet has no update/append ergonomics for 10-second flushes and would
  need extra machinery (arrow/duckdb) for queries. SQLite ships in stdlib.

### ADR-003: pyqtgraph over matplotlib for live plots
- **Context**: 60 s rolling graph updating at up to 10 FPS.
- **Decision**: `pyqtgraph.PlotWidget` for live charts; QPainter for tiny
  custom widgets (sparkline, gauge, donut, heatmap).
- **Why**: matplotlib redraws are slow (~100 ms) and pull in a huge dep;
  pyqtgraph is Qt-native, renders in <5 ms and supports fill-under-curve
  out of the box.

### ADR-004: share-based per-process attribution
- **Context**: Windows exposes no cheap per-PID *network* byte counter
  (ETW is expensive; `Process.IO counters` are disk+pipe).
- **Decision**: attribute total interface rate to processes proportionally
  to their established-connection count; clearly documented as an estimate.
- **Why**: zero-dependency, stable, good-enough ranking for "who is
  talking"; byte-exact attribution is a v1.3 ETW feature.

### ADR-005: Qt signals as the only GUI channel
- **Context**: three worker threads must update widgets safely.
- **Decision**: workers never touch widgets; they emit `bridge.*` Qt
  signals (auto-queued to the GUI thread) or call plain callbacks that emit.
- **Why**: eliminates a whole class of race conditions/crashes.

## Key constants

| Constant | Value | Where |
|---|---|---|
| Sample interval | 500 ms (100–1000) | `config.DEFAULTS` |
| Process scan interval | 2000 ms | `config.DEFAULTS` |
| Ring buffer capacity | 8192 points/series | `StatsStore` |
| Live window | 60 s | `config.DEFAULTS` |
| Redraw cap | 10 FPS (100 ms) | `LiveGraph` |
| DB flush | 10 s | `config.DEFAULTS` |
| Rollup refresh | 5 min | `core/scheduler.ROLLUP_PERIOD_SECONDS` |
| Quota warn levels | 0.8 / 0.95 / 1.0 | `config.DEFAULTS` |
| Speed alert default | 50 Mbps sustained 10 s | `config.DEFAULTS` |
| Log rotate | 2 MB × 3 | `core/logger.py` |

## Dependencies + rationale

| Package | Why | Runtime? |
|---|---|---|
| PySide6 | Qt 6 GUI (LGPL, official bindings) | yes |
| pyqtgraph | fast live plotting on Qt | yes |
| psutil | counters, connections, processes, PID liveness | yes |
| numpy | ring buffers, vectorized conversions | yes |
| Pillow | asset generation (icon) | build only |
| pyinstaller | packaging to onefile exe | build only |
| scapy | optional deep capture | optional |
| wmi / pywin32 | link speed & PDH fallbacks (graceful without) | optional |

## Glossary

- **Interface** — a network adapter (Ethernet, Wi-Fi, VPN tunnel) as named by Windows.
- **Sample** — one per-interface throughput measurement (bytes/sec over the last tick).
- **Rollup** — pre-aggregated traffic bucket (hour/day/month) with peak rates.
- **Top talker** — process ranked by total bytes over a time range.
- **Quota** — a byte limit per daily/monthly window with warn levels.
- **HUD** — floating always-on-top mini speed widget.

## Onboarding notes

1. Read `ARCHITECTURE.md` (15 min) — threading model is the critical part.
2. Run `python src/main.py --demo --debug` before touching capture code.
3. Tests: `pytest tests/ -q` (no Qt needed; conftest adds `src/` to path).
4. GUI changes: hot-reload by relaunching; QSS lives in `gui/theme.py`.
5. DB changes: append a migration in `storage/migrations.py` — never edit
   `SCHEMA` destructively (existing user DBs).

## Gotchas

- **psutil per-process**: `net_connections` needs admin on some builds to
  see other users' PIDs; `Process.io_counters` is *disk* IO, not network.
- **Loopback double counting**: Windows counts app-local traffic on the
  loopback pseudo-interface; we exclude it by name (`_is_loopback`).
- **VPN adapters**: some (older OpenVPN) never bump psutil counters — the
  PDH rescue in `interface_sampler` exists for exactly this; keep it.
- **pyqtgraph/OpenGL**: on some remote-desktop sessions hardware
  acceleration glitches; we deliberately do *not* enable `useOpenGL`.
- **nowrap=True**: pass it to `net_io_counters` or 32-bit counters wrap on
  long uptimes and produce negative deltas (we clamp at 0 anyway).
- **MSYS/Windows paths**: PyInstaller spec uses `src\\main.py`; keep the
  backslash for the Windows bootloader.
- **Qt + threads**: creating *any* QWidget off the main thread aborts the
  process — route through `bridge` signals only.
- **Tray icon timing**: `QSystemTrayIcon` created before `QApplication`
  crashes; the tray is constructed inside `MainWindow.__init__` for that
  reason.
