"""Skill: Data Exfiltration & Insider Risk Analysis."""
PRIORITY = 60
KEYWORDS = ["exfiltrat", "data leak", "dlp", "insider", "usb", "removable",
            "upload", "transfer", "cloud storage", "dropbox", "google drive",
            "onedrive", "sharepoint", "print", "large volume", "sensitive data",
            "pii", "phi", "gdpr", "hipaa", "confidential", "intellectual property",
            "source code", "customer list", "export", "archive", "zip bomb"]

DETECTORS = [
    (["usb", "removable", "thumb drive", "flash drive"], "usb_transfer", 25,
     "Removable media used — check device control logs & device serial."),
    (["dlp", "data loss prevention"], "dlp_trigger", 20,
     "DLP policy triggered — validate policy match fidelity & data classification."),
    (["dropbox", "google drive", "onedrive", "mega.nz", "transfer.sh"], "cloud_upload", 25,
     "Personal cloud storage upload — common exfil path, block & review history."),
    (["large volume", "bulk download", "mass download", "gb of", "tb of"], "bulk_volume", 25,
     "Bulk data movement — compare against baseline for user & department."),
    (["pii", "phi", "gdpr", "hipaa", "customer data", "credit card"], "regulated_data", 30,
     "Regulated/personal data involved — privacy office & legal notification SLAs apply."),
    (["resign", "notice period", "leaving", "termination", "last day"], "departing_user", 20,
     "Departing employee — heightened insider risk window; preserve mailbox & files."),
    (["source code", "intellectual property", "trade secret", "cad files"], "ip_theft", 30,
     "IP-related data — legal privilege may apply, engage counsel early."),
    (["print", "printing"], "printing", 10,
     "Printing of sensitive material — low-tech but real exfil path."),
    (["encrypt", "password protect", "7z", "rar with password"], "encrypted_archive", 20,
     "Encrypted archive — defeats DLP content inspection; treat as high suspicion."),
]


def analyze(text, iocs, context):
    low = (text or "").lower()
    hits = []
    risk = 0
    for kws, key, pts, note in DETECTORS:
        if any(kw in low for kw in kws):
            hits.append({"key": key, "points": pts, "note": note})
            risk += pts
    return {
        "exfiltration": {
            "hits": hits,
            "risk_score": min(risk, 100),
        }
    }


def respond(text, iocs, analysis, context):
    e = analysis.get("exfiltration", {})
    if not e or not e.get("hits"):
        return ""
    lines = ["**Data Exfiltration & Insider Risk**"]
    for h in e["hits"]:
        lines.append(f"- 📤 {h['note']}")
    lines.append("- Actions: preserve logs (cas/audit), suspend share links, engage HR/Legal if insider suspected, "
                 "scope by data classification.")
    lines.append(f"- Exfiltration risk score: **{e.get('risk_score', 0)}/100**")
    return "\n".join(lines)


def report_section(analysis):
    e = analysis.get("exfiltration")
    if not e or not e.get("hits"):
        return None
    rows = "".join(
        f"<tr><td class='k'>{h['key'].replace('_', ' ').title()}</td><td>{h['note']}</td></tr>"
        for h in e.get("hits", [])
    )
    rows += f"<tr><td class='k'>Exfiltration risk</td><td><b>{e.get('risk_score', 0)}/100</b></td></tr>"
    return {"title": "Data Exfiltration & Insider Risk", "html": f"<table>{rows}</table>"}
