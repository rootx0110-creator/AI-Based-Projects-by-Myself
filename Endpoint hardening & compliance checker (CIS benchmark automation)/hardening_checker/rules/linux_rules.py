"""Linux rule set (optional platform support).

Rules run only when the scanner is invoked on Linux. Checks rely on standard
tools (sshd -T, sysctl, systemctl) and are read-only.
"""

from __future__ import annotations

from hardening_checker.core.models import Profile, Remediation, Rule, Severity


def _r(rule_id, title, severity, category, spec, *, description="", rationale="",
       remediation_summary="", steps=None, script="", profile=Profile.L1,
       manual=False, refs=None, tags=None, audit_hint=""):
    return Rule(
        rule_id=rule_id,
        title=title,
        description=description or title,
        severity=severity,
        profile=profile,
        category=category,
        check_spec=spec,
        remediation=Remediation(
            summary=remediation_summary or title,
            steps=steps or [],
            script=script,
            script_shell="bash" if script else "",
        ),
        rationale=rationale,
        refs=refs or [],
        manual=manual,
        platforms=("linux",),
        tags=tags or [],
        audit_hint=audit_hint,
    )


def get_rules() -> list[Rule]:
    rules: list[Rule] = []

    rules += [
        _r(
            "HC-LNX-0001", "SSH: X11 forwarding disabled",
            Severity.MEDIUM, "SSH Server",
            {"kind": "command", "capture": "stdout",
             "command": ["sshd", "-T"],
             "expected_kind": "in", "expected": "x11forwarding no",
             "fail_message": "sshd_config allows X11 forwarding.",
             "audit_hint": "sshd -T dumps the effective config."},
            remediation_summary="Set 'X11Forwarding no' in sshd_config.",
            script="sed -i 's/^#\\?X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config",
            refs=["CIS 5.2.x (L1)"],
        ),
        _r(
            "HC-LNX-0002", "SSH: MaxAuthTries 4 or fewer",
            Severity.MEDIUM, "SSH Server",
            {"kind": "command", "capture": "stdout",
             "command": ["sshd", "-T"],
             "expected_kind": "regex", "expected": r"maxauthtries\s+[0-4]\b",
             "fail_message": "MaxAuthTries is above 4.",
             "audit_hint": "Lower attempt counts slow brute force."},
            remediation_summary="Set MaxAuthTries 4 or fewer.",
            script="sed -i 's/^#\\?MaxAuthTries.*/MaxAuthTries 4/' /etc/ssh/sshd_config",
            refs=["CIS 5.2.x (L1)"],
        ),
        _r(
            "HC-LNX-0003", "SSH: root login prohibited",
            Severity.HIGH, "SSH Server",
            {"kind": "command", "capture": "stdout",
             "command": ["sshd", "-T"],
             "expected_kind": "in", "expected": "permitrootlogin no",
             "fail_message": "Direct root SSH login is permitted.",
             "audit_hint": "'permitrootlogin no' forces named accounts."},
            remediation_summary="Set PermitRootLogin no.",
            script="sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config",
            refs=["CIS 5.2.x (L1)"],
        ),
        _r(
            "HC-LNX-0004", "IPv4 ICMP redirects not accepted",
            Severity.MEDIUM, "Network",
            {"kind": "command", "capture": "stdout",
             "command": ["sysctl", "-n", "net.ipv4.conf.all.accept_redirects"],
             "expected_kind": "exact", "expected": "0",
             "fail_message": "ICMP redirects are accepted.",
             "audit_hint": "sysctl value must be 0 on all interfaces."},
            remediation_summary="Disable ICMP redirect acceptance.",
            script="sysctl -w net.ipv4.conf.all.accept_redirects=0",
            refs=["CIS 3.x (L1)"],
        ),
        _r(
            "HC-LNX-0005", "IPv4 reverse path filtering enabled",
            Severity.MEDIUM, "Network",
            {"kind": "command", "capture": "stdout",
             "command": ["sysctl", "-n", "net.ipv4.conf.all.rp_filter"],
             "expected_kind": "exact", "expected": "1",
             "fail_message": "Reverse path filtering is disabled.",
             "audit_hint": "rp_filter=1 drops martian packets."},
            remediation_summary="Enable reverse path filtering.",
            script="sysctl -w net.ipv4.conf.all.rp_filter=1",
            refs=["CIS 3.x (L1)"],
        ),
        _r(
            "HC-LNX-0006", "Core dumps restricted",
            Severity.LOW, "System",
            {"kind": "file_content",
             "path": "/etc/security/limits.conf",
             "pattern": r"^\s*\*\s+hard\s+core\s+0\s*$",
             "expected_kind": "exists", "expected": None,
             "fail_message": "limits.conf does not disable core dumps.",
             "audit_hint": "A '* hard core 0' line must exist."},
            remediation_summary="Add '* hard core 0' to limits.conf.",
            script="echo '* hard core 0' >> /etc/security/limits.conf",
            refs=["CIS 1.x (L1)"],
        ),
        _r(
            "HC-LNX-0007", "Audit daemon (auditd) is running",
            Severity.HIGH, "Audit",
            {"kind": "service", "service": "auditd",
             "expected_kind": "exact", "expected": "active",
             "fail_message": "auditd is not active.",
             "audit_hint": "systemctl is-active auditd should return 'active'."},
            remediation_summary="Enable and start auditd.",
            script="systemctl enable --now auditd",
            refs=["CIS 4.1.x (L2)"],
        ),
        _r(
            "HC-LNX-0008", "Manual: verify bootloader password",
            Severity.MEDIUM, "Boot",
            {"kind": "file_exists", "path": "/boot/grub2/user.cfg",
             "expected_kind": "exists", "expected": None,
             "fail_message": "GRUB user.cfg not found; verify manually.",
             "audit_hint": "Presence of user.cfg suggests a GRUB password is set."},
            manual=True,
            refs=["CIS 1.4.x (L1)"],
        ),
    ]
    return rules
