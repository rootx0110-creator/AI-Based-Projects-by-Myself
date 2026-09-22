"""STRIDEForge threat analysis pipeline."""

from .rules import STRIDE, rules_for

RISK_TIERS = [("Critical", 40), ("High", 30), ("Medium", 18)]

FACTOR_NAMES = {
    "damage": "Damage",
    "reproducibility": "Reproducibility",
    "exploitability": "Exploitability",
    "affected_users": "Affected Users",
    "discoverability": "Discoverability",
}

FLAG_INCREMENT_NAMES = {
    "internet": "Internet-facing",
    "pii": "Contains PII",
    "pci": "Card / PCI data",
    "phi": "Health data (PHI)",
}

CONTROL_NOTES = {
    "authn": "Strong authentication",
    "authz": "Strict authorization",
    "encrypted": "Encryption in place",
    "logged": "Audit logging",
    "rate_limited": "Rate limiting",
}


def _clamp(v, lo=1, hi=10):
    return max(lo, min(hi, int(round(v))))


def _flags(el):
    return el.get("flags") or {}


def _eff_zone(el, boundaries):
    """Zone of the last boundary rectangle containing the element center."""
    x, y = el.get("x", 0), el.get("y", 0)
    w, h = el.get("w", 150), el.get("h", 70)
    cx, cy = x + w / 2.0, y + h / 2.0
    for b in boundaries or []:
        if b.get("x", 0) <= cx <= b.get("x", 0) + b.get("w", 0) and \
           b.get("y", 0) <= cy <= b.get("y", 0) + b.get("h", 0):
            return b.get("zone") or b.get("label") or "zone"
    return el.get("zone") or "default"


def _risk_total(d):
    return sum(int(d[k]) for k in FACTOR_NAMES)


def _tier(total):
    for name, threshold in RISK_TIERS:
        if total >= threshold:
            return name
    return "Low"


def apply_modifiers(base, element, flow=None, crossing=False, kind="process"):
    """Adjust base DREAD scores by context; return (scores, notes)."""
    d = dict(base)
    notes = []
    flags = _flags(element)

    # ---- risk raises ---------------------------------------------------
    if flags.get("internet"):
        d["exploitability"] = _clamp(d["exploitability"] + 2)
        d["discoverability"] = _clamp(d["discoverability"] + 2)
        d["affected_users"] = _clamp(d["affected_users"] + 1)
        notes.append("+2 exploit / +2 discover / +1 affected (internet-facing)")
    for f, label in FLAG_INCREMENT_NAMES.items():
        if flags.get(f):
            d["damage"] = _clamp(d["damage"] + 2)
            notes.append("+2 damage (%s)" % label)
    if crossing:
        d["damage"] = _clamp(d["damage"] + 1)
        d["affected_users"] = _clamp(d["affected_users"] + 1)
        notes.append("+1 damage / +1 affected (crosses trust boundary)")

    # ---- controls (residual risk) --------------------------------------
    if flags.get("authn"):
        d["exploitability"] = _clamp(d["exploitability"] - 2)
        d["discoverability"] = _clamp(d["discoverability"] - 1)
        notes.append("-2 exploit / -1 discover (strong authentication)")
    if flags.get("authz"):
        d["exploitability"] = _clamp(d["exploitability"] - 2)
        d["damage"] = _clamp(d["damage"] - 1)
        notes.append("-2 exploit / -1 damage (strict authorization)")
    if flags.get("encrypted"):
        d["damage"] = _clamp(d["damage"] - 1)
        d["exploitability"] = _clamp(d["exploitability"] - 2)
        notes.append("-1 damage / -2 exploit (encryption in place)")
    if flags.get("logged"):
        d["damage"] = _clamp(d["damage"] - 2)
        d["discoverability"] = _clamp(d["discoverability"] - 1)
        notes.append("-2 damage / -1 discover (audit logging)")
    if flags.get("rate_limited"):
        d["exploitability"] = _clamp(d["exploitability"] - 2)
        d["affected_users"] = _clamp(d["affected_users"] - 1)
        notes.append("-2 exploit / -1 affected (rate limiting)")

    return d, notes


def _element_threats(el, zones, boundaries):
    kind = el.get("kind")
    etype = el.get("type", "generic")
    label = el.get("label") or "Unnamed element"
    zone = zones.get(el.get("id"))
    threats = []
    for stride in STRIDE:
        for rule in rules_for(kind, etype, stride):
            scores, notes = apply_modifiers(
                rule["dread"], el,
                crossing=_is_flow_of_interest(el, zones, boundaries),
                kind=kind,
            )
            total = _risk_total(scores)
            threats.append({
                "id": None,  # assigned later
                "element_id": el.get("id"),
                "element_label": label,
                "element_kind": kind,
                "element_type": etype,
                "element_zone": zone,
                "stride": stride,
                "stride_name": STRIDE[stride],
                "title": rule["title"],
                "description": rule["description"],
                "mitigation": rule["mitigation"],
                "dread": scores,
                "dread_total": total,
                "risk": _tier(total),
                "context_notes": notes,
            })
    return threats


def _is_flow_of_interest(el, zones, boundaries):
    """Only flows matter for crossing detection; elements never 'cross'."""
    return False


def _flow_threats(flow, elements, zones):
    src = next((e for e in elements if e.get("id") == flow.get("source")), None)
    tgt = next((e for e in elements if e.get("id") == flow.get("target")), None)
    slabel = (src or {}).get("label") or flow.get("source") or "?"
    tlabel = (tgt or {}).get("label") or flow.get("target") or "?"
    label = "%s -> %s" % (slabel, tlabel)
    crossing = zones.get(flow.get("source")) != zones.get(flow.get("target"))
    flow_flags = {"encrypted": bool(flow.get("encrypted")),
                  "authenticated": bool(flow.get("authenticated"))}

    threats = []
    for stride in STRIDE:
        for rule in rules_for("data_flow", "any", stride):
            scores, notes = apply_modifiers(
                rule["dread"], flow,
                flow=_flow_proxy(flow, flow_flags),
                crossing=crossing,
                kind="data_flow",
            )
            # on transit threats, encryption specifically de-risks S/T/I
            if flow_flags["encrypted"] and stride in ("S", "T", "I"):
                scores["damage"] = _clamp(scores["damage"] - 1)
                scores["exploitability"] = _clamp(scores["exploitability"] - 1)
                notes.append("-1 damage / -1 exploit (TLS in transit)")
            if flow_flags["authenticated"] and stride == "S":
                scores["exploitability"] = _clamp(scores["exploitability"] - 1)
                notes.append("-1 exploit (flow authenticated)")
            total = _risk_total(scores)
            threats.append({
                "id": None,
                "element_id": flow.get("id"),
                "element_label": label,
                "element_kind": "data_flow",
                "element_type": "data_flow",
                "element_zone": "%s / %s" % (zones.get(flow.get("source")), zones.get(flow.get("target"))),
                "stride": stride,
                "stride_name": STRIDE[stride],
                "title": rule["title"],
                "description": rule["description"],
                "mitigation": rule["mitigation"],
                "dread": scores,
                "dread_total": total,
                "risk": _tier(total),
                "context_notes": notes,
            })
    return threats


def _flow_proxy(flow, flow_flags):
    """Present flow flags to apply_modifiers as element flags."""
    return {"id": flow.get("id"), "flags": flow_flags}


def analyze_architecture(model):
    """Full pipeline: returns {summary, threats, meta}."""
    model = model or {}
    elements = [e for e in (model.get("elements") or []) if isinstance(e, dict)]
    flows = [f for f in (model.get("flows") or []) if isinstance(f, dict)]
    boundaries = [b for b in (model.get("boundaries") or []) if isinstance(b, dict)]
    name = model.get("name") or "Untitled Architecture"

    by_id = {e.get("id"): e for e in elements}

    if not elements and not flows:
        return {
            "error": "Architecture is empty. Add at least one component or data flow.",
            "summary": None,
            "threats": [],
            "meta": {"name": name},
        }

    zones = {}
    for e in elements:
        zones[e.get("id")] = _eff_zone(e, boundaries)
    # flows source/target zones: default if element missing
    for f in flows:
        zones.setdefault(f.get("source"), zones.get(f.get("source")) or _eff_zone({"id": f.get("source")}, boundaries) or "default")
        zones.setdefault(f.get("target"), zones.get(f.get("target")) or _eff_zone({"id": f.get("target")}, boundaries) or "default")

    threats = []
    for e in elements:
        threats.extend(_element_threats(e, zones, boundaries))
    for f in flows:
        threats.extend(_flow_threats(f, elements, zones))

    threats.sort(key=lambda t: (-t["dread_total"], t["element_label"]))

    for i, t in enumerate(threats, 1):
        t["id"] = "T%03d" % i

    by_stride = {s: 0 for s in STRIDE}
    by_risk = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for t in threats:
        by_stride[t["stride"]] += 1
        by_risk[t["risk"]] += 1

    if by_risk["Critical"]:
        overall = "Critical"
    elif by_risk["High"]:
        overall = "High"
    elif by_risk["Medium"]:
        overall = "Medium"
    elif len(threats):
        overall = "Low"
    else:
        overall = "Low"

    avg = round(sum(t["dread_total"] for t in threats) / max(1, len(threats)), 1)

    recs = []
    for t in threats:
        if t["risk"] in ("Critical", "High"):
            m = t["mitigation"]
            if m not in recs:
                recs.append(m)
        if len(recs) >= 8:
            break

    summary = {
        "name": name,
        "total": len(threats),
        "by_stride": by_stride,
        "by_risk": by_risk,
        "overall": overall,
        "avg_dread": avg,
        "elements_analyzed": len(elements),
        "flows_analyzed": len(flows),
        "boundaries": len(boundaries),
        "recommendations": recs,
        "top_threats": [t["id"] for t in threats[:5]],
    }

    meta = {
        "name": name,
        "description": model.get("description") or "",
        "stride": [
            {"letter": s, "name": STRIDE[s]} for s in STRIDE
        ],
    }

    return {"summary": summary, "threats": threats, "meta": meta}