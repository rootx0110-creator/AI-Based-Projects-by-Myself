# NetPulse — Architecture

## High-level data flow

```
┌─────────────────────────────  WORKER THREADS  ─────────────────────────────┐
│                                                                            │
│  ┌───────────────────┐   ┌───────────────────┐   ┌──────────────────────┐  │
│  │ InterfaceSampler  │   │  ProcessMapper    │   │  Rollup/Quota timer  │  │
│  │ (psutil, 500ms)   │   │  (2s scan)        │   │  (5 min)             │  │
│  └────────┬──────────┘   └────────┬──────────┘   └──────────┬───────────┘  │
│           │ Sample                 │ {pid: ProcessInfo}      │              │
│           ▼                        ▼                         ▼              │
│  ┌─────────────────────────────────────────┐      ┌─────────────────────┐  │
│  │        StatsStore (ring buffer)         │      │  SQLite (batched)   │  │
│  └───────────────────┬─────────────────────┘      └──────────▲──────────┘  │
│                      │ callback                              │ flush 10s   │
└──────────────────────┼───────────────────────────────────────┼─────────────┘
                       │ Qt Signal (queued, thread-marshalled)
                       ▼
┌─────────────────────────────  GUI MAIN THREAD  ────────────────────────────┐
│  EventBridge ──► MainWindow                                                │
│                    ├─ DashboardTab (gauge · live graph · sparks · donut)   │
│                    ├─ ProcessesTab (table + drill-down)                    │
│                    ├─ InterfacesTab (stacked chart + adapters)             │
│                    ├─ HistoryTab  (rollups · top talkers · export)         │
│                    ├─ SettingsTab (config UI)                              │
│                    ├─ HudWidget (floating)  ├─ TrayIcon (tooltip/balloon)  │
│                    └─ ToastManager (alerts)                                │
└────────────────────────────────────────────────────────────────────────────┘
```

## Component responsibilities

| Component | Responsibility | Thread |
|---|---|---|
| `capture/interface_sampler.py` | Poll `psutil.net_io_counters`, diff → bytes/sec, PDH rescue for frozen counters | sampler thread |
| `capture/process_mapper.py` | `net_connections` → PID → process, new-connection detection, share-based rate attribution | mapper thread |
| `capture/ring_buffer.py` | Fixed-capacity numpy time series (no unbounded growth) | any |
| `capture/sniffer.py` | Optional scapy capture (protocol/host counters), fails soft | sniffer thread |
| `storage/database.py` | SQLite schema, WAL, queue + writer thread batching INSERTs | db-writer thread |
| `storage/migrations.py` | Forward-only schema migrations via `schema_version` | startup |
| `storage/exporter.py` | CSV/JSON/PNG export | GUI thread |
| `analytics/rollups.py` | Hour/day/month bucketing, peak rates, heatmap query | rollup timer / GUI |
| `analytics/quota.py` | Quota windows, level classification, alert dedupe | rollup timer |
| `analytics/top_talkers.py` | Ranked process totals over a range | GUI |
| `core/scheduler.py` | Wires capture→store→DB→bridge; flush orchestration | own + workers |
| `core/alerts.py` | Sustained-speed rule, watched-process rule | caller thread |
| `core/events.py` | Qt-signal bridge (only thread-safe channel to GUI) | any → main |
| `core/stats.py` | Latest snapshot + ring buffers for GUI reads | any |
| `gui/*` | Widgets/tabs; never call psutil directly | main |

## Threading model

| Thread | Started by | Loop | Exit |
|---|---|---|---|
| Qt main | `QApplication` | event loop | `app.exec()` returns |
| `sampler` | `InterfaceSampler.start()` | sample → callback → sleep | `stop()` Event |
| `process-mapper` | `ProcessMapper.start()` | scan → callback → sleep | `stop()` Event |
| `db-writer` | `Database.open()` | drain queue every 10 s | `close()` flush+join |
| `rollups` | `Scheduler.start()` | refresh hour rollup + quota every 5 min | `stop()` Event |
| `db-flush` | `schedule_db_flush()` | `flush_pending()` every N s | `Timer.cancel()` |

Rules:

1. **No Qt calls off the main thread.** Workers communicate only via
   `bridge.*` Qt signals (queued connections marshal to the GUI thread) or
   callback functions invoked on the worker thread.
2. **Shared mutable state** (`StatsStore`, ring buffers, pending DB batch)
   is guarded by locks; readers copy under lock.
3. **DB writes** only from the `db-writer` thread (single owner) except
   synchronous rollup upserts, serialized by SQLite + WAL.

## Data flows

### Interface sample
`sampler tick` → diff `net_io_counters` per interface → `Sample(per_iface, totals)`
→ `StatsStore.push_sample` (ring buffers) → `AlertEngine.check_speed`
→ `bridge.sample_ready.emit(sample)` → GUI: gauge/graph/sparks/tray tooltip.
Accumulated bytes are added to `Scheduler._pending_bytes`; every
`db_flush_seconds` they are enqueued as `SampleRow`s and INSERT-batched.

### Per-process mapping
`mapper tick (2s)` → `net_connections(kind="inet")` → group by PID → detect
new remotes vs previous snapshot → provisional share = conns/total_conns
→ scaled by latest total interface rate → `bridge.processes_ready.emit`.
Watched processes feed `AlertEngine.check_processes` → new-connection alerts.

### Quota alert
`rollup timer (5 min)` → `totals_for_range(window_start, now)` →
`QuotaTracker.evaluate(used)` → level crossing (80/95/100%) fires once per
window → `bridge.quota_alert` → toast + tray balloon.

## Storage schema (SQLite, WAL)

```sql
samples(id PK, ts INTEGER /*unix ms*/, iface TEXT, bytes_sent INTEGER,
        bytes_recv INTEGER, pkts_sent INTEGER DEFAULT 0, pkts_recv INTEGER DEFAULT 0)
  idx_samples_ts(ts) · idx_samples_iface_ts(iface, ts)

process_samples(id PK, ts INTEGER, pid INTEGER, process_name TEXT,
                bytes_sent INTEGER, bytes_recv INTEGER)
  idx_process_samples_ts(ts)

rollups(bucket_ts INTEGER, granularity TEXT /*hour|day|month*/, bytes_sent,
        bytes_recv, peak_down_bps, peak_up_bps, PK(bucket_ts, granularity))

quotas(id PK, name, period /*daily|monthly*/, limit_bytes, current_bytes, last_reset)
schema_version(version) -- migration bookkeeping
```

## Performance budget

| Metric | Budget | Mechanism |
|---|---|---|
| CPU steady-state | < 2% | 500 ms counter diff (O(#ifaces)); 2 s process scan; 10 FPS redraw cap |
| RAM | < 150 MB | ring buffers capped at 8192 points × float64; deque maxlen; PySide6 baseline |
| Disk | ~1.4 MB/day | batched writes; 30-day purge button |
| First paint | < 1.5 s | no blocking work on GUI thread; DB opened async-writer style |

## Extension points

- **New metric source** (SNMP, WMI-only, remote host): implement
  `sample_once() -> Sample`-shaped object and call `StatsStore.push_sample`;
  the GUI reads via the bridge, so nothing else changes.
- **New chart type**: drop a widget in `gui/widgets/`, feed it from
  `bridge.sample_ready` / `bridge.processes_ready` or a `Database` query.
- **New alert rule**: add a `check_*` method on `AlertEngine`, call it from
  `Scheduler._on_sample/_on_processes`, emit a dedicated bridge signal.
- **Deeper capture**: enable `capture/sniffer.py` (scapy + Npcap) for
  protocol/host attribution; its counters can populate the donut.

## Build & packaging pipeline

```
build.bat
  ├─ python -m venv .venv
  ├─ pip install -r requirements.txt      (PySide6, pyqtgraph, psutil, numpy, Pillow, pyinstaller)
  ├─ python scripts/generate_assets.py    (icon.ico, logo.png — reproducible, Pillow-drawn)
  └─ pyinstaller build.spec
        ├─ Analysis(src/main.py, pathex=src)
        ├─ datas: assets/ → assets/
        ├─ hiddenimports: psutil, pyqtgraph, numpy
        ├─ excludes: tkinter, matplotlib, scapy, wmi, win32pdh
        └─ EXE(onefile, console=False, icon=assets/icon.ico)
  ⇒ dist/NetPulse.exe
```

`runtime_tmpdir=None` + `console=False` gives a single windowed EXE; the
manifest optionally requests elevation for full per-process stats.
