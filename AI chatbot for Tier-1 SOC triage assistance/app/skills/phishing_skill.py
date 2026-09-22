"""Skill: Phishing / Email Threat Analysis."""
import re

PRIORITY = 10
KEYWORDS = ["phish", "email", "spam", "attachment", "sender", "outlook",
            "mail", "subject", "inbox", "owa", "spoof", "impersonation",
            "invoice", "wire transfer", "ceo fraud", "bec", "unsubscribe"]

_DISPLAY_NAME = "Phishing & Email Threat Analysis"

_FREE_MAIL = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
    "protonmail.com", "mail.ru", "yandex.ru", "163.com", "qq.com",
}
_LOOKALIKE_PAIRS = [
    ("micros0ft", "microsoft"), ("microsift", "microsoft"),
    ("paypa1", "paypal"), ("amaz0n", "amazon"), ("app1e", "apple"),
    ("g00gle", "google"), ("netf1ix", "netflix"), ("faceb00k", "facebook"),
]
_URGENT_PHRASES = [
    "urgent", "immediately", "asap", "action required", "account suspended",
    "account locked", "verify your account", "password expiring",
    "unusual sign-in", "wire transfer", "gift card", "final notice",
    "click here", "payment declined", "limited time",
]
_SENSITIVE_EXT = {".docm", ".xlsm", ".pptm", ".exe", ".scr", ".hta", ".js",
                  ".vbs", ".ps1", ".bat", ".cmd", ".jar", ".lnk", ".iso", ".img", ".ace"}


def _sender_domain(iocs):
    for email in iocs.get("emails", []):
        return email.split("@")[1]
    return None


def _lookalike(domain):
    if not domain:
        return None
    for fake, brand in _LOOKALIKE_PAIRS:
        if fake in domain:
            return brand
    # homoglyph-ish: digit inside a well-known brand name
    if re.search(r"[0-9]", domain.split(".")[0]):
        for brand in ("microsoft", "paypal", "amazon", "google", "dhl", "fedex"):
            base = domain.split(".")[0]
            if brand[:4] in base and base != brand:
                return brand
    return None


def analyze(text, iocs, context):
    low = (text or "").lower()
    sender_domain = _sender_domain(iocs)

    free_mail = sender_domain in _FREE_MAIL if sender_domain else False
    lookalike = _lookalike(sender_domain)

    urgent_hits = [p for p in _URGENT_PHRASES if p in low]
    suspicious_attach = [
        f for f in iocs.get("filenames", [])
        if "." + f.rsplit(".", 1)[-1].lower() in _SENSITIVE_EXT
    ]
    link_count = len(iocs.get("urls", []))

    risk = 0
    if free_mail:
        risk += 15
    if lookalike:
        risk += 35
    risk += min(3 * len(urgent_hits), 24)
    risk += 20 if suspicious_attach else 0
    risk += min(3 * link_count, 12)

    return {
        "phishing": {
            "sender_domain": sender_domain,
            "free_mail": free_mail,
            "lookalike_of": lookalike,
            "urgent_hits": urgent_hits,
            "suspicious_attachments": suspicious_attach,
            "link_count": link_count,
            "risk_score": min(risk, 100),
        }
    }


def respond(text, iocs, analysis, context):
    p = analysis.get("phishing", {})
    if not p:
        return ""
    lines = [f"**{_DISPLAY_NAME}**"]
    if p.get("lookalike_of"):
        lines.append(
            f"- ⚠️ Sender domain looks like a **{p['lookalike_of']}** look-alike "
            f"({p.get('sender_domain') or 'n/a'}) — strong spoof indicator.")
    if p.get("free_mail"):
        lines.append("- Sender uses a free mail provider; verify against expected business correspondence.")
    if p.get("urgent_hits"):
        lines.append(f"- Social-engineering urgency markers: {', '.join('`' + h + '`' for h in p['urgent_hits'][:6])}")
    if p.get("suspicious_attachments"):
        lines.append(f"- Dangerous attachment types: {', '.join('`' + a + '`' for a in p['suspicious_attachments'])}")
    if p.get("link_count"):
        lines.append(f"- {p['link_count']} URL(s) in the alert body — check sandbox detonation before clicking.")
    risk = p.get("risk_score", 0)
    verdict = ("HIGH phishing likelihood" if risk >= 60
               else "MEDIUM phishing likelihood" if risk >= 30
               else "LOW phishing likelihood")
    lines.append(f"- Phishing risk score: **{risk}/100** → {verdict}")
    return "\n".join(lines)


def report_section(analysis):
    p = analysis.get("phishing")
    if not p:
        return None

    def row(k, v):
        return f"<tr><td class='k'>{k}</td><td>{v}</td></tr>"

    lookalike = (f"<span class='bad'>{p['lookalike_of']} look-alike</span>"
                 if p.get("lookalike_of") else "None detected")
    rows = "".join([
        row("Sender domain", p.get("sender_domain") or "—"),
        row("Free mail provider", "Yes" if p.get("free_mail") else "No"),
        row("Brand look-alike", lookalike),
        row("Urgency markers", ", ".join(p.get("urgent_hits", [])) or "None"),
        row("Suspicious attachments", ", ".join(p.get("suspicious_attachments", [])) or "None"),
        row("URLs found", str(p.get("link_count", 0))),
        row("Phishing risk", f"<b>{p.get('risk_score', 0)}/100</b>"),
    ])
    return {"title": "Phishing Analysis", "html": f"<table>{rows}</table>"}
