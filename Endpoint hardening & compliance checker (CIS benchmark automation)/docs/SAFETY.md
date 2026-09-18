# Safety Model

The checker is an **auditor, not an agent**. This document enumerates every
way it touches the system and the guarantees that make it safe to run on
production endpoints.

## Guarantees

1. **No writes to the registry.** All registry access uses
   `winreg.OpenKey(..., KEY_READ | KEY_WOW64_64KEY)` and `QueryValueEx`.
   There is no `SetValue`, `CreateKey`, or `DeleteKey` anywhere in the codebase.
2. **No state-changing commands.** Every executed command is an inspection:
   - `net accounts` (read policy)
   - `auditpol /get /category:*` (read audit policy)
   - `powershell -NoProfile -NonInteractive -Command "Get-…"` read-only cmdlets
     (`Get-MpComputerStatus`, `Get-BitLockerVolume`, `Get-Service`,
     `Get-LocalGroupMember`, `Get-CimInstance`)
   - Linux/macOS: `sshd -T`, `sysctl -n`, `systemctl is-active`, `spctl --status`,
     `fdesetup status`, `ufw status`
3. **No file writes outside your chosen report locations.** The only files the
   app creates are the reports/exports you explicitly save.
4. **No services, tasks, or policies modified.** No `Set-Service`, no
   `schtasks`, no `secedit /configure`, no `reg add`.
5. **No network transmission.** Scans are local. The only socket activity is a
   UDP connect() probe to enumerate the host's own IP address.
6. **Remediation is display-only.** Suggested fix scripts are rendered as text
   in the GUI and reports. They are never executed by the application.

## Elevation

The app runs fine **non-elevated**. Rules that require admin (e.g. reading
certain protected keys or listing local admins) are reported as `SKIPPED`
with a clear message — they never silently fail, and skipping never distorts
the score (excluded from the denominator).

## Data handling

- Results contain configuration state only (registry values, service states,
  command output). No user documents, browsing history, or credentials.
- Command output is truncated to 2,000 characters per evidence blob.
- Everything stays on disk where you save it; nothing is uploaded.

## Threat model for the tool itself

- **Tampering:** the tool is read-only, so compromising it cannot directly
  weaken the host. Still, distribute signed builds.
- **False sense of security:** a scan reflects the moment it ran. Schedule
  recurring scans (CLI + Task Scheduler) for continuous posture tracking.
- **Score gaming:** scoring weights are code, not configuration — review
  changes to `SEVERITY_WEIGHTS` in pull requests.

## Verifying the claims

- Read `hardening_checker/core/contexts.py` — every primitive is read-only.
- Run `python -m pytest tests/ -q` — the suite asserts evaluator behavior
  against a fake context without touching the OS.
- Process monitor (ProcMon) a scan: you will see registry *reads*, command
  launches, and writes only to the report path you chose.
