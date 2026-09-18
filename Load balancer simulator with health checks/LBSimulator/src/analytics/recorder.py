"""Event recorder with timeline support for replay."""

import json
from typing import List
from src.core.ring_buffer import RingBuffer
from src.core.clock import Clock

class EventRecorder:
    """Records domain events to disk and supports timeline scrubbing."""

    def __init__(self, max_events: int = 10000) -> None:
        self._buffer = RingBuffer(max_events)

    def record(self, event_type: str, payload: dict) -> None:
        self._buffer.append({
            "type": event_type,
            "payload": payload,
            "ts": Clock.now_iso(),
        })

    def get_recent(self, n: int = 200) -> List[dict]:
        return self._buffer.get_all(n)

    def export_json(self, path: str) -> None:
        events = list(reversed(self._buffer.get_all(self._buffer.size)))
        with open(path, "w") as f:
            json.dump({"events": events, "exported_at": Clock.now_iso()}, f, indent=2)

    def export_csv(self, path: str) -> None:
        events = list(reversed(self._buffer.get_all(self._buffer.size)))
        with open(path, "w") as f:
            f.write("ts,type,payload\n")
            for e in events:
                import json as _json
                f.write(f"{e['ts']},{e['type']},{_json.dumps(e['payload'])}\n")
