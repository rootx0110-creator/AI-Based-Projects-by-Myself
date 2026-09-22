"""Severity scoring engine for SOC triage."""
from app.engine.ioc_extractor import extract_iocs
from app.engine.mitre_mapper import map_attack

# Keywords that signal urgency
CRITICAL_SIGNALS = [
    "ransomware", "data encrypted", "files encrypted", "exfiltration",
    "active breach", "domain admin", "lsass dump", "credential dump",
    "wiper", "critical vulnerability exploited", "zero-day exploited",
    "c2 traffic", "active command and control", "lateral movement",
    "privilege escalation to", "domain controller compromised",
    # Named ransomware / high-impact families are critical by default
    "lockbit", "blackcat", "alphv", "cl0p", "akira", "revil", "conti",
    "ryuk", "maze", "egregor", "clop",
]

HIGH_SIGNALS = [
    "malware", "phishing", "credential theft", "brute force", "beacon",
    "web shell", "exploit attempt", "suspicious powershell", "c2 callback",
    "impossible travel", "account lockout", "data theft", "backdoor",
    "trojan", "keylogger", "remote access trojan", "botnet", "rootkit",
    "malicious attachment", "malicious url", "malicious ip",
]

MEDIUM_SIGNALS = [
    "suspicious", "unusual", "anomaly", "policy violation", "spam",
    "reconnaissance", "port scan", "failed login", "detonation",
    "phish suspected", "link clicked", "unknown publisher",
]

URGENT_HINTS = [
    "urgent", "critical", "immediately", "asap", "production down",
    "ceo", "cfo", "vip user", "executive", "domain controller",
    "payment", "wire transfer", "customer data", "pii", "phi",
]


def compute_severity(text, iocs=None, attack_matches=None):
    """Return dict with score 0-100, severity label and reasons."""
    iocs = iocs or extract_iocs(text)
    attack_matches = attack_matches if attack_matches is not None else map_attack(text, iocs)

    score = 10
    reasons = []

    low = (text or "").lower()

    def add(points, reason):
        nonlocal score
        score += points
        reasons.append(f"+{points}: {reason}")

    # Text signals
    for kw in CRITICAL_SIGNALS:
        if kw in low:
            add(20, f"critical signal '{kw}'")
    for kw in HIGH_SIGNALS:
        if kw in low:
            add(10, f"high signal '{kw}'")
    for kw in MEDIUM_SIGNALS:
        if kw in low:
            add(4, f"medium signal '{kw}'")

    # IOC presence
    if iocs.get("cves"):
        add(15, f"{len(iocs['cves'])} CVE reference(s)")
    if iocs.get("hashes"):
        add(8, f"{len(iocs['hashes'])} file hash(es)")
    if iocs.get("urls"):
        add(6, f"{len(iocs['urls'])} URL(s)")
    if iocs.get("ips"):
        add(4, f"{len(iocs['ips'])} IP address(es)")
    if iocs.get("domains"):
        add(3, f"{len(iocs['domains'])} domain(s)")

    # ATT&CK techniques raise confidence
    tactic_weight = {
        "Initial Access": 10, "Execution": 10, "Persistence": 12,
        "Privilege Escalation": 12, "Defense Evasion": 10,
        "Credential Access": 14, "Discovery": 4, "Lateral Movement": 16,
        "Exfiltration": 20, "Command and Control": 14, "Impact": 22,
    }
    for m in attack_matches[:5]:
        w = tactic_weight.get(m["tactic"].split(" / ")[0], 6)
        add(min(w, 20), f"ATT&CK {m['id']} {m['name']}")

    # Urgency / VIP context
    for kw in URGENT_HINTS:
        if kw in low:
            add(6, f"business context '{kw}'")

    score = max(5, min(100, score))
    severity = severity_from_score(score)
    return {"score": score, "severity": severity, "reasons": reasons[:14]}


def severity_from_score(score):
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


SEVERITY_COLORS = {
    "CRITICAL": "#ff4757",
    "HIGH": "#ffa502",
    "MEDIUM": "#ffd32a",
    "LOW": "#2ed573",
}
