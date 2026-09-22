"""Business-logic services: catalog assembly, scoring, gap analysis, mapping."""

import datetime

from . import store
from .data import (
    BBICT_DOMAINS,
    BBICT_TO_ISO,
    BBICT_TO_NIST,
    FRAMEWORKS,
    ISO27001_CONTROLS,
    NIST_CSF_CATEGORIES,
    STATUS_SCORES,
    STATUSES,
)


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _iso_catalog():
    return [
        {"id": cid, "title": title, "theme": theme, "framework": "iso27001", "description": ""}
        for cid, title, theme in ISO27001_CONTROLS
    ]


def _bb_catalog():
    return [
        {"id": bid, "title": title, "theme": "Domain", "framework": "bbict", "description": desc}
        for bid, title, desc in BBICT_DOMAINS
    ]


def _nist_catalog():
    out = []
    for cat_id, name, parent, desc in NIST_CSF_CATEGORIES:
        if parent is None:  # function header rows are not assessable controls
            continue
        out.append({
            "id": cat_id,
            "title": name,
            "theme": parent,
            "framework": "nistcsf",
            "description": desc,
        })
    return out


def get_catalog():
    cat = _iso_catalog() + _bb_catalog() + _nist_catalog()
    state = store.load_all()
    entries = state["entries"]
    for item in cat:
        key = f"{item['framework']}::{item['id']}"
        entry = entries.get(key, {})
        item["status"] = entry.get("status", "")
        item["owner"] = entry.get("owner", "")
        item["notes"] = entry.get("notes", "")
        item["evidence"] = entry.get("evidence", "")
        item["updated"] = entry.get("updated", "")
    return cat


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_catalog(cat=None):
    """Per-framework compliance percentage. 'Not Applicable' is excluded."""
    cat = cat or get_catalog()
    scores = {}
    for fw in FRAMEWORKS:
        items = [c for c in cat if c["framework"] == fw]
        total = 0.0
        counted = 0
        for c in items:
            s = STATUS_SCORES.get(c["status"])
            if s is None and c["status"] == "Not Applicable":
                continue  # excluded from denominator
            counted += 1
            total += s if s is not None else 0.0
        scores[fw] = {
            "score": round(100.0 * total / counted, 1) if counted else 0.0,
            "implemented": sum(1 for c in items if c["status"] == "Implemented"),
            "partial": sum(1 for c in items if c["status"] == "Partially Implemented"),
            "planned": sum(1 for c in items if c["status"] == "Planned"),
            "not_implemented": sum(1 for c in items if c["status"] == "Not Implemented"),
            "not_applicable": sum(1 for c in items if c["status"] == "Not Applicable"),
            "total": len(items),
            "assessed": counted,
        }
    return scores


def maturity_level(pct):
    if pct >= 90:
        return {"level": 5, "label": "Optimized"}
    if pct >= 75:
        return {"level": 4, "label": "Managed"}
    if pct >= 55:
        return {"level": 3, "label": "Defined"}
    if pct >= 30:
        return {"level": 2, "label": "Developing"}
    return {"level": 1, "label": "Initial"}


def dashboard_summary():
    cat = get_catalog()
    scores = score_catalog(cat)
    out = {"frameworks": {}, "overall": {}}
    total_score = 0.0
    for fw, meta in FRAMEWORKS.items():
        s = scores[fw]
        m = maturity_level(s["score"])
        out["frameworks"][fw] = {**meta, **s, "maturity": m}
        total_score += s["score"]
    out["overall"]["score"] = round(total_score / len(FRAMEWORKS), 1)
    out["overall"]["maturity"] = maturity_level(out["overall"]["score"])
    out["organization"] = store.load_all().get("organization", "")
    out["generated_at"] = _now()
    out["statuses"] = STATUSES
    return out


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------

def compute_gaps(min_score=0.5):
    """Controls not Implemented (and not N/A) become prioritized findings."""
    cat = get_catalog()
    weights = {"Not Implemented": 3.0, "Planned": 2.0, "Partially Implemented": 1.0}
    gaps = []
    for c in cat:
        if c["status"] in ("Implemented", "Not Applicable", ""):
            continue
        w = weights.get(c["status"], 1.0)
        # Higher weight for technological controls that regulators care about
        theme_boost = 1.15 if c["theme"] in ("Technological",) else 1.0
        risk = round(min(10.0, w * 2.2 * theme_boost), 1)
        gaps.append({
            "framework": c["framework"],
            "framework_name": FRAMEWORKS[c["framework"]]["short"],
            "id": c["id"],
            "title": c["title"],
            "theme": c["theme"],
            "status": c["status"],
            "owner": c["owner"],
            "notes": c["notes"],
            "risk": risk,
            "recommendation": _recommendation(c),
        })
    gaps.sort(key=lambda g: (-g["risk"], g["framework"], g["id"]))
    return gaps


def _recommendation(c):
    fw = c["framework"]
    if fw == "iso27001":
        return (
            f"Close the gap for {c['id']} ({c['title']}): assign an owner, define an "
            f"implementation plan with target date, and collect evidence (policy, log, "
            f"report or screenshot) suitable for Annex A audit."
        )
    if fw == "bbict":
        return (
            f"Remediate {c['id']} ({c['title']}) to align with Bangladesh Bank ICT "
            f"Guideline expectations; document evidence for regulator inspection."
        )
    return (
        f"Advance {c['id']} ({c['title']}) to the target tier under NIST CSF 2.0 "
        f"{c['theme']} function."
    )


def save_findings(findings):
    clean = []
    for f in findings:
        clean.append({
            "framework": f.get("framework", ""),
            "id": f.get("id", ""),
            "title": f.get("title", ""),
            "status": f.get("status", ""),
            "owner": f.get("owner", ""),
            "risk": f.get("risk", 0),
            "recommendation": f.get("recommendation", ""),
        })
    store.set_findings(clean)
    return {"saved": len(clean)}


# ---------------------------------------------------------------------------
# Cross-mapping / heatmap
# ---------------------------------------------------------------------------

def control_mapper(framework, control_id):
    """Map one control to equivalent controls in the other frameworks.

    BB ICT domains are the bridge: ISO <-> NIST mappings go via the domains
    that reference them, keeping the crosswalk auditable.
    """
    if framework == "bbict":
        bb = [control_id]
        iso = BBICT_TO_ISO.get(control_id, [])
        nist = BBICT_TO_NIST.get(control_id, [])
    elif framework == "iso27001":
        bb = [bid for bid, iso_ids in BBICT_TO_ISO.items() if control_id in iso_ids]
        iso = [control_id]
        nist = sorted({n for b in bb for n in BBICT_TO_NIST.get(b, [])})
    else:  # nistcsf
        bb = [bid for bid, cats in BBICT_TO_NIST.items() if control_id in cats]
        iso = sorted({i for b in bb for i in BBICT_TO_ISO.get(b, [])})
        nist = [control_id]
    cat = {c["framework"] + "::" + c["id"]: c for c in get_catalog()}
    return {
        "source": cat.get(f"{framework}::{control_id}"),
        "iso27001": [cat["iso27001::" + i] for i in iso if "iso27001::" + i in cat],
        "bbict": [cat["bbict::" + b] for b in bb if "bbict::" + b in cat],
        "nistcsf": [cat["nistcsf::" + n] for n in nist if "nistcsf::" + n in cat],
    }


def coverage_matrix():
    """Matrix rows = BB domains; columns = framework coverage counts."""
    rows = []
    for bid, title, _desc in BBICT_DOMAINS:
        iso_ids = BBICT_TO_ISO.get(bid, [])
        nist_ids = BBICT_TO_NIST.get(bid, [])
        rows.append({
            "id": bid,
            "title": title,
            "iso": len(iso_ids),
            "nist": len(nist_ids),
            "iso_ids": iso_ids,
            "nist_ids": nist_ids,
        })
    return rows
