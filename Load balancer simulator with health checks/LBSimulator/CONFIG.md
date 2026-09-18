# Configuration

LBSimulator stores configuration in `%APPDATA%/LBSimulator/config.json`.

## Default Config

```json
{
  "frontend_port": 8000,
  "backend_count": 3,
  "backend_base_port": 12000,
  "health_check_interval_s": 5.0,
  "health_check_timeout_s": 2.0,
  "health_unhealthy_threshold": 3,
  "health_error_threshold_pct": 5.0,
  "traffic_rps": 100,
  "traffic_concurrency": 20,
  "algorithm": "Round Robin",
  "theme": "dark"
}
```

## Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `frontend_port` | int | 8000 | Port the LB frontend listens on |
| `backend_count` | int | 3 | Number of mock backends to spawn |
| `backend_base_port` | int | 12000 | Starting port for mock backends |
| `health_check_interval_s` | float | 5.0 | Seconds between active health probes |
| `health_check_timeout_s` | float | 2.0 | Timeout for each health probe |
| `health_unhealthy_threshold` | int | 3 | Consecutive failures to mark UNHEALTHY |
| `health_error_threshold_pct` | float | 5.0 | Passive error rate % to mark DEGRADED |
| `traffic_rps` | int | 100 | Starting requests per second |
| `traffic_concurrency` | int | 20 | Concurrent client connections |
| `algorithm` | string | "Round Robin" | Active load balancing algorithm |
| `theme` | string | "dark" | UI theme: "dark" or "light" |
