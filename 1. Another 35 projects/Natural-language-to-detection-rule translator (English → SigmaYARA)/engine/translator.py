# =============================================================================
#  Translator orchestration
#
#  Ties the full pipeline together:
#    text -> entity extraction -> concept detection -> sigma & yara -> results
# =============================================================================
import re
from datetime import date

from .concepts import (ConceptHits, coverage_ratio, detect_concepts,
                       resolve_logsource, summarize_hits)
from .entities import extract_entities, summarize
from .sigma import build_sigma
from .yara import build_yara


def translate(text, created=None):
    """Translate a natural-language description into Sigma + YARA rules.

    Returns a dict suited for JSON serialization.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Please describe the behavior you want to detect.")

    # guard against silly-length input
    if len(text) > 8000:
        text = text[:8000]

    entities = extract_entities(text)
    hits = detect_concepts(text, entities)

    sigma = build_sigma(text, entities, hits, created=created)
    yara = build_yara(text, entities, hits, created=created)

    confidence = coverage_ratio(hits, entities, text)

    concepts = summarize_hits(hits)
    mitre = [{"id": tid, "name": name, "score": node["score"]}
             for tid, name, node in _techniques(hits)]

    words = resolve_logsource(hits, entities)

    return {
        "input": text,
        "confidence": confidence,
        "confidence_pct": round(confidence * 100),
        "logsource": words,
        "level": _level(hits),
        "entities_summary": summarize(entities),
        "entities_count": entities.count(),
        "concepts": concepts,
        "mitre": mitre,
        "sigma": sigma.to_yaml(),
        "sigma_meta": sigma.to_dict(),
        "yara": yara,
        "generated_at": _now(),
        "version": "1.0.0",
    }


def _techniques(hits):
    """Iterator of (tactic_name, technique, node) after scoring."""
    items = sorted(hits.mitre.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for tid, node in items:
        yield tid, node["name"], node


def _level(hits):
    from .lexicon import DETECTION_CONCEPTS
    level = "medium"
    for h in hits.hits:
        lvl = DETECTION_CONCEPTS.get(h["concept"], {}).get("severity", "medium")
        if lvl == "critical":
            return "critical"
        if lvl == "high":
            level = "high"
    return level


def _now():
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


VALIDATE_RE = re.compile(r"^\s*\S", re.MULTILINE)


def looks_like_rule(text):
    """Cheap heuristic: did the user paste a YAML/YARA rule instead?"""
    low = text.lower()
    if low.startswith(("rule ", "yara", "import \"", "include \"")):
        return True
    if "detection:" in low and "logsource:" in low:
        return True
    return False