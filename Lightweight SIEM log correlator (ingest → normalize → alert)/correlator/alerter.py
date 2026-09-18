"""Alert manager: turns correlations into actionable alerts with lifecycle."""
from datetime import datetime


class AlertManager:
    def __init__(self, store):
        self.store = store
        self._seq = 0

    def _next_id(self):
        self._seq += 1
        return self._seq + self.store.ingest_seq

    def new_alert(self, correlation, source_event=None):
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        risk = correlation.get("risk", 50)
        severity = correlation.get("severity")
        tier = alert_tier(risk)
        if tier_weight(severity) > tier_weight(tier):
            tier = severity

        alert = {
            "id": self._next_id(),
            "title": correlation.get("rule_name"),
            "rule": correlation.get("rule"),
            "description": correlation.get("description"),
            "severity": tier,
            "risk": risk,
            "status": "open",
            "generated_at": now,
            "correlation_id": correlation.get("abstract_id"),
            "count": correlation.get("count", 0),
            "grouped_value": correlation.get("grouped_value"),
            "event_sample": (correlation.get("sample") or [])[:3],
            "actor": correlation.get("grouped_value"),
            "updated_at": now,
        }
        return self.store.add_alert(alert)

    def ack(self, alert_id):
        return self.store.ack_alert(alert_id)

    def close(self, alert_id):
        return self.store.close_alert(alert_id)


def tier_weight(sev):
    return {
        "info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5,
    }.get(sev, 0)


def alert_tier(risk):
    if risk >= 80:
        return "critical"
    if risk >= 60:
        return "high"
    if risk >= 40:
        return "medium"
    if risk >= 20:
        return "low"
    return "info"