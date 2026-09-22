"""Skill: Triage Playbook Advisor.

Recommends an actionable playbook based on the alert category detected by the
other skills. Purely offline logic driven by the analysis dict.
"""
PRIORITY = 5  # runs early; its output is used by the chat renderer

_PLAYBOOKS = {
    "phishing": {
        "name": "Phishing Email Triage",
        "steps": [
            "Extract sender domain, subject & all URLs; detonate URLs in a sandbox (never click from prod mailbox).",
            "Search mail gateway for all recipients of the same message; determine spread.",
            "Purge the message from all mailboxes (Zap/purge) if confirmed malicious.",
            "Block sender domain / URLs / attachment hashes at the gateway & proxy.",
            "If a user clicked & entered creds: force password reset + revoke sessions immediately.",
            "Check the recipient's mailbox rules for attacker-created forwarding (BEC indicator).",
        ],
    },
    "malware": {
        "name": "Malware / Endpoint Compromise",
        "steps": [
            "Isolate the endpoint from the network (EDR containment) while preserving memory.",
            "Collect process lineage, autoruns, and hash the sample; submit to sandbox/TI.",
            "Hunt the same hash & C2 domains/IPs across the estate.",
            "Check persistence: scheduled tasks, Run keys, services, WMI subscriptions.",
            "Verify AV/EDR detections are enabled everywhere; reimage if rootkit suspected.",
            "Reset credentials for accounts used on the host.",
        ],
    },
    "ransomware": {
        "name": "Ransomware / Destructive Attack",
        "steps": [
            "Declare a major incident; activate the crisis team & comms plan.",
            "Isolate affected hosts AND take backups offline/immutable immediately.",
            "Block C2 IPs/domains at the firewall & DNS; kill switch domain sinkhole if known.",
            "Identify patient zero & the encryption timeline from EDR telemetry.",
            "Check for data staging/exfiltration before encryption (double-extortion).",
            "Engage legal, cyber-insurance & law enforcement before any ransom decision.",
        ],
    },
    "credential": {
        "name": "Compromised Credentials",
        "steps": [
            "Disable/reset the affected accounts; revoke refresh tokens & active sessions.",
            "Force re-authentication for the tenant segment; check MFA method changes.",
            "Review sign-in logs for the source IPs across ALL accounts (password spray scoping).",
            "Check for mailbox rules, new MFA devices, or OAuth app consents (persistence).",
            "Hunt for lateral movement using those credentials (4624 type 3/10 patterns).",
            "If AD: check for DCSync/LSASS dump events around the same timeframe.",
        ],
    },
    "network": {
        "name": "Suspicious Network Activity / C2",
        "steps": [
            "Confirm the IOC in proxy/DNS/NetFlow — establish periodicity & volume.",
            "Resolve & enrich the destination (passive DNS, TI, WHOIS age).",
            "Block at firewall/DNS/proxy; add to SIEM watchlist retro-hunt 30 days.",
            "Identify the internal source host & user; check for other hosts beaconing.",
            "If tunneling suspected: pull full DNS query logs, measure entropy & lengths.",
            "Escalate to IR if C2 confirmed — treat host as compromised.",
        ],
    },
    "vulnerability": {
        "name": "Vulnerability / Exposure Response",
        "steps": [
            "Verify the finding on the specific asset — version, reachability, exploitability.",
            "Check CISA KEV & vendor advisory for active exploitation status.",
            "If actively exploited & public-facing: apply emergency change / virtual patch (WAF/IPS).",
            "Hunt for exploitation artifacts (web shells, unexpected processes, new admins).",
            "Schedule permanent patch within the risk-based SLA; track exceptions.",
            "Update asset inventory & exposure management data.",
        ],
    },
    "exfiltration": {
        "name": "Data Exfiltration / Insider Risk",
        "steps": [
            "Freeze/preserve relevant audit logs & mailbox data (litigation hold).",
            "Quantify what moved: files, records, classification levels.",
            "Suspend external sharing links & review OAuth grants for the user.",
            "Engage HR/Legal/Privacy before interviewing the user.",
            "Review DLP policy coverage gaps that allowed the movement.",
            "Determine regulatory notification obligations (GDPR 72h, HIPAA, state laws).",
        ],
    },
}

_ORDER = ["ransomware", "phishing", "malware", "credential", "network",
          "vulnerability", "exfiltration"]


def pick_playbook(analysis):
    """Pick the most relevant playbook from the merged analysis dict."""
    if not analysis:
        return None
    mal = analysis.get("malware", {})
    families = " ".join(f.get("family", "").lower() for f in mal.get("families", []))
    if "lockbit" in families or "ryuk" in families or "conti" in families or \
       "ransom" in (analysis.get("_raw_text", "") or "").lower():
        return "ransomware", _PLAYBOOKS["ransomware"]

    for key in _ORDER:
        data = analysis.get(key)
        if not data:
            continue
        score = data.get("risk_score", 0) if isinstance(data, dict) else 0
        if score >= 30:
            return key, _PLAYBOOKS[key]
    # fallback: lowest-bar playbook present
    for key in _ORDER:
        if analysis.get(key):
            return key, _PLAYBOOKS[key]
    return None


def analyze(text, iocs, context):
    # Placeholder so the runner doesn't skip; real output lives in respond/report.
    return {}


def respond(text, iocs, analysis, context):
    pick = pick_playbook(analysis)
    if not pick:
        return ("**Playbook Advisor**\n- No specific playbook matched yet — paste more alert detail "
                "(sender, IOC list, detection rule name, affected host/user) for a tailored plan.")
    key, pb = pick
    lines = [f"**📋 Recommended Playbook — {pb['name']}**"]
    for i, step in enumerate(pb["steps"], 1):
        lines.append(f"{i}. {step}")
    return "\n".join(lines)


def report_section(analysis):
    pick = pick_playbook(analysis)
    if not pick:
        return None
    key, pb = pick
    steps = "".join(f"<li>{s}</li>" for s in pb["steps"])
    html = f"<p class='pb-name'>{pb['name']}</p><ol class='pb-steps'>{steps}</ol>"
    return {"title": "Recommended Response Playbook", "html": html}
