"""Tunable risk scoring for incidents (0-100)."""

from .defaults import SEVERITY_WEIGHT


def score_incident(incident, iocs, settings=None):
    weights = (settings or {}).get("risk_weights") or {}
    w = {
        "severity": float(weights.get("severity", 0.35)),
        "ti_verdict": float(weights.get("ti_verdict", 0.30)),
        "ioc_count": float(weights.get("ioc_count", 0.15)),
        "critical_asset": float(weights.get("critical_asset", 0.10)),
        "ransom_index": float(weights.get("ransom_index", 0.10)),
    }

    sev = SEVERITY_WEIGHT.get(incident.get("severity", "medium"), 50) / 100.0

    ti = 0.0
    if iocs:
        verdicts = [i.get("threat_verdict") for i in iocs]
        if "malicious" in verdicts:
            ti = 0.9
        elif "suspicious" in verdicts:
            ti = 0.6
        elif "ransomware" in verdicts:
            ti = 1.0

    ioc_f = min(len(iocs) / 5.0, 1.0)

    asset = 0.0
    asset_name = (incident.get("context") or {}).get("host", "") or ""
    if incident.get("impacted_asset"):
        asset = 0.3
    if any(k in asset_name.upper() for k in ("DC", "DB-", "SAP", "MAIL", "GATEWAY")):
        asset = 0.7

    ransom = 0.0
    type_hint = (incident.get("type") or "") + (incident.get("title") or "").lower()
    if "ransom" in type_hint or incident.get("context", {}).get("extension"):
        ransom = 0.85

    score = int(round(100 * (
        w["severity"] * sev +
        w["ti_verdict"] * ti +
        w["ioc_count"] * ioc_f +
        w["critical_asset"] * asset +
        w["ransom_index"] * ransom
    )))
    return max(0, min(100, score))