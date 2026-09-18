"""Correlation engine: rule-based temporal correlation across normalized events.

Sliding time windows group matching events; when the threshold is reached a
correlation object is produced, which feeds the alert stage.
"""
import hashlib
import time
from collections import deque
from datetime import datetime

# ---------------------------------------------------------------------------
# Rule definitions
#   window     : sliding window in seconds
#   threshold  : number of matching events needed
#   required   : required value for a key (string to match exactly) — omit = any
#   later_type : optional event_type that must arrive AFTER the first category
# ---------------------------------------------------------------------------
DEFAULT_RULES = [
    {
        "id": "brute_force",
        "name": "Brute Force Attempt",
        "description": "Repeated failed auth attempts from a single source IP.",
        "match": {"event_type": "auth_failed"},
        "group_by": "src_ip",
        "window": 60,
        "threshold": 5,
        "severity": "high",
    },
    {
        "id": "port_scan",
        "name": "Port Scan Detected",
        "description": "One source hitting many distinct destination ports.",
        "match": {"event_type": "connect"},
        "group_by": "src_ip",
        "distinct": "dst_port",
        "window": 60,
        "threshold": 8,
        "severity": "high",
    },
    {
        "id": "ssh_scan",
        "name": "SSH Scan Pattern",
        "description": "Many distinct users attempted from one source IP.",
        "match": {"event_type": "auth_failed"},
        "group_by": "src_ip",
        "distinct": "user",
        "window": 120,
        "threshold": 6,
        "severity": "medium",
    },
    {
        "id": "data_exfil",
        "name": "Potential Data Exfiltration",
        "description": "Large outbound transfer from a single source.",
        "match": {"event_type": "outbound"},
        "group_by": "src_ip",
        "window": 120,
        "threshold": 3,
        "severity": "critical",
    },
    {
        "id": "ids_alert",
        "name": "IDS Alert Burst",
        "description": "A burst of intrusion-detection alerts from one host.",
        "match": {"event_type": "ids_alert"},
        "group_by": "src_ip",
        "window": 60,
        "threshold": 3,
        "severity": "high",
    },
    {
        "id": "escalation",
        "name": "Privilege Escalation Sequence",
        "description": "Failed auth followed by successful auth from same actor.",
        "first_type": "auth_failed",
        "later_type": "auth_success",
        "group_by": "src_ip",
        "window": 300,
        "threshold": 1,
        "severity": "critical",
    },
]

SEVERITY_WEIGHT = {
    "info": 5,
    "low": 15,
    "medium": 30,
    "high": 55,
    "critical": 80,
}


class RuleEngine:
    def __init__(self, rules=None, window_scale=1.0):
        self.rules = rules or DEFAULT_RULES
        self.window_scale = window_scale
        # group_key -> deque of (event_epoch, event, rule)
        self._buckets = {}

    # ------------------------------------------------------------------ util
    @staticmethod
    def _epoch(event):
        ts = event.get("timestamp")
        if not ts:
            return time.time()
        try:
            s = str(ts).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                return dt.timestamp()
            return dt.timestamp()
        except Exception:
            return time.time()

    @staticmethod
    def _group_key(rule, event):
        gb = rule.get("group_by")
        if gb:
            return f"{rule['id']}|{event.get(gb)}"
        vals = []
        required_keys = set(rule.get("match", {}).keys()) | set(
            [rule.get("first_type"), rule.get("later_type")]
        )
        for k in ("src_ip", "dst_ip", "user", "event_type"):
            if k in required_keys or (gb is None):
                v = event.get(k)
                if v is not None:
                    vals.append(f"{k}={v}")
        return f"{rule['id']}|{'&'.join(vals) or 'any'}"

    @staticmethod
    def _risk(event):
        sev = event.get("severity", "info")
        return SEVERITY_WEIGHT.get(sev, 10)

    # ------------------------------------------------------------- matching
    def _matches_basic(self, rule, event):
        m = rule.get("match")
        if not m:
            return False
        for key, val in m.items():
            if event.get(key) != val:
                return False
        return True

    def _matches_escalation(self, rule, event):
        if event.get("event_type") == rule.get("first_type"):
            return True
        if event.get("event_type") == rule.get("later_type"):
            return True
        return False

    def _matches_rule(self, rule, event):
        if "match" in rule:
            return self._matches_basic(rule, event)
        if "first_type" in rule:
            return self._matches_escalation(rule, event)
        return False

    def _distinct_count(self, rule, events):
        dkey = rule.get("distinct")
        if not dkey:
            return None
        unique = {ev.get(dkey) for ev in events if ev.get(dkey) is not None}
        return len(unique), list(unique)[:20]

    def _prune(self, rule, bucket, now):
        window = rule.get("window", 60) * self.window_scale
        cutoff = now - window
        while bucket and bucket[0][0] < cutoff:
            bucket.popleft()

    # ----------------------------------------------------------------- main
    def evaluate(self, event):
        """Feed one normalized event; return list of fired correlations."""
        now = self._epoch(event)
        fired = []
        for rule in self.rules:
            if not self._matches_rule(rule, event):
                continue
            key = self._group_key(rule, event)
            bucket = self._buckets.setdefault(key, deque())
            bucket.append((now, event))
            self._prune(rule, bucket, now)

            distinct = self._distinct_count(rule, [e for _, e in bucket])

            n = len(bucket)
            threshold = rule.get("threshold", 3)
            if distinct is not None:
                n = distinct[0]
            if n >= threshold:
                # fire once per window: take current window slice and clear
                window = rule.get("window", 60) * self.window_scale
                cutoff = now - window
                window_events = [e for ts, e in bucket if ts >= cutoff]
                unique_events = []
                seen = set()
                for e in window_events:
                    marker = e.get("hash") or id(e)
                    if marker not in seen:
                        seen.add(marker)
                        unique_events.append(e)
                self._buckets[key] = deque()  # reset to avoid spam
                fired.append(self._make_correlation(rule, unique_events, now))
        return fired

    def _make_correlation(self, rule, events, now):
        sev = rule.get("severity")
        risk = max((self._risk(e) for e in events), default=40)
        if rule.get("severity") in ("critical", "high"):
            risk = max(risk, 65)
        ctx = {
            "rule": rule["id"],
            "rule_name": rule["name"],
            "description": rule["description"],
            "timestamp": datetime.utcfromtimestamp(now).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "severity": sev,
            "risk": risk,
            "count": len(events),
            "window": rule.get("window"),
            "distinct_by": rule.get("distinct"),
            "event_ids": [e.get("ingest_id") for e in events[:50]],
            "hashes": list({e.get("hash") for e in events})[:20],
            "sample": [e.get("raw")[:300] for e in events[:5]],
            "grouped_value": events[-1].get(rule.get("group_by")) if events else None,
        }
        return ctx