"""In-memory store with JSON snapshot persistence.

Keeps raw logs, normalized events, correlations, and alerts — everything
the lightweight SIEM needs — plus aggregate stats used by the dashboard.
"""
import json
import hashlib
import threading
from datetime import datetime
from collections import defaultdict, Counter


def _now():
    return datetime.utcnow().isoformat() + "Z"


def _iso_to_epoch(iso):
    """Convert an ISO-8601 timestamp to epoch seconds (float)."""
    try:
        s = iso.rstrip("Z")
        if "+" in s and s.endswith(":00"):
            s = s[:-6]
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def event_hash(event):
    """Deterministic hash over normalized core fields (for dedup)."""
    parts = (
        str(event.get("timestamp", "")),
        event.get("source", ""),
        event.get("event_type", ""),
        event.get("src_ip", "") or "",
        event.get("dst_ip", "") or "",
        event.get("user", "") or "",
        event.get("message", ""),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


class Event(dict):
    """Normalized common-schema event (dict subclass for easy JSON)."""

    @property
    def epoch(self):
        return _iso_to_epoch(self.get("timestamp", ""))


class Alert(dict):
    @property
    def epoch(self):
        return _iso_to_epoch(self.get("generated_at", ""))


class Correlation(dict):
    @property
    def epoch(self):
        return _iso_to_epoch(self.get("timestamp", ""))


class Store:
    def __init__(self, snapshot_path=None):
        self._lock = threading.Lock()
        self.snapshot_path = snapshot_path
        self.logs = []            # raw logs: {ingest_id, ts, raw}
        self.events = []          # normalized Event objects
        self.correlations = []    # Correlation objects
        self.alerts = []          # Alert objects
        self.stats = {
            "ingested_raw": 0,
            "normalized": 0,
            "failed": 0,
            "correlations": 0,
            "alerts": 0,
            "open_alerts": 0,
            "sessions": 0,
        }
        self.rule_hits = Counter()
        self.events_per_source = Counter()
        self.events_per_type = Counter()
        self.severity_counts = Counter()
        self.top_sources = Counter()
        self.top_destinations = Counter()
        self.hourly_buckets = defaultdict(int)  # key ISO hour
        self.ingest_seq = 0
        if snapshot_path:
            self.load()

    # ---------- ingestion ----------
    def add_raw(self, raw_text: str):
        with self._lock:
            self.ingest_seq += 1
            rec = {
                "ingest_id": self.ingest_seq,
                "ts": _now(),
                "raw": raw_text,
            }
            self.logs.append(rec)
            self.stats["ingested_raw"] += 1
            self._bucket_hour(rec["ts"])
            if len(self.logs) > 20000:
                self.logs = self.logs[-20000:]
            return rec

    def add_event(self, event: dict) -> Event:
        with self._lock:
            ev = Event(event)
            ev["hash"] = ev.get("hash") or event_hash(ev)
            ev["normalized_at"] = _now()
            self.events.append(ev)
            self.stats["normalized"] += 1
            if ev.get("source"):
                self.events_per_source[ev["source"]] += 1
            if ev.get("event_type"):
                self.events_per_type[ev["event_type"]] += 1
            if ev.get("severity"):
                self.severity_counts[ev["severity"]] += 1
            if ev.get("src_ip"):
                self.top_sources[ev["src_ip"]] += 1
            if ev.get("dst_ip"):
                self.top_destinations[ev["dst_ip"]] += 1
            self._bucket_hour(ev.get("timestamp", _now()))
            if len(self.events) > 100000:
                self.events = self.events[-100000:]
            return ev

    def mark_failed(self):
        with self._lock:
            self.stats["failed"] += 1

    def add_correlation(self, corr: dict) -> Correlation:
        with self._lock:
            c = Correlation(corr)
            self.correlations.append(c)
            self.stats["correlations"] += 1
            self.rule_hits[c.get("rule", "unknown")] += 1
            if len(self.correlations) > 20000:
                self.correlations = self.correlations[-20000:]
            return c

    def add_alert(self, alert: dict) -> Alert:
        with self._lock:
            a = Alert(alert)
            self.alerts.append(a)
            self.stats["alerts"] += 1
            self.stats["open_alerts"] += 1
            if len(self.alerts) > 20000:
                self.alerts = self.alerts[-20000:]
            return a

    def ack_alert(self, alert_id: int):
        with self._lock:
            for a in self.alerts:
                if a.get("id") == alert_id and a.get("status") == "open":
                    a["status"] = "acknowledged"
                    a["updated_at"] = _now()
                    self.stats["open_alerts"] = max(
                        0, self.stats["open_alerts"] - 1
                    )
                    return a
        return None

    def close_alert(self, alert_id: int):
        with self._lock:
            for a in self.alerts:
                if a.get("id") == alert_id and a.get("status") in (
                    "open",
                    "acknowledged",
                ):
                    a["status"] = "closed"
                    a["closed_at"] = _now()
                    a["updated_at"] = _now()
                    self.stats["open_alerts"] = max(
                        0, self.stats["open_alerts"] - 1
                    )
                    return a
        return None

    def reset(self):
        with self._lock:
            self.logs.clear()
            self.events.clear()
            self.correlations.clear()
            self.alerts.clear()
            for k in self.stats:
                self.stats[k] = 0
            self.rule_hits = Counter()
            self.events_per_source = Counter()
            self.events_per_type = Counter()
            self.severity_counts = Counter()
            self.top_sources = Counter()
            self.top_destinations = Counter()
            self.hourly_buckets = defaultdict(int)
            self.ingest_seq = 0

    def _bucket_hour(self, iso_ts):
        try:
            key = iso_ts[:13] + ":00Z"
        except Exception:
            key = "unknown"
        self.hourly_buckets[key] += 1

    # ---------- snapshot ----------
    def to_dict(self):
        return {
            "logs": self.logs,
            "events": self.events,
            "correlations": self.correlations,
            "alerts": self.alerts,
            "stats": self.stats,
            "rule_hits": dict(self.rule_hits),
            "events_per_source": dict(self.events_per_source),
            "events_per_type": dict(self.events_per_type),
            "severity_counts": dict(self.severity_counts),
            "top_sources": dict(self.top_sources.most_common(15)),
            "top_destinations": dict(self.top_destinations.most_common(10)),
            "hourly": dict(sorted(self.hourly_buckets.items())),
            "ingest_seq": self.ingest_seq,
        }

    def load(self):
        try:
            with open(self.snapshot_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.logs = data.get("logs", [])
            self.events = [Event(e) for e in data.get("events", [])]
            self.correlations = [Correlation(c) for c in data.get("correlations", [])]
            self.alerts = [Alert(a) for a in data.get("alerts", [])]
            self.stats.update(data.get("stats", {}))
            self.rule_hits = Counter(data.get("rule_hits", {}))
            self.events_per_source = Counter(data.get("events_per_source", {}))
            self.events_per_type = Counter(data.get("events_per_type", {}))
            self.severity_counts = Counter(data.get("severity_counts", {}))
            self.top_sources = Counter(data.get("top_sources", {}))
            self.top_destinations = Counter(data.get("top_destinations", {}))
            self.hourly_buckets = defaultdict(int, data.get("hourly", {}))
            self.ingest_seq = data.get("ingest_seq", 0)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def save(self):
        if not self.snapshot_path:
            return
        with self._lock:
            payload = self.to_dict()
        try:
            with open(self.snapshot_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, default=str)
        except Exception:
            pass