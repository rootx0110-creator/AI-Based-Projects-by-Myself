"""Verdict fusion: combines heuristic risk with optional LLM verdict."""

from __future__ import annotations

from dataclasses import dataclass

from .heuristic import HeuristicScore

VERDICTS = ("safe", "suspicious", "phishing")


def _llm_risk(verdict: str, confidence: int) -> float:
    """Map an LLM verdict+confidence into a 0-100 risk value."""
    c = max(0, min(100, confidence))
    if verdict == "phishing":
        return 55 + c * 0.45
    if verdict == "safe":
        return c * 0.35
    return 30 + c * 0.4


@dataclass
class ScanResult:
    analysis_id: str
    verdict: str
    risk: int
    confidence: float
    reasons: list[str]
    tactics: list[str]
    evidence: list[dict]
    heuristic: dict
    llm: dict | None
    email: dict
    scanned_at: str
    suggested_action: str

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "verdict": self.verdict,
            "risk": self.risk,
            "confidence": round(self.confidence, 1),
            "reasons": self.reasons,
            "tactics": self.tactics,
            "evidence": self.evidence,
            "heuristic": self.heuristic,
            "llm": self.llm,
            "email": self.email,
            "scanned_at": self.scanned_at,
            "suggested_action": self.suggested_action,
        }


def fuse(analysis_id: str, heuristic: HeuristicScore,
         llm_result: dict | None, email: dict, scanned_at: str) -> ScanResult:
    heur_risk = float(heuristic.risk)
    heur_verdict = heuristic.verdict

    reasons = [e["detail"] for e in heuristic.evidence]
    tactics: list[str] = []
    llm_used = llm_result is not None and "error" not in llm_result
    llm_note: dict | None = llm_result

    if llm_used:
        for r in (llm_result.get("reasons") or []):
            if str(r) not in reasons:
                reasons.append(str(r))
        tactics = [str(t) for t in (llm_result.get("tactics") or []) if str(t)]
        llm_risk = _llm_risk(llm_result["verdict"], llm_result["confidence"])

        # Blended risk: heuristics dominate when very high/low,
        # otherwise LLM pulls the needle toward its assessment.
        if heur_risk >= 70:
            risk = heur_risk * 0.75 + llm_risk * 0.25
        elif heur_risk <= 25:
            risk = heur_risk * 0.7 + llm_risk * 0.3
        else:
            risk = heur_risk * 0.55 + llm_risk * 0.45
    else:
        risk = heur_risk
        if llm_result and "error" in llm_result:
            llm_note = {"error": llm_result["error"], "failed": True}
        else:
            llm_note = None

    risk = int(round(max(0.0, min(100.0, risk))))

    if risk >= 70:
        verdict = "phishing"
    elif risk >= 35:
        verdict = "suspicious"
    else:
        verdict = "safe"

    if not reasons:
        reasons = ["No strong phishing signals detected in this message."]

    confidence = _confidence_from(risk)

    suggested = ""
    if llm_used:
        suggested = str(llm_result.get("suggested_action") or "")
    if not suggested:
        if verdict == "phishing":
            suggested = "Do not click links or open attachments. Delete the message and report it to your security team."
        elif verdict == "suspicious":
            suggested = "Cross-check the sender address with the organization and contact them on a known channel before acting."
        else:
            suggested = "No action required, but stay alert to lookalike sender domains."

    return ScanResult(
        analysis_id=analysis_id,
        verdict=verdict,
        risk=risk,
        confidence=confidence,
        reasons=reasons,
        tactics=tactics,
        evidence=heuristic.evidence,
        heuristic=heuristic.to_dict(),
        llm=llm_note,
        email=email,
        scanned_at=scanned_at,
        suggested_action=suggested,
    )


def _confidence_from(risk: int) -> float:
    """Confidence loosely reflects how far the risk sits from decision
    boundaries, giving a softer number inside the suspicious band."""
    if risk >= 70:
        return min(99.0, 70.0 + (risk - 70) * 0.7)
    if risk <= 35:
        return min(99.0, 70.0 + (35 - risk) * 0.7)
    # suspicious band: lowest confidence near the midpoint
    band = 35 <= risk <= 70
    center = 52.5
    if band:
        return max(30.0, 65.0 - abs(risk - center) * 1.0)
    return 50.0