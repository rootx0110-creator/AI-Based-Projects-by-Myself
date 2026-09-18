class RiskScorer:
    """Aggregates weighted evidence into a 0-100 risk score and verdict."""

    VERDICT_LEVELS = [
        (0, 14, "SAFE"),
        (15, 39, "LOW RISK"),
        (40, 69, "MODERATE"),
        (70, 89, "HIGH RISK"),
        (90, 100, "CRITICAL"),
    ]

    COLORS = {
        "SAFE": "#2ecc71",
        "LOW RISK": "#f1c40f",
        "MODERATE": "#e67e22",
        "HIGH RISK": "#e74c3c",
        "CRITICAL": "#8e44ad",
    }

    def __init__(self, evidence: list):
        self.evidence = evidence or []

    # ------------------------------------------------------------------ #
    def score(self):
        total = sum(int(e.get("weight", 0)) for e in self.evidence)
        capped = min(100, total)
        return capped

    def verdict(self, score: int = None) -> str:
        s = self.score() if score is None else score
        for lo, hi, label in self.VERDICT_LEVELS:
            if lo <= s <= hi:
                return label
        return "SAFE"

    def color_for(self, verdict: str) -> str:
        return self.COLORS.get(verdict, "#95a5a6")

    # ------------------------------------------------------------------ #
    def breakdown(self) -> dict:
        s = self.score()
        return {
            "score": s,
            "verdict": self.verdict(s),
            "color": self.color_for(self.verdict(s)),
            "evidence_count": len(self.evidence),
            "evidence": self.evidence,
        }