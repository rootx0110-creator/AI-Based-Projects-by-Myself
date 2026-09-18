import threading
import time

SEVERITIES = {
    1: "Info",
    2: "Warning",
    3: "Critical",
}

ALERT_COLORS = {
    1: "#38bdf8",
    2: "#f59e0b",
    3: "#ef4444",
}


class Alert:
    __slots__ = ("id", "ts", "severity", "source", "title", "detail", "status")

    def __init__(self, row):
        self.id = row["id"]
        self.ts = row["ts"]
        self.severity = row["severity"]
        self.source = row["source"]
        self.title = row["title"]
        self.detail = row["detail"]
        self.status = row["status"]

    @property
    def severity_label(self):
        return SEVERITIES.get(self.severity, str(self.severity))

    @property
    def time_label(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ts))


class AlertBus:
    """Persists alerts to storage and fans them out to in-process listeners."""

    def __init__(self, storage):
        self.storage = storage
        self._listeners = []
        self._lock = threading.Lock()

    def subscribe(self, fn):
        with self._lock:
            self._listeners.append(fn)

    def notify(self, severity, source, title, detail=""):
        ts = time.time()
        alert_id = self.storage.add_alert(ts, severity, source, title, detail)
        row = {"id": alert_id, "ts": ts, "severity": severity, "source": source,
               "title": title, "detail": detail, "status": "open"}
        alert = Alert(row)
        listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(alert)
            except Exception:
                pass
        return alert