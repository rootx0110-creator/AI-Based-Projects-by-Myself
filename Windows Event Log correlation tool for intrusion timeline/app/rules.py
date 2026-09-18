"""MITRE ATT&CK detection rules for the correlation engine.

A rule has an evaluator that takes a RuleContext and returns a list of
matches as dicts: '{'events': [...], 'summary': str}'.

Evaluator kinds implemented:
  * single        - each matching event becomes its own alert (capped)
  * excess        - group events by a key attr; flag if N matches in a window
  * sequence      - flag event B if a matching trigger event A happened before
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from .models import Rule, Severity
from .parser import ParseCanceled

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class RuleContext:
    """State shared with rule evaluators."""

    def __init__(self, events: List):
        self.events = events
        self.by_id: Dict[int, List] = defaultdict(list)
        self.canceled = False
        for e in events:
            self.by_id[e.event_id].append(e)

    def check_canceled(self):
        if self.canceled:
            raise ParseCanceled("Analysis canceled by user.")


def get(e, *names: str) -> str:
    for n in names:
        v = e.data.get(n)
        if v:
            return v
    return ""


def _key(e, names: Tuple[str, ...]) -> str:
    val = get(e, *names) or "?"
    return val.strip().lower()


def _collect_grouped(
    ctx: RuleContext,
    event_ids: List[int],
    key_names: Tuple[str, ...],
    win_seconds: float,
    min_count: int,
    max_groups: int = 50,
    per_group_cap: Optional[int] = None,
    matcher=None,
) -> List[Dict]:
    """Group candidate events by key; return groups with >= min_count inside
    a sliding window whose most recent activity is within win_seconds."""
    groups: Dict[str, List] = defaultdict(list)
    seen = set()
    for eid in event_ids:
        for e in ctx.by_id.get(eid, []):
            if matcher is not None and not matcher(e):
                continue
            key = _key(e, key_names)
            if key in ("?", "none", "-"):
                continue
            if hash((key, e.record_id, e.timestamp)) in seen:
                continue
            seen.add(hash((key, e.record_id, e.timestamp)))
            groups[key].append(e)

    results: List[Dict] = []
    for key, evs in groups.items():
        if len(results) >= max_groups:
            break
        evs.sort(key=lambda e: e.timestamp)
        # last min_count events must fit inside the window
        tail = evs[-min_count:] if len(evs) >= min_count else evs
        if len(tail) < min_count:
            continue
        span = (tail[-1].timestamp - tail[0].timestamp).total_seconds()
        if span <= win_seconds:
            payload = evs[:per_group_cap] if per_group_cap else evs
            results.append({"events": payload, "key": key, "count": len(evs)})
    return results


def _seq_match(
    ctx: RuleContext,
    trigger_ids: List[int],
    follow_ids: List[int],
    key_names: Tuple[str, ...],
    window_seconds: float,
    max_matches: int = 40,
) -> List[Dict]:
    """Find pairs: a trigger event (by id) followed by a follow event sharing
    the same key within window_seconds. One match per follow event, capped."""
    follows_by_key: Dict[str, List] = defaultdict(list)
    for eid in follow_ids:
        for e in ctx.by_id.get(eid, []):
            k = _key(e, key_names)
            if k in ("?", "none", "-"):
                continue
            follows_by_key[k].append(e)

    found: List[Dict] = []
    triggers = []
    for eid in trigger_ids:
        triggers += ctx.by_id.get(eid, [])
    triggers.sort(key=lambda e: e.timestamp)

    for e in triggers:
        k = _key(e, key_names)
        if k not in follows_by_key:
            continue
        fts = [f for f in follows_by_key[k]
               if 0 <= (f.timestamp - e.timestamp).total_seconds() <= window_seconds]
        if fts:
            fts.sort(key=lambda f: f.timestamp)
            hit = fts[0]
            if hit.record_id not in {x.record_id for x in found}:
                found.append({"events": [e, hit], "summary": f"{k}: trigger->follow"})
            if len(found) >= max_matches:
                break
    return found


# --------------------------------------------------------------------------- #
# Evaluator constructors
# --------------------------------------------------------------------------- #


def excess_rule(
    event_ids: List[int],
    key_names: Tuple[str, ...],
    win_seconds: float,
    min_count: int,
    max_groups: int = 50,
    per_group_cap: Optional[int] = None,
    matcher=None,
):
    def _eval(ctx: RuleContext) -> List[Dict]:
        return _collect_grouped(
            ctx, event_ids, key_names, win_seconds, min_count,
            max_groups=max_groups, per_group_cap=per_group_cap, matcher=matcher,
        )
    return _eval


def seq_rule(
    trigger_ids: List[int],
    follow_ids: List[int],
    key_names: Tuple[str, ...],
    window_seconds: float,
    max_matches: int = 40,
):
    def _eval(ctx: RuleContext) -> List[Dict]:
        return _seq_match(ctx, trigger_ids, follow_ids, key_names, window_seconds, max_matches)
    return _eval


def single_rule(event_id: int, matcher=None, cap: int = 40):
    """matcher(e) -> bool ; if None, match all events with this id."""
    def _eval(ctx: RuleContext) -> List[Dict]:
        out = []
        evs = list(ctx.by_id.get(event_id, []))
        evs.sort(key=lambda e: e.timestamp)
        for e in evs:
            if matcher is not None and not matcher(e):
                continue
            out.append({"events": [e]})
            if len(out) >= cap:
                break
        return out
    return _eval


# --------------------------------------------------------------------------- #
# Specialized matchers
# --------------------------------------------------------------------------- #

_ENC_PW = re.compile(r"(-enc|-en|encodedcom| -e | /e )", re.I)
_LSASS = re.compile(r"lsass", re.I)
_WHITELIST_LSASS_PROC = {"svchost.exe", "wininit.exe", "csrss.exe", "lsass.exe",
                         "services.exe", "system", ""}
_SAM = re.compile(r"(\\+config\\+(SAM|SYSTEM|SECURITY|SOFTWARE)\b|\\\\System32\\\\Config\\\\)", re.I)
_DEFENDER = re.compile(r"(Windows Defender|Defender|DisableAntiSpyware|DisableRealtimeMonitoring)", re.I)
_RUNKEYS = re.compile(r"CurrentVersion\\(RunOnce|RunServices|RunExt|Run)|"
                      r"StartupApproved|Shell\\(StartupApproved|Run|Bam)", re.I)
_STARTUP = re.compile(
    r"(Start Menu\\Programs\\Startup|AppData\\Roaming\\Microsoft\\Windows\\Start)",
    re.I,
)
_SCRIPTS = {"mshta.exe", "cscript.exe", "wscript.exe", "regsvr32.exe", "cmd.exe"}
_CERTUTIL = re.compile(r"certutil.*(-urlcache|urlcache.*)", re.I)
_MIMI = re.compile(r"(mimikatz|invoke-mimikatz|kerberoast|Get-KerberosTicket|"
                   r"downloadstring|DownloadString|new-object.*webclient|"
                   r"findstr.*reg svc|wmic process call create)", re.I)


def _is_4688(e):
    return e.event_id == 4688


def matcher_encoded_pw(e):
    if not _is_4688(e):
        return False
    proc = (e.get("NewProcessName") or "").lower()
    if not proc.endswith("powershell.exe") and not proc.endswith("pwsh.exe"):
        return False
    return bool(_ENC_PW.search(e.command_line or ""))


def matcher_lsass(e):
    if e.event_id not in (4656, 4663):
        return False
    obj = e.object_name or ""
    if not _LSASS.search(obj):
        return False
    proc = (e.get("ProcessName") or "").lower()
    return proc not in _WHITELIST_LSASS_PROC


def matcher_sam(e):
    if e.event_id not in (4656, 4663, 4690):
        return False
    return bool(_SAM.search(e.object_name or ""))


def matcher_kerberoast(e):
    if e.event_id != 4769:
        return False
    enc = (e.get("EncryptionType") or "")
    topt = (e.get("TicketOptions") or "")
    svc = (e.get("ServiceName") or "")
    if svc.endswith("$"):
        return False
    if enc and "0x17" not in enc.lower() and "18" not in enc:
        return False
    return "40810000" in topt


def matcher_dcsync(e):
    if e.event_id != 4662:
        return False
    am = (e.get("AccessMask") or "") + (e.get("AccessList") or "")
    return "ds-replication" in am.lower()


def matcher_anonymous(e):
    if e.event_id != 4624:
        return False
    if e.logon_type != "3":
        return False
    user = (e.get("TargetUserName") or e.get("SubjectUserName") or "")
    return user.upper() in ("ANONYMOUS LOGON", "ANONYMOUS")


def matcher_runkey(e):
    if e.event_id != 4657:
        return False
    return bool(_RUNKEYS.search(e.object_name or ""))


def matcher_startup(e):
    if e.event_id != 4663:
        return False
    obj = e.object_name or ""
    if not _STARTUP.search(obj):
        return False
    am = (e.get("AccessMask") or "")
    return "writedata" in (e.get("AccessList") or "").lower() or am in ("0x2", "0x6", "0x2\n")


def matcher_defender(e):
    if e.event_id != 4657:
        return False
    return bool(_DEFENDER.search(e.object_name or ""))


def matcher_certutil(e):
    if not _is_4688(e):
        return False
    cmd = e.command_line or ""
    return "certutil" in cmd.lower() and "-urlcache" in cmd.lower()


def matcher_lolbin(e):
    if not _is_4688(e):
        return False
    proc = (e.get("NewProcessName") or "").lower()
    if not proc:
        return False
    base = proc.rsplit("\\", 1)[-1]
    if base not in _SCRIPTS:
        return False
    cmd = e.command_line or ""
    if base == "mshta.exe" and "http" not in cmd.lower():
        return False
    return bool(_SCRIPTS) and any(s.lower() in cmd.lower() for s in ("http", "script", "/i:", "exec"))


def matcher_susp_psh(e):
    if e.event_id != 4104:
        return False
    script = e.get("ScriptBlockText") or e.data.get("Message") or ""
    return bool(_MIMI.search(script))


def matcher_admin_netlogon(e):
    if e.event_id != 4624:
        return False
    if e.logon_type != "3":
        return False
    user = (e.get("TargetUserName") or "")
    return user in ("administrator", "admin", "sa")


def matcher_rdp_anon(e):
    return e.event_id == 4624 and e.logon_type == "10"


def matcher_clearevent(e):
    return e.event_id == 1102


def matcher_preauth(e):
    if e.event_id != 4768:
        return False
    return (e.get("PreAuthType") or "") == "0"


def matcher_sedebug(e):
    if e.event_id != 4672:
        return False
    priv = (e.get("PrivilegeList") or e.get("AdditionalInformation") or "")
    return "sedebugprivilege" in priv.lower()


# --------------------------------------------------------------------------- #
# Rule set
# --------------------------------------------------------------------------- #

def build_rules() -> List[Rule]:
    return [
        # ---------- Initial Access / Bruteforce --------------------------- #
        Rule.make(
            "BRUTE_FORCE", "Account brute force",
            "Credential Access", "T1110.001", Severity.HIGH,
            "Repeated failed logons for a single account from one source in a short window.",
            excess_rule([4625], ("SourceNetworkAddress",), 60, 8, per_group_cap=60),
        ),
        Rule.make(
            "RDP_BRUTE_FORCE", "RDP brute force",
            "Initial Access", "T1110.001", Severity.HIGH,
            "Repeated failed interactive (RDP Type 10) logons packed in a short window.",
            excess_rule([4625], ("SourceNetworkAddress",), 120, 5,
                        matcher=lambda e: e.logon_type == "10", per_group_cap=60),
        ),
        Rule.make(
            "PASSWORD_SPRAY", "Password spray",
            "Credential Access", "T1110.003", Severity.HIGH,
            "Many distinct accounts attempted from the same source within a short window.",
            _spray_rule,
        ),
        Rule.make(
            "USER_ENUM", "Account user enumeration",
            "Discovery", "T1087.002", Severity.MEDIUM,
            "Large number of distinct usernames seen in failed logons from one IP.",
            _enum_rule,
        ),
        Rule.make(
            "LOCKOUT_BURST", "Account lockout burst",
            "Credential Access", "T1110", Severity.MEDIUM,
            "Several accounts locked out in quick succession.",
            excess_rule([4740], ("TargetUserName",), 300, 3, per_group_cap=30),
        ),
        Rule.make(
            "LOGON_AFTER_BRUTE", "Logon after brute force",
            "Initial Access", "T1110", Severity.CRITICAL,
            "A successful logon from an IP that had a brute-force pattern recently.",
            _logon_after_brute_rule,
        ),

        # ---------- Execution ---------------------------------------------- #
        Rule.make(
            "ENC_POWERSHELL", "Encoded PowerShell execution",
            "Execution", "T1059.001", Severity.CRITICAL,
            "PowerShell launched with an encoded command payload.",
            single_rule(4688, matcher_encoded_pw, cap=30),
        ),
        Rule.make(
            "SUSP_PSH", "Suspicious PowerShell script block",
            "Execution", "T1059.001", Severity.CRITICAL,
            "PowerShell script block referencing common post-exploitation tools.",
            single_rule(4104, matcher_susp_psh, cap=30),
        ),
        Rule.make(
            "CERTUTIL_DL", "CertUtil download",
            "Command and Control", "T1105", Severity.HIGH,
            "Certificate utility used to download a payload from the internet.",
            single_rule(4688, matcher_certutil, cap=20),
        ),
        Rule.make(
            "LOLBIN", "Living-off-the-land binary",
            "Execution", "T1218", Severity.MEDIUM,
            "Scripting / mshta / regsvr32 used with suspicious command line.",
            single_rule(4688, matcher_lolbin, cap=30),
        ),
        Rule.make(
            "PTH", "Credential relay indicator (4624 Type 3 + elevated)",
            "Credential Access", "T1550.002", Severity.MEDIUM,
            "Network logon with administrator account over SMB (potential relay).",
            single_rule(4624, matcher_pth, cap=25),
        ),

        # ---------- Persistence -------------------------------------------- #
        Rule.make(
            "NEW_SERVICE", "Service created",
            "Persistence", "T1543.003", Severity.MEDIUM,
            "A new Windows service was registered (possible persistence).",
            excess_rule([7045, 4697], ("ServiceName", "Service", "ServiceName"), 86400, 1, per_group_cap=5),
        ),
        Rule.make(
            "SCHED_TASK", "Scheduled task created",
            "Persistence", "T1053.005", Severity.MEDIUM,
            "A new scheduled task was created or enabled (possible persistence).",
            single_rule(4698, cap=40),
        ),
        Rule.make(
            "RUNKEY", "Registry Run key modified",
            "Persistence", "T1547.001", Severity.HIGH,
            "Autorun registry key (Run/RunOnce/StartupApproved) touched.",
            single_rule(4657, matcher_runkey, cap=40),
        ),
        Rule.make(
            "STARTUP_DIR", "Startup folder write",
            "Persistence", "T1547.001", Severity.HIGH,
            "A file was written to a Startup folder (persistence via autostart).",
            single_rule(4663, matcher_startup, cap=40),
        ),
        Rule.make(
            "DEFENSE_DISABLE", "Defender / security config modified",
            "Defense Evasion", "T1562.001", Severity.HIGH,
            "Effective security software configuration registry modified.",
            single_rule(4657, matcher_defender, cap=25),
        ),

        # ---------- Privilege Escalation ----------------------------------- #
        Rule.make(
            "SEDEBUG", "SeDebugPrivilege granted",
            "Privilege Escalation", "T1134.001", Severity.HIGH,
            "Session granted debug/impersonation privileges (token abuse).",
            single_rule(4672, matcher_sedebug, cap=30),
        ),
        Rule.make(
            "ELEV_TOKEN", "Elevated token logon",
            "Privilege Escalation", "T1134", Severity.MEDIUM,
            "Interactive logon with an elevated (admin) token.",
            single_rule(4624, lambda e: (e.get("ElevatedToken") or "0") == "%%1843", cap=30),
        ),

        # ---------- Credential Access --------------------------------------- #
        Rule.make(
            "LSASS", "LSASS process access",
            "Credential Access", "T1003.001", Severity.CRITICAL,
            "Process attempted to open the LSASS process (credential dump attempt).",
            single_rule(4663, matcher_lsass, cap=40),
        ),
        Rule.make(
            "SAM_HIVE", "SAM / SYSTEM hive access",
            "Credential Access", "T1003.002", Severity.CRITICAL,
            "Access to the SAM/SYSTEM registry hives (hash extraction).",
            single_rule(4663, matcher_sam, cap=40),
        ),
        Rule.make(
            "DCSYNC", "Directory replication (DCSync)",
            "Credential Access", "T1003.006", Severity.CRITICAL,
            "Replication-of-changes rights requested against domain objects.",
            single_rule(4662, matcher_dcsync, cap=15),
        ),
        Rule.make(
            "KERBEROAST", "Kerberoasting",
            "Credential Access", "T1558.003", Severity.HIGH,
            "Kerberos ticket request with RC4 encryption for a service account.",
            single_rule(4769, matcher_kerberoast, cap=40),
        ),
        Rule.make(
            "PREAUTH", "AS-REP (no preauth) ticket request",
            "Credential Access", "T1558.004", Severity.MEDIUM,
            "Ticket request without preauthentication (AS-REP roasting).",
            single_rule(4768, matcher_preauth, cap=30),
        ),

        # ---------- Lateral Movement ----------------------------------------- #
        Rule.make(
            "EXPLICIT_CRED", "Explicit credentials used",
            "Lateral Movement", "T1021.006", Severity.MEDIUM,
            "A logon was attempted using explicit credentials (RunAs / remote exec).",
            single_rule(4648, cap=50),
        ),
        Rule.make(
            "ADMIN_NETLOGON", "Admin network logon",
            "Lateral Movement", "T1021.002", Severity.HIGH,
            "Administrator account authenticated over the network.",
            single_rule(4624, matcher_admin_netlogon, cap=25),
        ),
        Rule.make(
            "RDP_LOGON", "Remote Desktop logon",
            "Lateral Movement", "T1021.001", Severity.MEDIUM,
            "Interactive session established over Remote Desktop.",
            single_rule(4624, matcher_rdp_anon, cap=40),
        ),

        # ---------- Defense Evasion / Impact --------------------------------- #
        Rule.make(
            "ANON_SESSION", "Anonymous session",
            "Discovery", "T1018", Severity.MEDIUM,
            "Anonymous (guest) network logon occurred.",
            single_rule(4624, matcher_anonymous, cap=20),
        ),
        Rule.make(
            "LOG_CLEAR", "Event log cleared",
            "Defense Evasion", "T1070.001", Severity.HIGH,
            "The security event log was cleared (indicator destruction).",
            single_rule(1102, cap=20),
        ),
    ]


# --------------------------------------------------------------------------- #
# Custom evaluators that need state + multiple sorts
# --------------------------------------------------------------------------- #

def _spray_rule(ctx: RuleContext) -> List[Dict]:
    by_ip: Dict[str, List] = defaultdict(list)
    for e in ctx.by_id.get(4625, []):
        ip = _key(e, ("SourceNetworkAddress",))
        if ip in ("?", "-"):
            continue
        by_ip[ip].append(e)
    found = []
    for ip, evs in by_ip.items():
        evs.sort(key=lambda e: e.timestamp)
        tail = evs[-12:]
        span = (tail[-1].timestamp - tail[0].timestamp).total_seconds()
        users = {get(e, "TargetUserName") for e in tail}
        if span <= 600 and len(users) >= 6 and len(evs) >= 8:
            found.append({
                "events": evs[:60],
                "summary": f"spray from {ip}: {len(users)} accounts / {len(evs)} attempts",
            })
        if len(found) >= 25:
            break
    return found


def _enum_rule(ctx: RuleContext) -> List[Dict]:
    """Flag an IP that produced many distinct failed usernames (or account
    lookups) inside a short window."""
    by_ip: Dict[str, List] = defaultdict(list)
    for eid in (4625, 4771):
        for e in ctx.by_id.get(eid, []):
            ip = _key(e, ("SourceNetworkAddress",))
            if ip in ("?", "-"):
                continue
            by_ip[ip].append(e)
    found = []
    for ip, evs in by_ip.items():
        evs.sort(key=lambda e: e.timestamp)
        tail = evs[-40:]
        if len(tail) < 12:
            continue
        span = (tail[-1].timestamp - tail[0].timestamp).total_seconds()
        users = {get(e, "TargetUserName", "AccountName") for e in tail}
        if span <= 300 and len(users) >= 12:
            found.append({
                "events": evs[:80],
                "summary": f"{len(users)} distinct accounts enumerated from {ip}",
            })
        if len(found) >= 25:
            break
    return found


def _logon_after_brute_rule(ctx: RuleContext) -> List[Dict]:
    """Find successful types-3/10 logons 4624 from an IP that had >=5 failed
    logons 4625 in the 10 minutes before."""
    fails_by_ip: Dict[str, List] = defaultdict(list)
    for e in ctx.by_id.get(4625, []):
        ip = _key(e, ("SourceNetworkAddress",))
        if ip in ("?", "-"):
            continue
        fails_by_ip[ip].append(e)
    spam_ips = {
        ip: evs for ip, evs in fails_by_ip.items()
        if len(evs) >= 5
    }
    found = []
    for e in ctx.by_id.get(4624, []):
        ip = _key(e, ("SourceNetworkAddress",))
        if ip not in spam_ips:
            continue
        if e.logon_type not in ("3", "10"):
            continue
        recent = [f for f in spam_ips[ip]
                  if 0 <= (e.timestamp - f.timestamp).total_seconds() <= 600]
        if len(recent) >= 5:
            found.append({
                "events": [e] + recent[-8:],
                "summary": (f"{get(e,'TargetUserName')}@{ip} after {len(recent)} failures"),
            })
        if len(found) >= 30:
            break
    return found


def matcher_pth(e):
    if e.event_id != 4624 or e.logon_type != "3":
        return False
    return bool(e.get("ElevatedToken"))