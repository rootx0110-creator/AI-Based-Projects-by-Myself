# Memory — LBSimulator

## Project Conventions

### Naming
- `snake_case` for modules, functions, variables
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Backend IDs: `s1`, `s2`, ... `sN` (short, memorable)

### Log Levels
- `DEBUG` — algorithmic details, per-request traces
- `INFO` — lifecycle events (start/stop, backend up/down)
- `WARNING` — degraded state, circuit breaker trips
- `ERROR` — unrecoverable errors, proxy failures

### Error Codes
- `LB_ERROR_NO_BACKENDS` — pool has no eligible backends
- `LB_ERROR_PROXY_FAILED` — upstream request failed
- `LB_ERROR_HEALTH_FAIL` — health check failed
- `LB_ERROR_CIRCUIT_OPEN` — circuit breaker rejected request

## Design Decision Log (ADR-Style)

### ADR-001: aiohttp over FastAPI+uvicorn for LB core
**Status**: Accepted

**Context**: Need an async HTTP server that can act as a reverse proxy with per-request backend selection.

**Decision**: Use aiohttp because:
1. Built-in `web.AppRunner` + `TCPSite` for easy server lifecycle
2. `ClientSession` for outgoing proxy requests
3. No need for the full FastAPI/Starlette stack — we only need routing + proxy
4. Lighter weight, fewer dependencies

**Consequences**: Manual routing logic in `lb/frontend.py`; no automatic OpenAPI docs.

### ADR-002: In-process mock backends over Docker
**Status**: Accepted

**Context**: We need backend servers that can be killed, have latency injected, and return synthetic errors — all controllable from the GUI.

**Decision**: Spawn aiohttp servers in-process on random ports. Each mock backend is a `MockBackendServer` instance.

**Consequences**:
- Much faster startup than Docker
- No Docker dependency for end users
- Cannot simulate real OS-level failures (but can simulate application-level: kill, 500s, latency)
- Ephemeral port management needed to avoid collisions

### ADR-003: Qt signals over polling for GUI updates
**Status**: Accepted

**Context**: The GUI needs to display real-time metrics without blocking or polling.

**Decision**: Use `SignalBridge` (PyQt6 QObject) to emit domain events from the asyncio thread to Qt slots via `QMetaObject.invokeMethod` with `QueuedConnection`.

**Consequences**:
- No busy-waiting or polling loops
- GUI updates are event-driven
- All state changes flow through the event bus
- Slight complexity in marshalling; but much lower CPU than polling

### ADR-004: Event bus (domain events) vs direct calls
**Status**: Accepted

**Context**: Multiple subsystems (health checker, router, load generator, chaos) need to communicate state changes to the GUI and recorder.

**Decision**: Use a simple in-memory `EventBus` with typed subscriptions.

**Consequences**:
- Decouples publishers from subscribers
- Easy to add new observers (e.g., a future metrics dashboard)
- Single class `Event` envelope
- No external broker needed (in-process only)

## Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_FRONTEND_PORT` | 8000 | LB frontend listener port |
| `DEFAULT_BACKEND_BASE_PORT` | 12000 | First mock backend port |
| `DEFAULT_HEALTH_INTERVAL_S` | 5.0 | Seconds between active probes |
| `DEFAULT_HEALTH_TIMEOUT_S` | 2.0 | Probe timeout |
| `DEFAULT_HEALTH_UNHEALTHY_THRESHOLD` | 3 | Consecutive failures to mark unhealthy |
| `DEFAULT_HEALTH_ERROR_THRESHOLD_PCT` | 5.0 | Passive error rate % to mark degraded |
| `DEFAULT_TRAFFIC_RPS` | 100 | Starting RPS |
| `DEFAULT_TRAFFIC_CONCURRENCY` | 20 | Concurrent client connections |
| `SLIDING_HISTOGRAM_WINDOW` | 500 | Samples per histogram |
| `LOG_BUFFER_CAPACITY` | 1000 | Ring buffer max entries |
| `EVENT_RECORDER_MAX` | 20000 | Maximum events recorded |

## Dependencies + Rationale

| Dependency | Version | Why |
|------------|---------|-----|
| aiohttp | ≥3.11 | Async HTTP server + client for proxy and mock backends |
| PyQt6 | ≥6.7 | Cross-platform GUI framework with signals/slots |
| qasync | ≥0.28 | Integrates asyncio event loop with Qt (QEventLoop) |
| pyqtgraph | ≥0.13 | Fast real-time plotting for dashboard |
| pydantic | ≥2.9 | Config validation (optional, not yet used heavily) |
| numpy | ≥2.2 | Numerical operations for pyqtgraph data arrays |
| pyinstaller | ≥6.10 | Single-file .exe packaging |

## Glossary

| Term | Definition |
|------|-----------|
| Frontend | The reverse proxy listener that receives client requests and forwards them to backends |
| Backend | A server that handles proxied requests; can be real or mock |
| Pool | The registry of all known backends; maintains eligibility state |
| Upstream | Synonym for backend (from proxy perspective) |
| Health Check | Probe to determine if a backend is healthy enough to receive traffic |
| Active Check | Periodic synthetic probe (GET /health) initiated by the LB |
| Passive Check | Observation of actual request outcomes (5xx rate, latency) |
| Circuit Breaker | Pattern that stops sending traffic to a failing backend temporarily |
| P2C (Power of Two Choices) | Algorithm that probes two random candidates and picks the better one |
| Sticky Session | Routing pattern where the same client always goes to the same backend |
| Drain | Gradually stop sending new requests to a backend while finishing in-flight requests |
| Chaos Engineering | Deliberate fault injection to test resilience |
| RPS | Requests per second |
| RTT | Round-trip time (latency) |
| Sliding Histogram | Fixed-window sample buffer for approximate percentile computation |
| Ring Buffer | Fixed-size circular buffer that overwrites oldest entries when full |
| Signal Bridge | PyQt6 mechanism to emit events from asyncio thread to Qt main thread |

## Onboarding Notes

1. **To run from source**: `python src/main.py`
2. **To build .exe**: Run `build.bat`
3. **To add an algorithm**: Create file in `src/lb/algorithms/`, implement `Algorithm` protocol, register in `__init__.py`
4. **To add a chaos action**: Add method to `ChaosEngine`, add button in `gui/chaos_panel.py`
5. **To change theme colors**: Edit the CSS strings in `gui/app.py:_apply_theme`

## Gotchas

1. **Windows asyncio**: Use `ProactorEventLoop` (default on Windows Python 3.8+). aiohttp works fine with it, but some libraries may need `SelectorEventLoop`. qasync handles the bridge.

2. **Qt + asyncio integration**: Use `qasync.QEventLoop` to run both Qt and asyncio in the same thread. Do NOT use `asyncio.run()` alongside `app.exec()` — they conflict.

3. **Fast loopback requests may exhaust ephemeral ports**: Each HTTP request creates a TCP connection. At very high RPS with short-lived connections, Windows ephemeral port range (default ~49151) can be exhausted. Use `TCPConnector(limit=...)` to cap connections.

4. **Percentile calculation**: The current `SlidingHistogram` uses sorted window — O(n log n) per percentile call. For production-scale telemetry, use HDR histogram or t-digest. For this simulator, the window is small enough (500 samples) that it's fine.

5. **Deterministic seed**: The load generator accepts a `seed` parameter for reproducible traffic patterns. Without a seed, results vary between runs (non-deterministic).

6. **Backend port allocation**: Mock backends use port range starting at `backend_base_port`. Ensure this range doesn't conflict with other services.

7. **PyInstaller hidden imports**: aiohttp and aiodns have dynamic imports that PyInstaller may miss. Use `--hidden-import` or `--collect-submodules` in the spec.

8. **PyQt6 + pyqtgraph theme**: pyqtgraph has its own config options (`pg.setConfigOption`) separate from Qt stylesheets. Both must be updated for consistent dark/light themes.
