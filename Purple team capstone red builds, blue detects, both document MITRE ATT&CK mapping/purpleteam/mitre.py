"""MITRE ATT&CK / D3FEND registry for the purple team lab.

Two sides of the exercise share this single registry:

* ``RED_TECHNIQUES`` - techniques the red side can *build* (simulated in a
  sandboxed lab target; they never touch a real system).
* ``BLUE_RULES`` - detection rules the blue side can run; every rule maps to
  the ATT&CK techniques its *data sources* can observe (many-to-many, which is
  what makes the coverage matrix worth studying).

Each entry is plain data (frozen-friendly, dumpable to JSON) so the HTML
report and docs are generated from one source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class Technique:
    id: str                       # e.g. "T1053.005"
    name: str
    tactic: str
    tactics: tuple = ()           # some techniques span several tactics
    platform: str = "Windows"
    description: str = ""
    module: str = ""              # red module id that builds this technique
    build: str = ""               # short "what the attacker did"

    @property
    def tactic_list(self) -> tuple:
        return tuple(self.tactics) if self.tactics else (self.tactic,)


@dataclass(frozen=True)
class Rule:
    id: str                 # e.g. "RULE-PS-OBFUSCATION"
    name: str
    data_source: str        # MITRE data source, e.g. "Network Traffic"
    sigma: str              # example sigma-style query name
    detects: tuple = ()     # technique ids this rule can surface
    rationale: str = ""

    @property
    def technique_ids(self) -> tuple:
        return tuple(self.detects)


def _t(i, **kw):  # shorthand
    return Technique(id=i, **kw)


RED_TECHNIQUES: tuple[Technique, ...] = (
    _t(
        "T1053.005",
        name="Scheduled Task/Job: Scheduled Task",
        tactic="Persistence",
        tactics=("Persistence", "Execution", "Privilege Escalation"),
        platform="Windows",
        description="An attacker registers a scheduled task so malware runs at a chosen time "
                    "or event, surviving reboots and earning persistent execution.",
        module="sched_task",
        build="Dropped a scheduled-task definition (XML) into the lab task store and "
              "registered it in the job listing.",
    ),
    _t(
        "T1566.001",
        name="Phishing: Spearphishing Attachment",
        tactic="Initial Access",
        tactics=("Initial Access",),
        platform="Windows/Linux/macOS",
        description="A lure email carrying an Office document or archive with embedded macro "
                    "or downloader is delivered to a victim's download folder.",
        module="phish_attach",
        build="Placed a macro-laden Office/archive lure in the victim's lab download folder.",
    ),
    _t(
        "T1547.001",
        name="Boot or Logon Autostart: Registry Run Keys / Startup Folder",
        tactic="Persistence",
        tactics=("Persistence", "Privilege Escalation"),
        platform="Windows",
        description="Persistence via HKCU/HKLM ...\\Run key values or the Startup folder; "
                    "the payload runs automatically at logon.",
        module="run_key",
        build="Wrote a logon-autostart value (Run key) plus a Startup-folder shortcut marker.",
    ),
    _t(
        "T1059.001",
        name="PowerShell",
        tactic="Execution",
        tactics=("Execution",),
        platform="Windows",
        description="Adversaries abuse PowerShell for execution, discovery, persistence "
                    "and defense evasion.",
        module="powershell",
        build="Executed a simulated PowerShell command line captured to the PowerShell log.",
    ),
    _t(
        "T1027",
        name="Obfuscated Files or Information",
        tactic="Defense Evasion",
        tactics=("Defense Evasion",),
        platform="Windows/macOS/Linux",
        description="Payloads, commands or artifacts are encoded or obfuscated to evade "
                    "detection and harm analysis.",
        module="powershell",
        build="Launch and payload were buried in Base64/char-math obfuscation captured to log.",
    ),
    _t(
        "T1082",
        name="System Information Discovery",
        tactic="Discovery",
        tactics=("Discovery",),
        platform="Windows/macOS/Linux",
        description="The adversary collects host facts (name, OS, IP, users, patch level) "
                    "to shape the next step of the operation.",
        module="sysinfo",
        build="Ran a discovery sweep and wrote a recon report into the lab host.",
    ),
    _t(
        "T1105",
        name="Ingress Tool Transfer",
        tactic="Command and Control",
        tactics=("Command and Control",),
        platform="Windows/macOS/Linux",
        description="A second-stage utility or toolkit is transferred onto the victim over "
                    "the existing channel.",
        module="tool_drop",
        build="Pulled a tool binary into the lab tools store over the simulated channel.",
    ),
    _t(
        "T1036.005",
        name="Masquerading: Match Legitimate Name or Location",
        tactic="Defense Evasion",
        tactics=("Defense Evasion",),
        platform="Windows/macOS/Linux",
        description="A dropped binary is renamed to look like a trusted system process "
                    "(svchost.exe, lsass.exe, ping.exe...).",
        module="masquerade",
        build="Copied a legitimate-looking PE into a system folder under a trusted name.",
    ),
    _t(
        "T1041",
        name="Exfiltration Over C2 Channel",
        tactic="Exfiltration",
        tactics=("Exfiltration",),
        platform="Windows/macOS/Linux",
        description="Sensitive data is shipped out over the established command-and-control "
                    "path, riding the same channel a defender already watches.",
        module="c2_exfil",
        build="Streamed a secrets blob to the lab listener over the loopback C2 channel.",
    ),
    _t(
        "T1106",
        name="Native API",
        tactic="Execution",
        tactics=("Execution",),
        platform="Windows/macOS/Linux",
        description="Direct OS API calls (process creation, memory steering) are abused to "
                    "run code while staying under the tooling radar.",
        module="native_api",
        build="Issued simulated process-control API calls recorded in the native API log.",
    ),
)


BLUE_RULES: tuple[Rule, ...] = (
    Rule(
        id="RULE-SCHTASK",
        name="Scheduled Task Abuse / New Job",
        data_source="Windows Event Log (4698/4699) + File: Task Scheduler",
        sigma="win_susp_task_creation",
        detects=("T1053.005",),
        rationale="Authorized task creation is rare in the lab; a new job pointing at "
                  "scripts or downloads is a top-10 persistence signal.",
    ),
    Rule(
        id="RULE-DL-ATTACHMENT",
        name="Suspicious Attachment in Downloads",
        data_source="File",
        sigma="file_lure_office_archive",
        detects=("T1566.001",),
        rationale="Office/archive lures with macros arriving in a user download folder are "
                  "the classic initial-access artifact.",
    ),
    Rule(
        id="RULE-AUTOSTART",
        name="Logon Autostart / Run Key Change",
        data_source="Windows Registry",
        sigma="registry_run_key_modification",
        detects=("T1547.001",),
        rationale="New HKCU Run values and Startup shortcuts rarely appear during normal use; "
                  "immediate persistence candidate.",
    ),
    Rule(
        id="RULE-PS-OBFUSC",
        name="Obfuscated PowerShell / Script Block Logging",
        data_source="PowerShell Script Block Logging (4104)",
        sigma="posh_pc_encoded",
        detects=("T1059.001", "T1027"),
        rationale="EncodedCommand and char-math obfuscation in PS log lines is high fidelity "
                  "for both execution and evasion.",
    ),
    Rule(
        id="RULE-DISCOVERY",
        name="System Discovery Sweep",
        data_source="Process + Command Execution",
        sigma="win_system_information_discovery",
        detects=("T1082",),
        rationale="Dense hostinfo-collection bursts (whoami, ipconfig, systeminfo...) in a row "
                  "predict recon → lateral movement.",
    ),
    Rule(
        id="RULE-TOOL-DROP",
        name="Unexpected Binary Drop / Masquerade",
        data_source="File + Process",
        sigma="win_dropped_known_binary",
        detects=("T1105", "T1036.005"),
        rationale="Fresh binaries in managed folders or trusted-name lookalikes are a "
                  "defense-evasion + C2 red flag.",
    ),
    Rule(
        id="RULE-EXFIL",
        name="High-Entropy Outbound Transfer on C2 Port",
        data_source="Network Traffic",
        sigma="net_high_entropy_c2_upload",
        detects=("T1041",),
        rationale="Base64/high-entropy bulk leaving the host on a non-standard local port is "
                  "the signature of an exfiltration burst.",
    ),
    Rule(
        id="RULE-API-CALL",
        name="Suspicious Native API Usage",
        data_source="Process API Monitoring",
        sigma="win_creation_spawn_chain",
        detects=("T1106",),
        rationale="Unusual process spawn/match chains and rapid API call density indicate "
                  "API-level execution.",
    ),
    Rule(
        id="RULE-CHANGE",
        name="Recent Suspicious File Creation (catch-all)",
        data_source="File",
        sigma="file_creation_suspicious_dir",
        detects=("T1053.005", "T1566.001", "T1547.001", "T1059.001", "T1027",
                 "T1082", "T1105", "T1036.005", "T1106"),
        rationale="Generic recency + sensitivity lens; catches techniques with no dedicated "
                  "rule to shrink blind spots.",
    ),
)


TECH_BY_ID: dict[str, Technique] = {t.id: t for t in RED_TECHNIQUES}
RULE_BY_ID: dict[str, Rule] = {r.id: r for r in BLUE_RULES}


def technique_ids() -> list[str]:
    return [t.id for t in RED_TECHNIQUES]


def rule_ids() -> list[str]:
    return [r.id for r in BLUE_RULES]


def rules_for_technique(tid: str) -> list[Rule]:
    return [r for r in BLUE_RULES if tid in r.detects]


def techniques_for_rule(rid: str) -> list[Technique]:
    rule = RULE_BY_ID[rid]
    return [TECH_BY_ID[t] for t in rule.detects if t in TECH_BY_ID]


def coverage_matrix(executed: list[str], findings: list[dict]) -> dict[str, dict[str, bool]]:
    """executed technique id -> {rule id: True when that rule fired for it}."""
    matrix: dict[str, dict[str, bool]] = {}
    for tid in executed:
        row: dict[str, bool] = {r.id: False for r in BLUE_RULES}
        for f in findings:
            if f.get("technique_id") == tid and f.get("rule_id"):
                row[f["rule_id"]] = True
        matrix[tid] = row
    return matrix


def detections_map() -> list[dict]:
    """Rule id -> list of technique ids it can detect (as plain data)."""
    return [{"rule": r.id, "techniques": list(r.detects)} for r in BLUE_RULES]


def as_dicts() -> dict[str, Any]:
    return {
        "techniques": [asdict(t) for t in RED_TECHNIQUES],
        "rules": [asdict(r) for r in BLUE_RULES],
        "detection_map": detections_map(),
    }