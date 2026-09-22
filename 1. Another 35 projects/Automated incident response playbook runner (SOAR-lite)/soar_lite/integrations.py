"""Simulated integration bus.

Adapters mimic real security tooling so the full IR lifecycle can run offline.
The interface mirrors what a real adapter would implement:

    execute(settings, action, params) -> {ok, output, latency_ms}

Outputs are deterministic enough for demos: verdicts are derived from the
indicator values so playbook branches behave predictably.
"""

import random
import time

from .storage import utcnow


# --------------------------------------------------------------------------
# deterministic verdicts so demo branches behave sensibly
# --------------------------------------------------------------------------
def _verdict_for(value, field):
    value = (value or "").lower()
    malicious_markers = {
        "domain": ["automation.cn", "recovery.center", "cdn-updates-svc", "amp-scanner",
                   "sinkhole", "phish", "c2"],
        "ip": ["45.140", "91.108", "185.220", "103.88", "198.51.100", "10.66.66"],
        "hash": ["7f3c9d21e8a54b0f", "3ab04f7c19d26e8a"],
        "email": ["notice-automation", "security@", "billing@", "invoice@"],
        "url": ["automation.cn", "invoice", "payment", "login", "secure", "account", "office"],
    }
    markers = malicious_markers.get(field, [])
    for m in markers:
        if m in value:
            return "malicious"
    suspicious = ["login", "office", "dropbox", "onmicrosoft", "weebly", "blogspot"]
    for m in suspicious:
        if m in value:
            return "suspicious"
    return "clean"


def _pick(source):
    return random.choice(source)


# --------------------------------------------------------------------------
# adapter implementations
# --------------------------------------------------------------------------
def run_siem(settings, action, p):
    queries = {
        "query": {
            "events_returned": random.randint(1, 240),
            "head": [
                {"time": utcnow(), "src": _pick(["10.10.0.14", "10.10.2.77", "10.10.0.9", "10.20.1.33"]),
                 "user": p.get("query", "").split("==")[-1].strip() if "==" in p.get("query", "") else "unknown",
                 "finding": _pick(["auth_ok_window", "network_connect_443", "process_spawn", "email_delivered"])} for _ in range(8)
            ],
            "timespan": "last 48h",
        }
    }
    return queries["query"]


def run_ti(settings, action, p):
    value = p.get("value", "")
    if "://" in value:
        field = "url"
    elif "." in value and ":" not in value and value.count(".") in (1, 2, 3) and not _is_ip(value):
        field = "domain"
    elif _is_ip(value):
        field = "ip"
    else:
        field = "hash"
    verdict = _verdict_for(value, field)
    if action == "ti.hash_reputation":
        field = "hash"
        repair = "ransomware" if value.lower().startswith("7f3c") else verdict
        return {"hash": value, "verdict": repair, "score": random.randint(40, 100),
                "family": _pick(["LockBit", "Emotet", "Qbot", "Dridex", "SocGholish"]), "sources": 6,
                "first_seen": utcnow(), "tags": ["c2", "trojan", "ransomware"] if repair == "ransomware" else ["trojan"]}
    return {"value": value, "field": field, "verdict": verdict,
            "score": {"malicious": random.randint(75, 99), "suspicious": random.randint(51, 74), "clean": random.randint(1, 49)}.get(verdict, 20),
            "sources": 4, "last_updated": utcnow(), "related_domains": ["evil-aux.net", "static-update.tk"] if verdict == "malicious" else []}


def _is_ip(value):
    parts = value.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


def run_sandbox(settings, action, p):
    value = p.get("hash", "")
    mal = value.lower().startswith(("7f3c", "3ab0"))
    return {"file": p.get("file", "unknown.bin"), "verdict": ("malicious" if mal else "clean"),
            "score": random.randint(70, 100) if mal else random.randint(3, 20),
            "detections": ["T1486_Encrypt", "T1105_Ingress", "T1059_Powershell"] if mal else [],
            "net_beacons": [{"dst": "91.108.56.144", "port": 443, "count": 87}] if mal else []}


def run_edr(settings, action, p):
    host = p.get("host", "unknown-host")
    return {"host": host, "isolated": True, "license": "licensed", "process_kill": True,
            "quarantined_path": "C:\\ProgramData\\vault", "remaining_processes": 0}


def run_firewall(settings, action, p):
    return {"ip": p.get("ip", ""), "blocked": True, "rule": p.get("rule", "AUTO-BLOCK"),
            "policy": "inside->outside", "rule_id": f"FW-{random.randint(10000, 99999)}",
            "ttl_days": 30}


def run_dns(settings, action, p):
    if action == "dns.query_burst":
        return {"qps": random.randint(5000, 90000), "amplification_factor": 48.5,
                "reflection": True, "top_source_asns": ["AS9002", "AS7195"]}
    return {"domain": p.get("domain", ""), "sinkholed": True, "sinkhole_ip": "10.255.255.1",
            "dnssec": "validated"}


def run_mail(settings, action, p):
    if action == "mail.trace":
        return {"message_id": p.get("message_id", "MSG-000000"), "found": True,
                "delivered": True, "recipients_found": random.randint(1, 40),
                "gateway": "mx1.corp.local", "spf": "fail", "dkim": "softfail"}
    return {"quarantined": True, "policy": "HighRisk-Phishing", "quarantine_store": "EDH"}


def run_ticketing(settings, action, p):
    return {"ticket": f"CSE-{random.randint(100000, 999999)}",
            "status": p.get("status", "updated"), "assignee": "SOC-L3",
            "summary": p.get("summary", "Incident response case")}


def run_iam(settings, action, p):
    return {"user": p.get("user", ""), "sessions_revoked": random.randint(1, 12),
            "mfa_required": True, "password_reset": "forced", "risk_detected": True}


def run_dcdn(settings, action, p):
    return {"domain": p.get("domain", ""), "scrubbing": True, "clean_traffic_routed": True,
            "bps_absorbed": round(random.uniform(2.1, 6.4), 1), "provider": "Cloudflare Spectrum"}


def run_waf(settings, action, p):
    return {"target": p.get("target", ""), "rate_limit": True, "rpm": p.get("rpm", 180),
            "challenge_mode": "managed", "bot_score_threshold": 30}


ADAPTERS = {
    "siem": run_siem,
    "ti": run_ti,
    "sandbox": run_sandbox,
    "edr": run_edr,
    "firewall": run_firewall,
    "dns": run_dns,
    "mail": run_mail,
    "ticketing": run_ticketing,
    "iam": run_iam,
    "dcdn": run_dcdn,
    "waf": run_waf,
}

# map action strings to the integration key that serves them
ACTION_OWNER = {
    "siem.query": "siem",
    "ti.url_reputation": "ti", "ti.ip_reputation": "ti", "ti.hash_reputation": "ti",
    "sandbox.submit": "sandbox",
    "edr.isolate_endpoint": "edr", "edr.kill_process": "edr", "edr.quarantine_file": "edr",
    "fw.block_ip": "firewall",
    "dns.sinkhole": "dns", "dns.query_burst": "dns",
    "mail.trace": "mail", "mail.quarantine": "mail",
    "ticketing.update": "ticketing", "ticketing.create": "ticketing",
    "iam.revoke_sessions": "iam",
    "dcdn.scrub": "dcdn",
    "waf.rate_limit": "waf",
}


class IntegrationBus:
    """Executes adapter actions with simulated latency + failure."""

    def __init__(self, store):
        self.store = store

    def health(self):
        settings = self.store.get("settings").get("integrations", {})
        rows = []
        for key, fn in ADAPTERS.items():
            cfg = settings.get(key, {})
            rows.append({
                "key": key,
                "enabled": cfg.get("enabled", True),
                "latency_ms": cfg.get("latency_ms", 500),
                "failure_rate": cfg.get("failure_rate", 0.02),
                "ok": cfg.get("enabled", True),
            })
        return rows

    def execute(self, action, params, latency_ms=None, failure_rate=None):
        integ_key = ACTION_OWNER.get(action)
        if not integ_key or integ_key not in ADAPTERS:
            return {"ok": False, "output": {"error": f"Unknown action: {action}"},
                    "latency_ms": 0, "integration": "unknown"}

        settings = self.store.get("settings").get("integrations", {}).get(integ_key, {})
        if not settings.get("enabled", True):
            return {"ok": False, "output": {"error": f"Integration {integ_key} disabled"},
                    "latency_ms": 0, "integration": integ_key}

        latency = latency_ms if latency_ms is not None else settings.get("latency_ms", 500)
        frate = failure_rate if failure_rate is not None else settings.get("failure_rate", 0.02)

        time.sleep(latency / 1000.0)
        if random.random() < frate:
            return {"ok": False, "output": {"error": "upstream timeout (simulated)"},
                    "latency_ms": int(latency), "integration": integ_key}

        try:
            output = ADAPTERS[integ_key](settings, action, params)
        except Exception as exc:  # simulate adapter crash
            return {"ok": False, "output": {"error": str(exc)},
                    "latency_ms": int(latency), "integration": integ_key}
        return {"ok": True, "output": output, "latency_ms": int(latency), "integration": integ_key}