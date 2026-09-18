# Architecture — LBSimulator

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GUI (PyQt6) — Main Thread                    │
│  ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐ │
│  │Dashboard│Backends│Algorithm│ Health  │Traffic │ Logs   │Settings│ │
│  └────────┴────────┴────────┴────────┴────────┴────────┴────────┘ │
│                            ▲                                         │
│                     SignalBridge (Qt signal)                         │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ async / thread boundary
┌─────────────────────────────┼───────────────────────────────────────┐
│                   Asyncio Worker Thread (qasync)                    │
│                                                                     │
│  ┌─────────────────────────▼─────────────────────────────────────┐  │
│  │                     Event Bus                                       │  │
│  │  lb.request ──► Recorder ──► Exporter                              │  │
│  │  lb.metrics ──► Dashboard (via SignalBridge)                       │  │
│  │  chaos.* ──► Logs ──► Backend state changes                       │  │
│  └─────────────────────────┬─────────────────────────────────────┘  │
│                            │                                         │
│  ┌─────────────────────────▼─────────────────────────────────────┐  │
│  │  LB Core                                                          │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐     │  │
│  │  │ Frontend     │───▶│ Router      │───▶│ Pool (backends) │     │  │
│  │  │ (aiohttp)    │    │ (algorithm) │    │                  │     │  │
│  │  └─────────────┘    └─────────────┘    └────────┬─────────┘     │  │
│  │                                                │                 │  │
│  │                              ┌─────────────────▼─────────┐     │  │
│  │                              │   Health Checker          │     │  │
│  │                              │  Active · Passive · CB     │     │  │
│  │                              │  State Machine            │     │  │
│  │                              └─────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────▼─────────────────────────────────────┐  │
│  │  Mock Backends (aiohttp servers on 127.0.0.1:<port>)          │  │
│  │  /health · /fast · /slow · /error · /flaky                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────▼─────────────────────────────────────┐  │
│  │  Load Generator (synthetic client)                             │  │
│  │  Patterns: constant · ramp-up · spike · sine · burst           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| Frontend | `lb/frontend.py` | aiohttp server that proxies requests to backends |
| Router | `lb/router.py` | Selects a backend using the active algorithm; provides rationale |
| Pool | `lb/pool.py` | Registry of backends; filters by state for active routing |
| Backend | `lb/backend.py` | Dataclass: id, host, port, weight, state, counters |
| Algorithms | `lb/algorithms/` | RR, WRR, LC, LRT, IP Hash, Random, P2C, Consistent Hash |
| Active Checker | `lb/health/active.py` | Periodic GET /health probes |
| Passive Checker | `lb/health/passive.py` | Observes 5xx rate, latency from actual requests |
| Circuit Breaker | `lb/health/circuit_breaker.py` | per-backend open/half-open/closed state |
| State Machine | `lb/health/state_machine.py` | Transitions: HEALTHY → DEGRADED → UNHEALTHY |
| Mock Backend | `simulator/mock_backend.py` | Spawns aiohttp servers simulating real backends |
| Load Generator | `simulator/load_generator.py` | Synthetic HTTP client at configured RPS |
| Traffic Patterns | `simulator/patterns.py` | constant, ramp-up, spike, sine wave, burst |
| Chaos Engine | `simulator/chaos.py` | Fault injection: kill, latency, 500s, random |
| Recorder | `analytics/recorder.py` | Records events for replay/export |
| Exporter | `analytics/exporter.py` | CSV / JSON / Prometheus exports |
| GUI App | `gui/app.py` | Main window, tabs, wiring, lifecycle |
| Dashboard | `gui/dashboard_tab.py` | Topology, global graph, sparklines |

## Threading / Async Model

```
Main Thread (Qt):
  - PyQt6 event loop (QApplication)
  - All GUI widgets, timers, signals
  - System tray, menu bar, status bar

Worker Thread (qasync / asyncio):
  - asyncio event loop (ProactorEventLoop on Windows)
  - aiohttp frontend server
  - Mock backend servers
  - Load generator
  - Health checker loop
  - Chaos engine loop

Marshaling:
  - SignalBridge (PyQt6.QObject) emits events from asyncio thread
    to Qt slots via QMetaObject.invokeMethod( QueuedConnection )
  - No polling; GUI updates only when events arrive
```

## Sequence Diagrams

### Normal Request Routing

```
Client (Load Generator)
  │
  ▼
Frontend (aiohttp, port 8000)
  │  GET /fast
  │
  ▼
Router.pick(ctx, metrics)
  │  candidates = Pool.active()
  │  backend = Algorithm.pick(ctx, candidates, metrics)
  │  rationale = Router._explain(backend, ctx)
  │
  ▼
aiohttp.ClientSession.get(http://127.0.0.1:<port>/fast)
  │  ← Response(body, status)
  │
  ▼
Router.on_response(backend, rtt_ms, ok)
  │  Algorithm.on_response(...)
  │  PassiveChecker.record(backend_id, ok, rtt_ms)
  │
  ▼
SignalBridge.emit_later("lb.request", {...})
  │  (GUI logs tab appends HTML line)
  │
  ▼
 Recorder.record("request", {...})
```

### Backend Failure → Removal → Failover

```
[health checker loop]
  │
  ▼
ActiveChecker.should_probe()
  │  GET http://127.0.0.1:<port>/health  (timeout=2s)
  │  ← timeout / 500 / connection refused
  │
  ▼
ActiveChecker.record_probe(backend, success=False)
  │  backend.failed_checks += 1
  │
  ▼
HealthStateMachine.update(backend)
  │  if failed_checks >= unhealthy_threshold:
  │     return BackendState.UNHEALTHY
  │
  ▼
Pool.active() now excludes this backend
  │
  ▼
Router.pick() → next eligible backend
  │  (failover: traffic rerouted automatically)
```

### Backend Recovery → Re-admission

```
[health checker loop — every interval_s]
  │
  ▼
ActiveChecker.should_probe()
  │  GET /health → 200 OK
  │
  ▼
ActiveChecker.record_probe(backend, success=True)
  │  backend.ok_checks += 1
  │  backend.failed_checks = max(0, failed_checks - 1)
  │
  ▼
HealthStateMachine.update(backend)
  │  if ok_checks >= recovery_threshold:
  │     return BackendState.HEALTHY
  │
  ▼
Pool.active() includes backend again
  │  (traffic flows back to recovered backend)
```

### Circuit Breaker Open → Half-Open → Closed

```
[passive checker accumulates errors]
  │
  ▼
CircuitBreaker.on_response(backend, ok=False)
  │  failures += 1
  │  if failures > threshold:
  │     state = OPEN
  │     opened_at = now
  │
  ▼
CircuitBreaker.on_request(backend)
  │  if state == OPEN:
  │     if now - opened_at > cooldown_ms:
  │        state = HALF_OPEN
  │        return True (allow one probe)
  │     else:
  │        return False (reject)
  │
  ▼
[half-open: single probe allowed]
  │  GET /health → OK
  │
  ▼
CircuitBreaker.on_response(backend, ok=True)
  │  successes += 1
  │  if state == HALF_OPEN and successes >= success_threshold:
  │     state = CLOSED
  │     failures = 0
  │
  ▼
Normal routing resumes for this backend
```

## Algorithm Contract

```python
class Algorithm(Protocol):
    name: str

    def pick(
        self,
        request: RequestContext,   # client_ip, path
        candidates: list[Backend], # eligible backends
        metrics: MetricsView,      # rps, active_conns, error_pct
    ) -> Backend: ...

    def on_response(
        self,
        backend: Backend,
        rtt_ms: float,
        ok: bool,
    ) -> None: ...

    def snapshot(self) -> dict:  # for GUI visualization
        ...
```

To add a new algorithm:
1. Create `lb/algorithms/myalgo.py` with a class implementing the protocol
2. Register in `lb/algorithms/__init__.py` under `_REGISTRY`
3. Add name to the combo box in `gui/algorithm_tab.py`

## Health State Machine

```
                    ┌──────────────┐
         ┌─────────│   HEALTHY    │─────────┐
         │ fail    └──────┬───────┘  recover │
         ▼                │                  ▼
  ┌─────────────┐         │         ┌──────────────┐
  │  DEGRADED   │         │         │   HEALTHY    │
  └──────┬──────┘         │         └──────────────┘
  K fail  │               │
  ▼        │               │
┌─────────────┐            │
│  UNHEALTHY  │            │
└──────┬──────┘            │
  manual│                  │
  enable│                  │
  ▼      │                  │
┌─────────────┐            │
│  DISABLED   │◄───────────┘
└──────┬──────┘
  drain│ (in-flight=0)
  ▼
┌─────────────┐
│ DISABLED    │
└─────────────┘
```

Circuit Breaker overlay (per-backend):
```
CLOSED ──(error rate > threshold)──▶ OPEN
OPEN   ──(cooldown elapsed)───────▶ HALF-OPEN
HALF-OPEN ──(probe OK)────────────▶ CLOSED
HALF-OPEN ──(probe FAIL)──────────▶ OPEN
```

## Metrics Model

### Per-Backend Counters
- `latency_ms` — last observed RTT (ms)
- `error_rate` — fraction of failed requests (0..1)
- `failed_checks` / `ok_checks` — health probe counters
- `state` — BackendState enum

### Global Histograms
- `SlidingHistogram` — sliding window of latency samples (default 500)
  - `.percentile(p)` — approximate p-th percentile
  - `.avg()` — mean over window
  - `.count()` — samples in window

### Derived Metrics
- Global RPS = sum of per-backend RPS (smoothed)
- Global error % = mean of per-backend error rates

## Performance Budget

| Metric | Target |
|--------|--------|
| Simulated RPS | 10,000 |
| CPU usage | < 10% on modern CPU |
| RAM | < 300 MB |
| GUI latency | < 16 ms (60 fps) |
| Health probe interval | 1–60 s (configurable) |

## Extension Points

1. **New algorithm**: implement `Algorithm` protocol, register in `__init__.py`
2. **New chaos type**: add method to `ChaosEngine`, hook in GUI
3. **New visualization**: add widget to `gui/widgets/`, wire in tab
4. **New traffic pattern**: add function to `simulator/patterns.py`
5. **New exporter format**: add method to `analytics/exporter.py`

## Build & Packaging Pipeline

```
build.bat:
  1. python -m venv venv
  2. venv\Scripts\pip install -r requirements.txt
  3. pyinstaller build.spec
  4. dist/LBSimulator.exe
```

Output: `dist/LBSimulator.exe` (single-file, windowed, no console).

## Cross-Platform Notes

- Core is cross-platform (Python + aiohttp + PyQt6)
- Windows-first packaging via PyInstaller
- macOS: use `python setup.py bdist_mac` or `pyinstaller --onefile --windowed`
- Linux: `pyinstaller --onefile --windowed` + appropriate icon
