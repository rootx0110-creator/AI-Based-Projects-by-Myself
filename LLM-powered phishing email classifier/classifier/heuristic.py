"""Deterministic heuristic scoring of extracted evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class HeuristicScore:
    risk: int            # 0-100
    verdict: str         # safe | suspicious | phishing
    points: float
    evidence: list[dict]

    def to_dict(self) -> dict:
        return {"risk": self.risk, "verdict": self.verdict,
                "points": self.points, "evidence": self.evidence}


def _verdict_for(risk: int) -> str:
    if risk >= 70:
        return "phishing"
    if risk >= 35:
        return "suspicious"
    return "safe"


def score(evidence: list[dict]) -> HeuristicScore:
    flagged = [e for e in evidence if e["points"] > 0]
    points = round(sum(e["points"] for e in flagged), 1)

    # Exponential saturation: an abundance of strong signals converges to
    # ~100 while a handful of weak ones stays well inside safe/suspicious.
    lam = 48.0
    risk = int(round(100.0 * (1.0 - math.exp(-points / lam))))
    return HeuristicScore(risk=max(0, min(100, risk)), verdict=_verdict_for(risk),
                          points=points, evidence=sorted(flagged,
                                                         key=lambda e: -e["points"]))