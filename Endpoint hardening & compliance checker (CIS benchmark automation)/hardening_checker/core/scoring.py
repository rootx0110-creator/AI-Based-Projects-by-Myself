"""Weighted compliance scoring from scan results."""

from __future__ import annotations

from .models import CheckResult, ResultStatus, Severity, SEVERITY_WEIGHTS

# Grades mapped from final score percentage.
GRADE_BANDS: tuple[tuple[float, str], ...] = (
    (95.0, "A+"),
    (90.0, "A"),
    (80.0, "B"),
    (70.0, "C"),
    (60.0, "D"),
    (50.0, "E"),
    (0.0, "F"),
)


def compute_score(results: list[CheckResult]) -> tuple[float, str]:
    """Return (score_percent, grade).

    Score = achieved weight / applicable weight, where:
      * PASS contributes its full severity weight
      * FAIL contributes 0
      * ERROR contributes half weight (unknown, not counted against the host)
      * NOT_APPLICABLE / SKIPPED / MANUAL are excluded from the denominator
    """
    achieved = 0.0
    applicable = 0.0

    for res in results:
        weight = SEVERITY_WEIGHTS[res.severity]
        if weight <= 0:
            continue
        if res.status in (ResultStatus.NOT_APPLICABLE, ResultStatus.SKIPPED, ResultStatus.MANUAL):
            continue
        applicable += weight
        if res.status is ResultStatus.PASS:
            achieved += weight
        elif res.status is ResultStatus.ERROR:
            achieved += weight * 0.5

    if applicable <= 0:
        return 0.0, "F"
    score = max(0.0, min(100.0, achieved / applicable * 100.0))
    grade = next(g for floor, g in GRADE_BANDS if score >= floor)
    return score, grade


def failing_by_severity(results: list[CheckResult]) -> dict[str, int]:
    counts: dict[str, int] = {s.value: 0 for s in Severity}
    for res in results:
        if res.status is ResultStatus.FAIL:
            counts[res.severity.value] += 1
    return counts


__all__ = ["compute_score", "failing_by_severity", "GRADE_BANDS"]
