"""Tests for scoring, models, and rule integrity."""

from __future__ import annotations

from hardening_checker.core.models import (
    CheckResult,
    Profile,
    ResultStatus,
    ScanReport,
    ScanSummary,
    Severity,
)
from hardening_checker.core.scoring import compute_score, failing_by_severity
from hardening_checker.core.scanner import load_rules


def _res(sev: Severity, status: ResultStatus) -> CheckResult:
    from hardening_checker.core.models import Remediation, Rule

    rule = Rule(
        rule_id="X", title="t", description="d", severity=sev,
        profile=Profile.L1, category="c",
        check_spec={"kind": "registry", "hive": "HKLM", "path": "p", "value": "v",
                    "expected_kind": "exact", "expected": 1},
        remediation=Remediation(),
    )
    return CheckResult(rule=rule, status=status)


def test_score_full_pass():
    results = [_res(Severity.HIGH, ResultStatus.PASS),
               _res(Severity.MEDIUM, ResultStatus.PASS)]
    score, grade = compute_score(results)
    assert score == 100.0
    assert grade == "A+"


def test_score_mixed():
    results = [_res(Severity.CRITICAL, ResultStatus.FAIL),
               _res(Severity.LOW, ResultStatus.PASS)]
    score, grade = compute_score(results)
    # applicable = 10 + 1 = 11; achieved = 1 -> ~9.1%
    assert score < 15
    assert grade == "F"


def test_score_error_counts_half():
    results = [_res(Severity.HIGH, ResultStatus.ERROR)]
    score, _ = compute_score(results)
    assert score == 50.0


def test_na_excluded_from_denominator():
    results = [_res(Severity.HIGH, ResultStatus.NOT_APPLICABLE),
               _res(Severity.MEDIUM, ResultStatus.PASS)]
    score, grade = compute_score(results)
    assert score == 100.0 and grade == "A+"


def test_failing_by_severity_counts():
    results = [_res(Severity.HIGH, ResultStatus.FAIL),
               _res(Severity.HIGH, ResultStatus.PASS),
               _res(Severity.LOW, ResultStatus.FAIL)]
    counts = failing_by_severity(results)
    assert counts["high"] == 1 and counts["low"] == 1


def test_windows_rules_load_and_unique():
    rules = load_rules("windows")
    assert len(rules) >= 40
    ids = [r.rule_id for r in rules]
    assert len(ids) == len(set(ids)), "duplicate rule ids"
    for r in rules:
        assert r.severity in Severity
        assert r.profile in Profile
        assert r.check_spec.get("kind")


def test_linux_rules_load():
    rules = load_rules("linux")
    assert len(rules) >= 5


def test_macos_rules_load():
    rules = load_rules("macos")
    assert len(rules) >= 3


def test_summary_recompute():
    s = ScanSummary()
    results = [_res(Severity.HIGH, ResultStatus.PASS),
               _res(Severity.HIGH, ResultStatus.FAIL),
               _res(Severity.LOW, ResultStatus.NOT_APPLICABLE)]
    s.recompute(results)
    assert s.total == 3 and s.passed == 1 and s.failed == 1
    assert s.not_applicable == 1


def test_report_to_dict_json_safe():
    import json

    s = ScanSummary()
    results = [_res(Severity.MEDIUM, ResultStatus.PASS)]
    s.recompute(results)
    report = ScanReport(
        scan_id="TESTID", started_at="t0", finished_at="t1",
        profile="level_1",
        platform=type("P", (), {"to_dict": lambda self: {}})(),
        results=results, summary=s, score=99.0, grade="A+",
    )
    data = json.dumps(report.to_dict(), default=str)
    assert "TESTID" in data
