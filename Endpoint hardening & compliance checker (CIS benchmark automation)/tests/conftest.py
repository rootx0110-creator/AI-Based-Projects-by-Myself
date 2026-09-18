"""Shared test fixtures: fake platform context + sample rules."""

from __future__ import annotations

import pytest

from hardening_checker.core.contexts import PlatformContext
from hardening_checker.core.exceptions import CheckExecutionError
from hardening_checker.core.models import Profile, Remediation, Rule, Severity


class FakeContext(PlatformContext):
    """Deterministic in-memory context for unit tests (no OS calls)."""

    name = "windows"

    def __init__(self, registry=None, files=None, services=None, admin=True):
        self._registry = {
            k.upper(): v for k, v in (registry or {}).items()
        }
        self._files = files or {}
        self._services = services or {}
        self._admin = admin

    def platform_info(self):
        from hardening_checker.core.models import PlatformInfo

        info = PlatformInfo(system="Windows", hostname="TEST-BOX")
        info.os_name = "Windows"
        info.os_version = "11"
        info.is_admin = self._admin
        return info

    # registry ----------------------------------------------------------
    def registry_value(self, hive, path, value):
        key = f"{hive}\\{path}\\{value}".upper()
        return self._registry.get(key)  # None when absent, like real winreg

    def registry_key_exists(self, hive, path):
        prefix = f"{hive}\\{path}".upper() + "\\"
        return any(k.startswith(prefix) for k in self._registry)

    # files -------------------------------------------------------------
    def file_exists(self, path):
        return path in self._files

    def read_file_text(self, path, max_bytes=1_000_000):
        if path not in self._files:
            raise CheckExecutionError(f"file not found: {path}")
        return self._files[path]

    # services ----------------------------------------------------------
    def service_status(self, service_name):
        return self._services.get(service_name)

    # commands ----------------------------------------------------------
    def run_command(self, command, timeout=15.0, shell=False):
        if command[:2] == ["net", "accounts"]:
            return 0, (
                "The command completed successfully.\n\n"
                "Computer name:                       TEST-BOX\n"
                "Minimum password length:             14\n"
                "Maximum password age (days):         90\n"
                "Minimum password age (days):         1\n"
                "Password history length:             24\n"
                "Lockout threshold:                   5\n"
                "Lockout duration (minutes):          15\n"
                "Lockout observation window (minutes): 15\n"
                "Password complexity:                 Enabled\n"
            ), ""
        raise CheckExecutionError(f"unexpected command: {command}")

    def run_powershell(self, script, timeout=30.0):
        if "Get-BitLockerVolume" in script:
            return 0, "True", ""
        if "Get-MpComputerStatus" in script and "RealTime" in script:
            return 0, "True", ""
        return 0, "", ""


@pytest.fixture
def fake_ctx():
    return FakeContext(
        registry={
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\FilterAdministratorToken": 1,
            r"HKLM\SYSTEM\CurrentControlSet\Control\Lsa\RunAsPPL": 1,
        },
        services={"WinDefend": "Running"},
    )


@pytest.fixture
def sample_rule():
    def make(spec=None, **overrides):
        defaults = dict(
            rule_id="HC-TEST-0001",
            title="Test rule",
            description="A rule used in tests",
            severity=Severity.HIGH,
            profile=Profile.L1,
            category="Testing",
            check_spec=spec or {"kind": "registry", "hive": "HKLM",
                                "path": "SOFTWARE\\X", "value": "Y",
                                "expected_kind": "exact", "expected": 1},
            remediation=Remediation(summary="fix it"),
        )
        defaults.update(overrides)
        return Rule(**defaults)
    return make
