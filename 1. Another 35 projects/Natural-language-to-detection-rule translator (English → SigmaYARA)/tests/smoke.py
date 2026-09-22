import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.translator import translate
from engine.entities import extract_entities

tests = [
    "A PowerShell process downloads a file from hxxp://evil.example.com/update.exe using Invoke-WebRequest and executes it with iex after decoding a Base64-encoded command line payload",
    "Mimikatz runs on an endpoint and dumps credentials from the LSASS process memory using sekurlsa::logonpasswords, the attacker then attempts lateral movement to 192.168.10.45 port 445.",
    "The malware writes a persistence value to HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run named 'Updater' pointing to %APPDATA%\\svchost.exe and creates a scheduled task called SecurityScan that runs every hour.",
    "An attacker runs whoami and net user domain admins on the workstation, then queries registry keys under HKLM\\SYSTEM.",
]
for t in tests:
    print("=" * 100)
    print("INPUT:", t[:80])
    r = translate(t)
    print("confidence:", r["confidence_pct"], "level:", r["level"], "logsource:", r["logsource"])
    print("entities:", r["entities_count"], "concepts:", [c["label"] for c in r["concepts"]])
    print("mitre:", [m["id"] for m in r["mitre"]])
    print("----- SIGMA -----")
    print(r["sigma"])
    print("----- YARA -----")
    print(r["yara"])
print("OK")