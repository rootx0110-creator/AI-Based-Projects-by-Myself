# LBSimulator — Load Balancer Simulator with Health Checks

A desktop application that visually simulates a reverse proxy load balancer distributing traffic across multiple backend servers, with real-time health checks, failover, chaos engineering, and live metrics visualization.

![Screenshot](./assets/screenshots/screenshot.png)

## How to Run in 3 Commands

### From Source

```bash
cd LBSimulator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

### Build Executable

```bash
cd LBSimulator
build.bat
```

Output: `dist/LBSimulator.exe`

## Screenshots

| Dashboard | Backends |
|-----------|----------|
| ![Dashboard](./assets/screenshots/dashboard.png) | ![Backends](./assets/screenshots/backends.png) |

| Algorithm | Traffic |
|-----------|---------|
| ![Algorithm](./assets/screenshots/algorithm.png) | ![Traffic](./assets/screenshots/traffic.png) |

| Logs | Settings |
|------|----------|
| ![Logs](./assets/screenshots/logs.png) | ![Settings](./assets/screenshots/settings.png) |

## Features

- **8 Load Balancing Algorithms**: Round Robin, Weighted RR, Least Connections, Least Response Time, IP Hash (sticky), Random, Power of Two Choices, Consistent Hashing
- **Health Check Subsystem**: Active probes, passive observation, circuit breaker, state machine (HEALTHY/DEGRADED/UNHEALTHY/DRAINING/DISABLED)
- **Traffic Simulator**: Configurable RPS, concurrency, 5 traffic patterns (constant, ramp-up, spike, sine wave, burst)
- **Chaos Engineering**: One-click kill, add latency, return 500s, random chaos mode
- **Live Visualization**: Topology diagram with animated edges, per-backend sparklines, global RPS/error graph, color-coded health badges
- **Real-Time Logs**: Live request log with routing rationale ("why this backend?")
- **Dark/Light Theme**: Toggle from Settings
- **System Tray**: Status summary, quick show/quit
- **Hotkeys**: Ctrl+S (start/stop), Ctrl+Shift+S (snapshot/export), F11 (fullscreen)
- **Export**: JSON, CSV, Prometheus text format

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed component diagrams and sequence flows.

## License

MIT — see [LICENSE](./LICENSE) (placeholder).
