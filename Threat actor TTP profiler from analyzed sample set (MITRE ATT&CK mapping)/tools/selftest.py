"""Headless self-test for the TTP profiler engine.

Creates synthetic samples (script-based and hand-built PE metadata),
runs the full pipeline and writes a sample HTML report.  Useful to verify
the core engine without launching the GUI.

    python -m tools.selftest [out_dir]
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.model import SampleResult  # noqa: E402
from app.core.workbench import Workbench  # noqa: E402
from app.reports import html_report  # noqa: E402

BEACON_STRINGS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "http://192.168.1.50/panel.php?id=",
    "cmd /c powershell -enc SQBFAFgAIAAoA",
    "svchost.exe",
    "IsDebuggerPresent",
    "CheckRemoteDebuggerPresent",
    "CurrentVersion\\Run",
    "schtasks /create",
    "vssadmin delete shadows",
    "WanaCrypt0r",
    "bitcoin",
]

MIMIKATZ_STRINGS = [
    "sekurlsa::logonpasswords",
    "lsass",
    "comsvcs.dll",
    "duplicateTokenEx",
    "RegSetValueEx",
    "HttpSendRequestA",
    "WinHttpOpen",
    "URLDownloadToFile",
    "net user /add",
    "CreateRemoteThread",
    "VirtualAllocEx",
    "WriteProcessMemory",
]


def _script_sample(path: str, lines) -> SampleResult:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return SampleResult(
        filepath=path,
        filename=os.path.basename(path),
        size_bytes=os.path.getsize(path),
        file_type="plain",
        strings=list(lines),
        md5="deadbeef",
        sha1="deadbeef",
        sha256="deadbeef",
    )


def _pe_sample(name: str) -> SampleResult:
    return SampleResult(
        filepath=name,
        filename=name,
        size_bytes=1024 * 220,
        file_type="pe32",
        machine="x64 (AMD64)",
        architecture="x64",
        compile_time="2023-11-09 14:22:05 UTC",
        sections=[
            {"name": "UPX0", "vsize": 0x1000, "rawsize": 0x1000, "entropy": 7.6, "flags": "0x60000020", "exec": True, "write": True},
            {"name": "UPX1", "vsize": 0x2000, "rawsize": 0x2000, "entropy": 7.9, "flags": "0x60000020", "exec": True, "write": True},
        ],
        imports=[
            "CreateRemoteThread", "VirtualAllocEx", "WriteProcessMemory", "OpenProcess",
            "GetAsyncKeyState", "SetWindowsHookEx", "BitBlt", "GetDC",
            "RegSetValueEx", "CreateService", "OpenSCManager",
            "HttpSendRequestA", "InternetOpenA", "InternetConnectA",
            "socket", "connect", "send", "recv",
            "MiniDumpWriteDump", "CryptEncrypt", "CryptDecrypt",
            "LookupPrivilegeValue", "AdjustTokenPrivileges", "ImpersonateLoggedOnUser",
            "FindFirstFileA", "CreateToolhelp32Snapshot", "GetComputerNameA",
        ],
        dlls=["kernel32.dll", "user32.dll", "advapi32.dll", "wininet.dll", "ws2_32.dll", "dbghelp.dll", "crypt32.dll"],
        strings=[
            "http://malicious.example/path", "cmd.exe", "powershell -enc SQBFAFg",
            "sekurlsa::logonpasswords", "lsass", "schtasks", "vssadmin delete shadows",
            "bitcoin", "WanaCrypt0r", "socks5", "proxy 1080",
        ],
        packer="UPX",
        entropy=7.9,
        iocs=[],
    )


def run(out_dir: str | None = None) -> str:
    out_dir = out_dir or tempfile.mkdtemp(prefix="ttp_selftest_")
    wb = Workbench()

    script_path = os.path.join(out_dir, "stage1_dropper.ps1.txt")
    wb.samples.append(_script_sample(script_path, BEACON_STRINGS))
    script_path2 = os.path.join(out_dir, "stage2_cred.ps1.txt")
    wb.samples.append(_script_sample(script_path2, MIMIKATZ_STRINGS))
    wb.samples.append(_pe_sample("stage3_agent.exe"))

    wb.reanalyze()

    print("YARA engine:", "native" if wb.yara.is_native else wb.yara.error or "pseudo")
    print("Techniques detected: %d" % len(wb.techniques))
    for t in sorted(wb.techniques.values(), key=lambda x: -x.confidence)[:15]:
        print("  %-10s %-55s conf=%.0f%%  %s" % (t.technique_id, t.name, t.confidence, t.evidence[0][:50] if t.evidence else ""))
    print("Actor matches:")
    for a in wb.actors[:6]:
        print("  %-8s %-18s similarity=%.2f  coverage=%.0f%%  %s" % (a.actor_id, a.name, a.score, a.coverage, ",".join(a.matched_techniques[:6])))

    iocs = len({(i["type"], i["name"]) for s in wb.samples for i in s.iocs})
    print("IOCs:", iocs)

    report_path = os.path.join(out_dir, "self_test_report.html")
    html = html_report.build_report(wb._analysis, {"yara_note": wb.yara.error} if not wb.yara.is_native else None)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Wrote:", report_path, "(%d bytes)" % len(html))
    return report_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    run(out)