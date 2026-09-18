"""Export metrics in various formats."""

import json
from typing import Dict, Any

class MetricsExporter:
    """Exports per-backend and global metrics."""

    def __init__(self, backends: dict) -> None:
        self._backends = backends

    def to_json(self) -> Dict[str, Any]:
        data = {"backends": {}}
        for bid, b in self._backends.items():
            data["backends"][bid] = {
                "state": b.state.name,
                "latency_ms": b.latency_ms,
                "error_rate": b.error_rate,
                "weight": b.weight,
            }
        return data

    def to_csv(self) -> str:
        lines = ["backend_id,state,latency_ms,error_rate,weight"]
        for bid, b in self._backends.items():
            lines.append(f"{bid},{b.state.name},{b.latency_ms},{b.error_rate},{b.weight}")
        return "\n".join(lines)

    def to_prometheus(self) -> str:
        out = []
        out.append("# HELP lb_backend_state Backend health state (1=healthy,2=degraded,3=unhealthy,4=draining,5=disabled)")
        out.append("# TYPE lb_backend_state gauge")
        state_map = {"HEALTHY": 1, "DEGRADED": 2, "UNHEALTHY": 3, "DRAINING": 4, "DISABLED": 5}
        for bid, b in self._backends.items():
            val = state_map.get(b.state.name, 0)
            out.append(f'lb_backend_state{{backend="{bid}"}} {val}')
            out.append(f'lb_backend_latency_ms{{backend="{bid}"}} {b.latency_ms}')
            out.append(f'lb_backend_error_rate{{backend="{bid}"}} {b.error_rate}')
        return "\n".join(out)
