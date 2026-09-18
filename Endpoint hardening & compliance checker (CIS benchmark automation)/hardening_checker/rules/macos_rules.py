"""macOS rule set (optional platform support, minimal set)."""

from __future__ import annotations

from hardening_checker.core.models import Profile, Remediation, Rule, Severity


def _r(rule_id, title, severity, category, spec, *, remediation_summary="",
       steps=None, script="", manual=False, refs=None, audit_hint=""):
    return Rule(
        rule_id=rule_id,
        title=title,
        description=title,
        severity=severity,
        profile=Profile.L1,
        category=category,
        check_spec=spec,
        remediation=Remediation(
            summary=remediation_summary or title,
            steps=steps or [],
            script=script,
            script_shell="bash" if script else "",
        ),
        refs=refs or [],
        manual=manual,
        platforms=("macos",),
        tags=[],
        audit_hint=audit_hint,
    )


def get_rules() -> list[Rule]:
    rules: list[Rule] = []

    rules += [
        _r(
            "HC-MAC-0001", "Gatekeeper is enabled",
            Severity.HIGH, "Gatekeeper",
            {"kind": "command", "capture": "stdout",
             "command": ["spctl", "--status"],
             "expected_kind": "in", "expected": "assessments enabled",
             "fail_message": "Gatekeeper assessment is disabled.",
             "audit_hint": "spctl --status prints assessment state."},
            remediation_summary="Enable Gatekeeper.",
            script="sudo spctl --master-enable",
            refs=["CIS 2.x (L1)"],
        ),
        _r(
            "HC-MAC-0002", "FileVault is on",
            Severity.CRITICAL, "FileVault",
            {"kind": "command", "capture": "stdout",
             "command": ["fdesetup", "status"],
             "expected_kind": "in", "expected": "On",
             "fail_message": "FileVault is not enabled.",
             "audit_hint": "fdesetup status prints 'FileVault is On' when active."},
            remediation_summary="Enable FileVault.",
            steps=["System Settings > Privacy & Security > FileVault > Turn On."],
            refs=["CIS 2.x (L1)"],
        ),
        _r(
            "HC-MAC-0003", "Firewall is on",
            Severity.HIGH, "Firewall",
            {"kind": "command", "capture": "stdout",
             "command": ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
             "expected_kind": "in", "expected": "enabled",
             "fail_message": "Application firewall is off.",
             "audit_hint": "socketfilterfw reports the global firewall state."},
            remediation_summary="Enable the application firewall.",
            script="sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on",
            refs=["CIS 3.x (L1)"],
        ),
        _r(
            "HC-MAC-0004", "Screen saver locks after 10 minutes or less",
            Severity.MEDIUM, "Session Lock",
            {"kind": "file_content",
             "path": "/Library/Preferences/com.apple.screensaver.plist",
             "pattern": r"askForPasswordDelay",
             "expected_kind": "exists", "expected": None,
             "fail_message": "Screensaver lock policy not found; verify manually.",
             "audit_hint": "Managed macs carry this key in the managed plist."},
            manual=True,
            refs=["CIS 5.x (L1)"],
        ),
    ]
    return rules
