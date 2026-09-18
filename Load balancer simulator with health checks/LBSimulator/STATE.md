# State — LBSimulator v1.0.0

## Status

| Item | Value |
|------|-------|
| Version | 1.0.0 |
| Status | Beta |
| Python | 3.11+ |
| Platform | Windows (primary), macOS, Linux |

## Implemented Features

| Feature | Status | Notes |
|---------|--------|-------|
| Frontend listener (aiohttp reverse proxy) | ✅ | Configurable port, default 8000 |
| Backend pool registry | ✅ | Active/healthy filtering |
| Round Robin | ✅ | Cyclic selection |
| Weighted Round Robin | ✅ | Weight-aware cyclic |
| Least Connections | ✅ | Min active conns |
| Least Response Time | ✅ | Min latency |
| IP Hash (sticky) | ✅ | Hash-based sticky |
| Random | ✅ | Uniform random |
| Power of Two Choices (P2C) | ✅ | Two-probe selection |
| Consistent Hashing | ✅ | Virtual-node ring |
| Active health checks | ✅ | Periodic /health probes |
| Passive health checks | ✅ | Error-rate + latency observer |
| Circuit breaker | ✅ | Closed/Open/Half-Open |
| Health state machine | ✅ | HEALTHY/DEGRADED/UNHEALTHY/DRAINING/DISABLED |
| Manual backend controls | ✅ | Kill, drain, enable |
| Traffic generator | ✅ | RPS, concurrency, payload |
| Traffic patterns | ✅ | constant, ramp-up, spike, sine, burst |
| Chaos engine | ✅ | Kill, latency, 500s, random |
| Dashboard tab | ✅ | Topology, global graphs, sparklines |
| Backends tab | ✅ | Per-backend cards with controls |
| Algorithm tab | ✅ | Selector + rationale + descriptions |
| Health tab | ✅ | Configurable thresholds |
| Traffic tab | ✅ | Load generator controls |
| Logs tab | ✅ | Live HTML log with routing decisions |
| Settings tab | ✅ | Theme toggle, hotkeys display |
| Chaos tab | ✅ | Fault injection panel |
| Replay bar | ✅ | Timeline scrubber placeholder |
| System tray | ✅ | Status summary, show/quit |
| Dark/Light theme | ✅ | CSS-based theming |
| Metric export | ✅ | JSON, CSV, Prometheus |
| Ring buffer logs | ✅ | Bounded 1000 entries |
| Event recorder | ✅ | JSON/CSV export, timeline |
| Scenario files | ✅ | 4 demo scenarios |
| Build script | ✅ | build.bat + spec |
| Hotkeys | ✅ | Ctrl+S, Ctrl+Shift+S, F11 |

## Known Issues / Limitations

- Windows ephemeral port limit (~49151) may constrain very high backend counts
- WebSocket passthrough is not implemented (optional, out of scope for v1)
- Consistent Hashing ring rebuild is triggered manually; auto-rebuild on backend change not yet wired
- Percentile calculation uses sorted sliding window (not HDR histogram or t-digest) — fine for시뮬레이션 but may be expensive at very high sample rates
- Replay mode is a stub (timeline bar exists but no actual replay engine)
- No Docker-based backend option (in-process mock servers only)
- System tray icon falls back to default if assets/icon.ico missing

## Roadmap

### v1.1
- [ ] WebSocket passthrough
- [ ] Consistent hash auto-rebuild on pool change
- [ ] Replay engine with timeline scrubber (full implementation)
- [ ] Performance optimization: t-digest for percentiles

### v1.2
- [ ] Prometheus remote write support
- [ ] Grafana dashboard JSON export
- [ ] Docker Compose example for local testing
- [ ] Cross-platform app icon (.icns, .png)

### v2.0
- [ ] Plugin system for custom algorithms and exporters
- [ ] Distributed mode (multiple LB instances)
- [ ] TLS termination (HTTPS frontend)
- [ ] Real backend integration (connect to actual servers)

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `tests/test_algorithms.py` | Round Robin, WRR, LC, LRT, IP Hash, Random, P2C, Consistent Hash |
| `tests/test_health_state_machine.py` | State transitions, thresholds |
| `tests/test_circuit_breaker.py` | Open/half-open/closed transitions |
| `tests/test_router_failover.py` | Backend removal + failover |
| `tests/test_chaos.py` | Kill, latency, 500 injection |

## Changelog

### v1.0.0 (2026-09-12)
- Initial release
- 8 load balancing algorithms
- Full health check subsystem (active, passive, circuit breaker, state machine)
- 5 traffic patterns
- Chaos engineering panel
- Dark/light theme
- 4 demo scenarios
- JSON/CSV/Prometheus export
- System tray integration
- Hotkeys
