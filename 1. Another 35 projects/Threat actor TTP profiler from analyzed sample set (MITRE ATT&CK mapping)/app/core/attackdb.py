"""MITRE ATT&CK mapping engine.

Combines static-analysis evidence (API imports, strings, DLL usage, PE traits
and YARA hits) into a weighted set of detected techniques.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from .model import SampleResult, TechniqueHit
from .tactics import TACTIC_ORDER

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

_ANSI_SUFFIX = re.compile(r"^(.*?)[aw]$", re.IGNORECASE)


def normalize_api(name: str) -> str:
    """Normalize an imported function name for matching.

    Strips the ANSI/Unicode A/W suffix and lowercases.
    """
    n = name.split("#")[0].split("@")[0].strip().lower()
    base = n.rstrip("aw")
    if len(base) >= 4:
        return base
    return n


def norm_apiset(names: List[str]) -> set:
    out = set()
    for n in names:
        norm = normalize_api(n)
        if norm:
            out.add(norm)
        out.add(n.lower())
    return out


class AttackDb:
    """Loads technique metadata + rules and performs matching."""

    def __init__(self, techniques_path: Optional[str] = None, rules_path: Optional[str] = None):
        techs, rules = self._load(
            techniques_path or os.path.join(DATA_DIR, "attack_techniques.json"),
            rules_path or os.path.join(DATA_DIR, "technique_rules.json"),
        )
        self.techniques: Dict[str, dict] = techs
        self.rules: Dict[str, dict] = rules
        self.children: Dict[str, List[str]] = {}
        for tid, rule in rules.items():
            parent = rule.get("parent_id")
            if parent:
                self.children.setdefault(parent, []).append(tid)

    # ------------------------------------------------------------------
    @staticmethod
    def _load(tech_path: str, rule_path: str):
        with open(tech_path, "r", encoding="utf-8") as fh:
            techs = json.load(fh)
        with open(rule_path, "r", encoding="utf-8") as fh:
            rules = json.load(fh)
        return techs, rules

    def tactic_order(self) -> List[str]:
        return TACTIC_ORDER

    # ------------------------------------------------------------------
    def match(self, sample: SampleResult) -> List[TechniqueHit]:
        """Match a single sample; returns detected technique hits."""
        apis = norm_apiset(sample.imports)
        strings_lc = [s.lower() for s in sample.strings]
        dlls_lc = {d.lower() for d in sample.dlls}
        yara_names = [r.lower() for r in sample.yara_hits]

        hits: Dict[str, TechniqueHit] = {}

        for tid, rule in self.rules.items():
            evidence: List[str] = []
            score = 0.0
            categories: set = set()

            # ---- API imports
            for a in rule.get("api", []):
                a_l = a.lower()
                if any(a_l in api for api in apis):
                    evidence.append("API: %s" % a)
                    score += 20
                    categories.add("api")
            # ---- strings
            for s in rule.get("strings", []):
                pat = s.lower()
                if pat.startswith("re:"):
                    try:
                        rx = re.compile(pat[3:], re.IGNORECASE)
                        matched = any(rx.search(st) for st in sample.strings)
                    except re.error:
                        matched = False
                else:
                    matched = any(pat in st for st in strings_lc)
                if matched:
                    specific = len(pat) >= 16
                    evidence.append('String: "%s"%s' % (s[:60], " (specific)" if specific else ""))
                    score += 16 if specific else 13
                    categories.add("string")
            # ---- dll usage
            for d in rule.get("dll", []):
                if d.lower() in dlls_lc:
                    evidence.append("Imports %s" % d)
                    score += 10
                    categories.add("dll")
            # ---- PE traits
            for trait, value in (rule.get("pe") or {}).items():
                if self._pe_trait_match(trait, value, sample):
                    evidence.append("PE trait: %s=%s" % (trait, value))
                    score += {}.get(trait, 26 if trait == "packer" else 22)
                    categories.add("pe")
            # ---- YARA hit names
            for y in rule.get("yara", []):
                if any(y.lower() in n for n in yara_names):
                    evidence.append("YARA rule *%s*" % y)
                    score += 30
                    categories.add("yara")

            if not evidence:
                continue

            if len(categories) >= 2 and score < 100:
                score += 10
            elif len(evidence) >= 3:
                score += 6
            confidence = min(95.0, score)
            if confidence < 20:
                continue

            meta = self.techniques.get(tid, {})
            hit = TechniqueHit(
                technique_id=tid,
                name=rule.get("name") or meta.get("name", tid),
                tactics=rule.get("tactics") or [meta.get("tactic", "unknown")],
                confidence=round(confidence, 1),
                weight=rule.get("weight", 1.0),
                evidence=list(dict.fromkeys(evidence)),
            )
            hits[tid] = hit

        return self._prune_superfluous(hits)

    @staticmethod
    def _pe_trait_match(trait: str, value, sample: SampleResult) -> bool:
        if trait == "packer":
            if value == "*":
                return bool(sample.packer)
            return bool(sample.packer) and value.lower() in sample.packer.lower()
        if trait == "entropy_min":
            try:
                return sample.entropy >= float(value)
            except (TypeError, ValueError):
                return False
        return False

    def _prune_superfluous(self, hits: Dict[str, TechniqueHit]) -> List[TechniqueHit]:
        """If a sub-technique was detected with the same evidence as its parent,
        drop the parent to avoid double counting."""
        detected = set(hits)
        for parent_id, kids in self.children.items():
            if parent_id not in detected:
                continue
            found_kids = [k for k in kids if k in detected]
            if not found_kids:
                continue
            parent_evidence = set(hits[parent_id].evidence)
            kid_evidence = set()
            for k in found_kids:
                kid_evidence.update(hits[k].evidence)
            if parent_evidence.issubset(kid_evidence):
                del hits[parent_id]
            elif parent_evidence == kid_evidence:
                del hits[parent_id]
        return sorted(hits.values(), key=lambda h: (-h.confidence, h.technique_id))