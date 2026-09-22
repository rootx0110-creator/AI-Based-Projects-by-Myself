"""Central defaults and reference data for SOAR-Lite."""

import os
import sys


def _bundle_root():
    """Read-only resources root (templates/static/playbooks)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_dir():
    """Writable runtime state lives next to the binary in frozen mode."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "data")
    return os.path.join(_bundle_root(), "data")


BASE_DIR = _bundle_root()
DATA_DIR = _data_dir()
PLAYBOOK_DIR = os.path.join(BASE_DIR, "playbooks")
STATIC_DIR = os.path.join(BASE_DIR, "static")
REPORT_CACHE = os.path.join(DATA_DIR, "report_cache")

SEVERITIES = ["critical", "high", "medium", "low", "informational"]

INCIDENT_TYPES = [
    "phishing",
    "malware",
    "ransomware",
    "unauthorized_access",
    "ddos",
    "data_exfil",
    "insider_threat",
    "other",
]

PLAYBOOK_BY_TYPE = {
    "phishing": "pb_phishing",
    "malware": "pb_malware",
    "ransomware": "pb_ransomware",
    "unauthorized_access": "pb_unauthorized_access",
    "ddos": "pb_ddos",
    "insider_threat": "pb_unauthorized_access",
    "data_exfil": "pb_malware",
}

LIFECYCLE_ORDER = [
    "open",
    "triage",
    "contained",
    "eradicated",
    "recovered",
    "closed",
]
ALLOWED_PHASES = LIFECYCLE_ORDER + ["monitoring", "cancelled"]

SEVERITY_WEIGHT = {"critical": 100, "high": 75, "medium": 50, "low": 25, "informational": 5}

DEFAULT_SETTINGS = {
    "instance": {"label": "SOAR-Lite — CyberSOC", "timezone": "UTC"},
    "risk_weights": {
        "severity": 0.35,
        "ti_verdict": 0.30,
        "ioc_count": 0.15,
        "critical_asset": 0.10,
        "ransom_index": 0.10,
    },
    "integrations": {
        "siem": {"enabled": True, "latency_ms": 700, "failure_rate": 0.04},
        "ti": {"enabled": True, "latency_ms": 500, "failure_rate": 0.02},
        "sandbox": {"enabled": True, "latency_ms": 1400, "failure_rate": 0.06},
        "edr": {"enabled": True, "latency_ms": 600, "failure_rate": 0.03},
        "firewall": {"enabled": True, "latency_ms": 800, "failure_rate": 0.02},
        "dns": {"enabled": True, "latency_ms": 500, "failure_rate": 0.02},
        "mail": {"enabled": True, "latency_ms": 550, "failure_rate": 0.04},
        "ticketing": {"enabled": True, "latency_ms": 300, "failure_rate": 0.01},
        "iam": {"enabled": True, "latency_ms": 650, "failure_rate": 0.03},
        "dcdn": {"enabled": True, "latency_ms": 400, "failure_rate": 0.01},
        "waf": {"enabled": True, "latency_ms": 400, "failure_rate": 0.01},
    },
}

INTEGRATION_META = [
    {"key": "siem", "name": "SIEM (Log Aggregation)", "vendor": "Splunk", "icon": "activity"},
    {"key": "ti", "name": "Threat Intelligence", "vendor": "OpenCTI/VT", "icon": "radar"},
    {"key": "sandbox", "name": "Dynamic Sandbox", "vendor": "Any.Run", "icon": "flask"},
    {"key": "edr", "name": "Endpoint Protection", "vendor": "CrowdStrike", "icon": "shield"},
    {"key": "firewall", "name": "Next-Gen Firewall", "vendor": "Palo Alto", "icon": "wall"},
    {"key": "dns", "name": "DNS Security", "vendor": "Infoblox", "icon": "dns"},
    {"key": "mail", "name": "Email Gateway", "vendor": "Mimecast", "icon": "mail"},
    {"key": "ticketing", "name": "Case Management", "vendor": "TheHive", "icon": "ticket"},
    {"key": "iam", "name": "Identity & Access", "vendor": "Okta", "icon": "key"},
    {"key": "dcdn", "name": "DDoS Scrubber", "vendor": "Cloudflare", "icon": "cloud"},
    {"key": "waf", "name": "Web App Firewall", "vendor": "AWS WAF", "icon": "web"},
]

ASSET_NAMES = [
    "WEB-01-GATEWAY", "DB-PROD-CORE", "EXCH-MAIL01", "AD-DC-01", "FILE-SRV-CORP",
    "HR-WS-024", "FIN-WS-011", "SAP-APPSRV-3", "VPN-EDGE-FW2", "MAIL-GW-SECONDARY",
]

ANALYSTS = ["A. Reyes", "M. Okafor", "S. Lindqvist", "K. Tanaka", "J. Moreau"]

COMMON_INCIDENT_CONTEXT = {
    "phishing": {
        "sender": "security@notice-automation.cn",
        "message_id": "MSG-58392011",
        "subject": "Invoice #88213 - overdue payment",
        "recipients": 38,
    },
    "ransomware": {
        "host": "FIN-WS-011",
        "process": "vaultctrl.exe",
        "extension": ".lockedx",
        "shared_drive": "S:",
    },
    "malware": {
        "host": "HR-WS-024",
        "process": "svchost_x.dll",
        "parent": "[email]/[link-click]",
    },
    "unauthorized_access": {
        "user": "d.kovacs",
        "auth_type": "VPN + O365",
        "region": "US-East",
        "impossible_travel": True,
    },
    "ddos": {
        "domain": "retail-frontend.example.com",
        "amplification": "NTP reflection",
        "peaks": "3.2 Gbps",
    },
}

IOC_SAMPLES = {
    "phishing": [
        ("url", "http://notice-automation.cn/pay/invoice"), ("ip", "45.140.182.77"),
        ("domain", "notice-automation.cn"), ("email", "security@notice-automation.cn"),
    ],
    "ransomware": [
        ("hash", "7f3c9d21e8a54b0f6c1d8a2e4b0c91d2e3f4a5b6c7d8e9f0a1b2c3d4e5f60708"),
        ("ip", "91.108.56.144"), ("domain", "mint-recovery.center"),
    ],
    "malware": [
        ("hash", "3ab04f7c19d26e8a21f4c0b967d814ab2e05c63f8d1a749bc3e6f0d285a1c49b"),
        ("ip", "185.220.101.44"), ("domain", "cdn-updates-svc.net"),
    ],
    "unauthorized_access": [
        ("ip", "103.88.46.19"), ("user", "d.kovacs"),
    ],
    "ddos": [
        ("ip", "198.51.100.7"), ("domain", "reflect.amp-scanner.top"),
    ],
}