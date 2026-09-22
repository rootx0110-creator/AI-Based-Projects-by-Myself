# =============================================================================
#  Curated example descriptions users can click to try instantly.
# =============================================================================

EXAMPLES = [
    {
        "title": "PowerShell Cradle",
        "text": ("A PowerShell process downloads a file from hxxp://evil.example.com/update.exe "
                 "using Invoke-WebRequest and executes it with iex after decoding a "
                 "Base64-encoded command line payload 4d61726b65722031323334"),
        "tags": ["powershell", "download", "amosaur"],
    },
    {
        "title": "Credential Dump",
        "text": ("Mimikatz runs on an endpoint and dumps credentials from the LSASS "
                 "process memory using sekurlsa::logonpasswords, the attacker then "
                 "attempts lateral movement to 192.168.10.45 port 445."),
        "tags": ["credential", "lateral"],
    },
    {
        "title": "Persistence via Registry",
        "text": ("The malware writes a persistence value to HKCU\\Software\\Microsoft\\Windows\\"
                 "CurrentVersion\\Run named 'Updater' pointing to %APPDATA%\\svchost.exe and "
                 "creates a scheduled task called SecurityScan that runs every hour."),
        "tags": ["registry", "persistence"],
    },
    {
        "title": "Recon Sweep",
        "text": ("An attacker runs whoami and net user domain admins on the workstation, "
                 "then queries registry keys under HKLM\\SYSTEM for current control set "
                 "details while pinging internal hosts to map the network."),
        "tags": ["recon", "discovery"],
    },
    {
        "title": "HTA Phishing",
        "text": ("A user opens a Microsoft Word email attachment containing an embedded "
                 "macro that launches mshta.exe with a remote HTA payload "
                 "hxxps://phish.example.net/x.hta which connects to a C2 beacon."),
        "tags": ["phishing", "macro"],
    },
    {
        "title": "Ransomware Impact",
        "text": ("A running process encrypts all documents on the C: drive and drops a "
                 "ransom note file named README.txt, it then uses vssadmin to delete "
                 "volume shadow copies before contacting 198.51.100.10 to exfiltrate "
                 "a database dump via HTTP."),
        "tags": ["ransom", "impact"],
    },
    {
        "title": "Obfuscated Command Line",
        "text": ("powershell.exe -windowstyle hidden -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA "
                 "is invoked on many endpoints with a base64 encoded payload that uses "
                 "Invoke-Expression to run code from a remote URL."),
        "tags": ["obfuscation", "encoded"],
    },
    {
        "title": "WMI Lateral Movement",
        "text": ("An unusual wmic process spawning cmd.exe on remote hosts and creating "
                 "a scheduled task on a target server using the WMI process "
                 "ExecCommand with credentials for an admin domain account."),
        "tags": ["lateral", "wmi"],
    },
]

# Phrases the UI highlights as quick concept search hints
QUICK_HINTS = ["download and execute", "credential dumping", "registry persistence",
               "scheduled task", "C2 beaconing", "obfuscated PowerShell", "lateral movement"]