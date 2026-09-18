"""Unit tests for the evaluator."""

from __future__ import annotations

import pytest

from hardening_checker.core.evaluator import Evaluator
from hardening_checker.core.exceptions import CheckExecutionError
from hardening_checker.core.models import ResultStatus


@pytest.fixture
def ev(fake_ctx):
    return Evaluator(fake_ctx)


def test_registry_exact_pass(ev, sample_rule):
    rule = sample_rule({"kind": "registry", "hive": "HKLM",
                        "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                        "value": "FilterAdministratorToken",
                        "expected_kind": "exact", "expected": 1})
    status, msg, observed, expected, evd = ev.evaluate(rule)
    assert status is ResultStatus.PASS
    assert observed == 1
    assert evd and evd[0].source == "registry"


def test_registry_fail_when_mismatch(ev, sample_rule):
    rule = sample_rule({"kind": "registry", "hive": "HKLM",
                        "path": r"SYSTEM\CurrentControlSet\Control\Lsa",
                        "value": "RunAsPPL",
                        "expected_kind": "exact", "expected": 0})
    status, msg, *_ = ev.evaluate(rule)
    assert status is ResultStatus.FAIL


def test_registry_missing_value_maps_to_error_not_crash(ev, sample_rule):
    rule = sample_rule({"kind": "registry", "hive": "HKLM", "path": "NOPE", "value": "X",
                        "expected_kind": "exact", "expected": 1})
    status, *_ = ev.evaluate(rule)
    assert status is ResultStatus.FAIL  # observed None -> compare fails


def test_allow_missing_not_applicable(ev, sample_rule):
    rule = sample_rule({"kind": "registry", "hive": "HKLM", "path": "NOPE", "value": "X",
                        "expected_kind": "exact", "expected": 1,
                        "allow_missing": True})
    status, msg, *_ = ev.evaluate(rule)
    assert status is ResultStatus.NOT_APPLICABLE


def test_net_accounts_regex_pass(ev, sample_rule):
    rule = sample_rule({"kind": "command", "capture": "stdout",
                        "command": ["net", "accounts"],
                        "expected_kind": "regex",
                        "expected": r"Minimum password length\s*:?\s*14"})
    status, *_ = ev.evaluate(rule)
    assert status is ResultStatus.PASS


def test_bool_comparison(ev, sample_rule):
    rule = sample_rule({"kind": "powershell", "script": "Get-BitLockerVolume",
                        "as_bool": True, "expected_kind": "equals_bool",
                        "expected": True})
    status, *_ = ev.evaluate(rule)
    assert status is ResultStatus.PASS


def test_min_max_numeric(ev, sample_rule):
    rule = sample_rule({"kind": "file_content", "path": "f.txt",
                        "expected_kind": "min", "expected": 5})
    # observed "" -> non-numeric -> fail with message
    status, msg, *_ = ev.evaluate(rule)
    assert status is ResultStatus.FAIL


def test_unknown_kind_raises(ev, sample_rule):
    rule = sample_rule({"kind": "does_not_exist"})
    with pytest.raises(CheckExecutionError):
        ev.evaluate(rule)


def test_unknown_expected_kind_raises(ev, sample_rule):
    rule = sample_rule({"kind": "registry", "hive": "HKLM",
                        "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                        "value": "FilterAdministratorToken",
                        "expected_kind": "bogus", "expected": 1})
    with pytest.raises(CheckExecutionError):
        ev.evaluate(rule)


def test_service_status_check(ev, sample_rule):
    rule = sample_rule({"kind": "service", "service": "WinDefend",
                        "expected_kind": "exact", "expected": "Running"})
    status, *_ = ev.evaluate(rule)
    assert status is ResultStatus.PASS


def test_file_content_exists(ev, fake_ctx, sample_rule):
    fake_ctx._files["c.txt"] = "hello world\n"
    rule = sample_rule({"kind": "file_content", "path": "c.txt",
                        "pattern": r"hello",
                        "expected_kind": "exists", "expected": None})
    status, *_ = ev.evaluate(rule)
    assert status is ResultStatus.PASS
