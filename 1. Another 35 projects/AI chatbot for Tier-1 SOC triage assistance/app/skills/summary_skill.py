"""Skill: Executive Summary & Next-Actions Generator.

Synthesizes the merged analysis into a short narrative summary + prioritized
next actions for the SOC analyst. Runs last (highest PRIORITY number).
"""
PRIORITY = 90

_VERDICT_CRITERIA = [
    (75, "CRITICAL — Active threat likely; treat as a potential major incident."),
    (50, "HIGH — Credible threat indicators; escalate to Tier-2/IR for containment."),
    (25, "MEDIUM — Suspicious but inconclusive; enrich and monitor closely."),
    (0,  "LOW — Weak or generic indicators; likely benign, document and close if no further signal."),
]


def _verdict(score):
    for threshold, label in _VERDICT_CRITERIA:
        if score >= threshold:
            return label
    return _VERDICT_CRITERIA[-1][1]


def _top_factors(analysis):
    factors = []
    p = analysis.get("phishing", {})
    if p.get("lookalike_of"):
        factors.append(f"sender domain impersonates {p['lookalike_of']}")
    if p.get("suspicious_attachments"):
        factors.append("dangerous attachment type present")
    c = analysis.get("credential", {})
    if c.get("dumping_tools"):
        factors.append("credential dumping tooling observed")
    if c.get("impossible_travel"):
        factors.append("impossible-travel authentication")
    m = analysis.get("malware", {})
    for fam in m.get("families", [])[:2]:
        factors.append(f"malware family: {fam['family']}")
    n = analysis.get("network", {})
    if n.get("beaconing"):
        factors.append("C2 beaconing pattern")
    if n.get("exfiltration"):
        factors.append("possible data exfiltration")
    v = analysis.get("vulnerability", {})
    if v.get("kev_flag") or v.get("named_vulns"):
        factors.append("known-exploited vulnerability exposure")
    e = analysis.get("exfiltration", {})
    if e.get("hits"):
        factors.append("insider/exfiltration risk markers")
    return factors


def _next_actions(analysis, attack_matches):
    actions = []
    ransomware = any(
        f.get("family", "").lower() in ("lockbit", "ryuk", "conti", "revil")
        for f in analysis.get("malware", {}).get("families", [])
    )
    if ransomware:
        actions.append("Declare major incident & activate ransomware playbook (isolate + protect backups).")
    if analysis.get("phishing", {}).get("lookalike_of") or \
       analysis.get("phishing", {}).get("risk_score", 0) >= 60:
        actions.append("Purge phishing message fleet-wide; block sender & detonate URLs.")
    if analysis.get("credential", {}).get("dumping_tools") or \
       analysis.get("credential", {}).get("pass_the_hash"):
        actions.append("Reset credentials & revoke sessions for affected accounts.")
    if analysis.get("network", {}).get("beaconing") or \
       analysis.get("network", {}).get("exfiltration"):
        actions.append("Block C2 indicators at egress; start 30-day retro-hunt for the same IOCs.")
    if analysis.get("vulnerability", {}).get("kev_flag"):
        actions.append("Emergency-patch or virtually patch the exploited vulnerability today.")
    if analysis.get("exfiltration", {}).get("hits"):
        actions.append("Preserve audit logs & engage Legal/Privacy for regulated data exposure.")
    for m in attack_matches[:2]:
        actions.append(f"Confirm technique {m['id']} ({m['name']}) with endpoint/telemetry evidence.")
    if not actions:
        actions.append("Enrich with TI & user context; monitor and re-evaluate if new signals arrive.")
    return actions[:7]


def analyze(text, iocs, context):
    return {}


def respond(text, iocs, analysis, context):
    sev = context.get("severity", {}) if isinstance(context, dict) else {}
    score = sev.get("score", 0)
    verdict = _verdict(score)
    factors = _top_factors(analysis)
    matches = context.get("attack_matches", []) if isinstance(context, dict) else []
    actions = _next_actions(analysis, matches)

    lines = ["**🧾 Executive Triage Summary**",
             f"- Verdict: **{verdict}** (risk score {score}/100)"]
    if factors:
        lines.append("- Key drivers: " + "; ".join(factors[:5]))
    lines.append("")
    lines.append("**Next actions**")
    for i, a in enumerate(actions, 1):
        lines.append(f"{i}. {a}")
    return "\n".join(lines)


def report_section(analysis):
    # Rendered natively by the report template; nothing extra to add here.
    return None
