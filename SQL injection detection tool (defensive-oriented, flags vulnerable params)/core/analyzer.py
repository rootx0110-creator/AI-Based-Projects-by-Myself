"""Detection + scoring engine.

Runs offline (side-effect free) analysis on parameter observations and, when a
LiveScanner is supplied, augments findings with confirmed behavioural probes.
"""

import json
import re
import time

from . import payloads as P
from . import parser as PAR
from .scanner import LiveScanner, ScannerError


# contribution (0..100) per confirmed technique ---------------------------------
TECH_WEIGHTS = {
    "signature": 30,
    "pattern": 18,
    "error_signature": 38,
    "keyword_density": 20,
    "meta_character": 8,
    "boolean_blind": 42,
    "boolean_eq": 16,
    "time_based": 50,
    "stacked_queries": 28,
    "dbms_fingerprint": 14,
    "encoding_obfuscation": 7,
    "unreachable": 0,
}
MAX_TECH_CONTRIB = {"keyword_density": 20}


def _matches(regex, text):
    m = regex.search(text)
    return (m.group(0) if m else None)


def analyze_value(value, location="query"):
    """Score a single observed parameter value offline.

    Returns (score, techniques, dbms_hints, evidence).
    techniques is a list of dicts: {key, label, evidence, weight, confidence}
    """
    if value is None:
        value = ""
    text = str(value)

    low = text.lower()
    techniques = []
    dbms_hints = set()
    seen = set()

    def add(key, evidence, confidence=1.0):
        if key in seen:
            return
        seen.add(key)
        techniques.append({
            "key": key,
            "label": P.TECHNIQUE_LABELS.get(key, key),
            "evidence": (evidence or "")[:220],
            "weight": TECH_WEIGHTS.get(key, 10),
            "confidence": round(confidence, 2),
        })

    # --- signature hits from canonical payload library ----------------------
    for bucket, probers in P.PAYLOADS.items():
        for probe in probers:
            probe_l = probe.lower()
            if probe_l in low or probe_l.replace(" ", "") in low.replace(" ", ""):
                add("signature", "canonical %s payload present: %s" % (bucket, probe))
                break

    # --- syntax patterns ----------------------------------------------------
    probes_map = (
        ("union_select", "UNION-based output attempt"),
        ("error_based", "error-based function injection"),
        ("boolean_eq", "boolean tautology comparison"),
        ("time_mysql", "MySQL SLEEP() probe"),
        ("time_pg", "PostgreSQL pg_sleep probe"),
        ("time_mssql", "MSSQL WAITFOR DELAY probe"),
        ("time_benchmark", "MySQL BENCHMARK timing probe"),
        ("stacked", "stacked queries via semicolon"),
        ("injection_probe", "quote breakout with SQL keyword"),
        ("quote_breakout", "quoted/string breakout pattern"),
        ("sys_schema", "system schema reference"),
        ("version_probe", "DBMS version function call"),
        ("cast_probe", "CAST/CONVERT type-confusion"),
        ("ascii_probe", "ASCII/CHAR blind extraction"),
        ("hex_encoded", "hex-encoded bytes (obfuscation)"),
    )
    for key, label in probes_map:
        ev = _matches(P.PATTERNS[key], text)
        if ev:
            add(key, "%s: %s" % (label, ev))

    # --- comment styles ------------------------------------------------------
    ev = _matches(P.PATTERNS["comment_sql"], text)
    if ev:
        add("pattern", "in-band SQL comment (-- ): " + ev)
    if P.PATTERNS["comment_block"].search(text):
        add("pattern", "block comment /*..*/")
    if P.PATTERNS["comment_hash"].search(text):
        add("pattern", "hash comment (#)")

    # --- keyword density ------------------------------------------------------
    density = 0
    kw_hits = []
    lowered = low
    for kw, weight in P.KEYWORD_WEIGHTS.items():
        if re.search(r"\b" + re.escape(kw).replace(r"\ ", r"\s+") + r"\b", lowered):
            density += weight
            kw_hits.append(kw)
            if len(kw_hits) >= 4:
                break
    if density >= 3:
        add("keyword_density",
            "heavy SQL vocabulary (%d token hits: %s)" %
            (len(kw_hits), ", ".join(kw_hits[:5])),
            min(1.0, 0.4 + density * 0.04))

    # --- meta characters -------------------------------------------------------
    meta_present = [c for c in P.META_CHARS if c in text]
    if meta_present and (density >= 2 or "'" in meta_present or ";" in meta_present):
        add("meta_character", "meta characters %s in a risky context"
            % ", ".join(meta_present[:5]))

    # --- error signatures in captured text -------------------------------------
    for dbms, sigs in P.ERROR_SIGNATURES.items():
        for sig in sigs:
            if re.search(sig, text, re.I):
                add("error_signature", "%s error text captured" % dbms)
                dbms_hints.add(dbms)
                break

    # --- DBMS fingerprint ------------------------------------------------------
    for dbms, kws in P.DBMS_KEYWORDS.items():
        for kw in kws:
            if kw in lowered or kw.replace(" ", "") in lowered.replace(" ", ""):
                add("dbms_fingerprint", "%s artefact '%s'" % (dbms, kw))
                dbms_hints.add(dbms)
                break
    if "union select" in lowered:
        dbms_hints.add("generic")

    # --- double encoding --------------------------------------------------------
    if "%2527" in text.replace("'", "%27").lower() or "%25" in lowered:
        add("encoding_obfuscation", "double-encoded payload")

    score = _score_from_techniques(techniques, len(text))
    return score, techniques, sorted(dbms_hints), len(seen)


def _score_from_techniques(techniques, length):
    disposed = {}
    total = 0
    for t in techniques:
        cap = MAX_TECH_CONTRIB.get(t["key"], None)
        if cap is not None:
            disposed[t["key"]] = min(cap, disposed.get(t["key"], 0) + t["weight"])
        else:
            disposed[t["key"]] = disposed.get(t["key"], 0) + t["weight"]
    for v in disposed.values():
        total += v
    return min(100, total)


# ---------------------------------------------------------------------------
# Target-level orchestration
# ---------------------------------------------------------------------------
def analyze_target(target, live=None, settings=None):
    """Run detection over one target. Returns a serializable result dict."""
    settings = settings or {}
    start = time.time()
    params = target.get("params", {}) or {}
    findings = []
    unreachable_any = False

    param_items = []
    for name, values in params.items():
        if not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            param_items.append((name, "" if value is None else str(value)))

    for name, value in param_items:
        location = _locate(target, name)
        score, techniques, dbms_hints, _count = analyze_value(value, location)

        # --- live confirmation ---------------------------------------------
        live_rows = []
        if live is not None and not name.startswith("__"):
            try:
                typed = _probe_param(live, target, name, value)
                for key, ev, conf in typed:
                    if key == "unreachable":
                        unreachable_any = True
                        continue
                    row = {
                        "key": key,
                        "label": P.TECHNIQUE_LABELS.get(key, key),
                        "evidence": ev,
                        "weight": TECH_WEIGHTS.get(key, 10),
                        "confidence": conf,
                        "live": True,
                    }
                    live_rows.append(row)
            except ScannerError as exc:
                unreachable_any = True
                live_rows.append({
                    "key": "unreachable", "label": "Scanner error", "evidence": str(exc),
                    "weight": 0, "confidence": 0.0, "live": True,
                })

        combined = techniques + live_rows
        final_score = min(100, _score_from_techniques(combined, len(value)))
        level = P.risk_level(final_score)
        all_dbms = sorted(set(dbms_hints) | set(typed_rows_dbms(live_rows)))

        findings.append({
            "name": name,
            "location": location,
            "value": _preview(value),
            "score": final_score,
            "risk": level,
            "dbms": all_dbms,
            "techniques": combined,
            "flagged": level in ("High", "Critical"),
            "recommendation": _recommendation(level, combined),
        })

    findings.sort(key=lambda f: f["score"], reverse=True)

    target_score = max((f["score"] for f in findings), default=0)
    target_risk = P.risk_level(target_score)
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Safe": 0}
    for f in findings:
        counts[f["risk"]] += 1

    return {
        "url": target.get("url", "unknown"),
        "host": target.get("host", ""),
        "path": target.get("path", ""),
        "method": target.get("method", "GET"),
        "source": target.get("source", "url"),
        "duration_ms": int((time.time() - start) * 1000),
        "param_count": len(findings),
        "score": target_score,
        "risk": target_risk,
        "counts": counts,
        "flagged_params": [f["name"] for f in findings if f["flagged"]],
        "vulnerable": target_risk in ("High", "Critical"),
        "findings": findings,
    }


def _probe_param(live, target, name, value):
    try:
        return live.probe_parameter(target, name, value)
    except ScannerError:
        return [("unreachable", "probe budget exceeded", 0.0)]


def typed_rows_dbms(rows):
    rows_dms = []
    for r in rows:
        if r["key"] in ("time_based", "error_signature"):
            rows_dms.append(_dbms_of(r))
    return rows_dms


def _dbms_of(row):
    ev = row.get("evidence", "")
    if "pg_sleep" in ev or "postgres" in ev:
        return "postgres"
    if "waitfor" in ev or "mssql" in ev:
        return "mssql"
    if "extractvalue" in ev or "mysql" in ev:
        return "mysql"
    return "unknown"


def _locate(target, name):
    if name.startswith("cookie:"):
        return "cookie"
    if name == "__cookie__":
        return "cookie"
    return "query"  # analyzer currently folds body/query into one param namespace


def _preview(value, n=120):
    value = str(value)
    return value if len(value) <= n else value[:n] + "..."


def _recommendation(level, techs):
    keys = {t["key"] for t in techs}
    if level in ("High", "Critical"):
        if "time_based" in keys:
            return "Parameter appears injectable via time-based blind technique. "
        if "error_signature" in keys:
            return "Parameter reflects DBMS errors - likely injectable and verbose. "
        if "boolean_blind" in keys:
            return "Parameter responses differ between true/false conditions. "
        return "High suspicion of injection. Validate with a manual review."
    return "Review and harden with parameterized queries and input validation."


# ---------------------------------------------------------------------------
# Whole-run orchestration
# ---------------------------------------------------------------------------
def run_scan(data, mode="url", live_settings=None, settings=None):
    """Top-level entry point: parse -> analyze (+optional live probe)."""
    targets = PAR.build_targets(mode, data)
    live_settings = live_settings or {}
    scanner = None
    if live_settings.get("enabled"):
        scanner = LiveScanner(
            timeout=live_settings.get("timeout", 8.0),
            post_delay_ms=live_settings.get("delay_ms", 0),
            consent=live_settings.get("consent", False),
        )

    results = []
    for t in targets:
        results.append(analyze_target(t, live=scanner, settings=settings))

    critical = sum(1 for r in results if r["risk"] == "Critical")
    high = sum(1 for r in results if r["risk"] == "High")
    vuln = sum(1 for r in results if r["vulnerable"])
    total_params = sum(r["param_count"] for r in results)

    overall_score = max((r["score"] for r in results), default=0)
    summary = {
        "targets": len(results),
        "total_params": total_params,
        "vulnerable": vuln,
        "critical": critical,
        "high": high,
        "overall_score": overall_score,
        "overall_risk": P.risk_level(overall_score),
        "mode": mode,
        "live": bool(scanner),
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return {"summary": summary, "targets": results}