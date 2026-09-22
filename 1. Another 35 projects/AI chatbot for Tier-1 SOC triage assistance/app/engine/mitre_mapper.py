"""MITRE ATT&CK mapping from free text and extracted IOCs."""

# technique_id: (name, tactic, keywords)
ATTACK_DB = {
    "T1566": ("Phishing", "Initial Access", [
        "phish", "phishing", "spearphish", "email campaign", "malicious email",
        "attachment", "url in email", "email link",
    ]),
    "T1566.001": ("Spearphishing Attachment", "Initial Access", [
        "attachment", "attached file", "invoice.pdf", "resume", "macro", "docm",
    ]),
    "T1204": ("User Execution", "Execution", [
        "user opened", "user clicked", "executed by user", "double click",
    ]),
    "T1204.002": ("Malicious File", "Execution", [
        "executable", "exe", "malicious file", "downloaded and executed",
    ]),
    "T1059": ("Command and Scripting Interpreter", "Execution", [
        "powershell", "cmd.exe", "command line", "script", "bash", "wscript",
        "cscript", "python", "javascript",
    ]),
    "T1059.001": ("PowerShell", "Execution", [
        "powershell", "-enc", "encodedcommand", "invoke-expression", "iex",
        "downloadstring",
    ]),
    "T1053": ("Scheduled Task/Job", "Persistence", [
        "scheduled task", "schtasks", "cron", "at job", "persistence task",
    ]),
    "T1547": ("Boot or Logon Autostart Execution", "Persistence", [
        "run key", "registry run", "startup folder", "autostart",
        "winlogon", "image file execution",
    ]),
    "T1136": ("Create Account", "Persistence", [
        "new user created", "account created", "net user add",
    ]),
    "T1078": ("Valid Accounts", "Defense Evasion / Persistence", [
        "valid account", "stolen credentials", "credential", "password spray",
        "brute force", "impossible travel", "anomalous login",
    ]),
    "T1110": ("Brute Force", "Credential Access", [
        "brute force", "password spray", "failed logons", "lockout",
        "credential stuffing",
    ]),
    "T1003": ("OS Credential Dumping", "Credential Access", [
        "mimikatz", "lsass", "credential dump", "sekurlsa", "ntds.dit",
        "hash dump",
    ]),
    "T1040": ("Network Sniffing", "Credential Access", [
        "packet capture", "sniffing", "pcap capture", "promiscuous",
    ]),
    "T1021": ("Remote Services", "Lateral Movement", [
        "rdp", "winrm", "psexec", "wmi exec", "smb", "ssh session",
        "lateral movement", "remote execution",
    ]),
    "T1210": ("Exploitation of Remote Services", "Lateral Movement", [
        "exploit attempt", "eternalblue", "ms17-010", "exploited service",
    ]),
    "T1041": ("Exfiltration Over C2 Channel", "Exfiltration", [
        "exfiltration", "data uploaded", "large outbound transfer",
        "beacon upload", "data theft",
    ]),
    "T1048": ("Exfiltration Over Alternative Protocol", "Exfiltration", [
        "dns tunneling", "dns exfiltration", "icmp tunnel", "ftp upload",
    ]),
    "T1071": ("Application Layer Protocol", "Command and Control", [
        "beacon", "c2", "c&c", "command and control", "callback",
        "http post c2", "malicious domain contact",
    ]),
    "T1090": ("Proxy", "Command and Control", [
        "proxy", "socks", "tor relay", "open redirect",
    ]),
    "T1486": ("Data Encrypted for Impact", "Impact", [
        "ransomware", "files encrypted", "ransom note", "lockbit",
        "encryptor", "shadow copy deleted",
    ]),
    "T1490": ("Inhibit System Recovery", "Impact", [
        "vssadmin delete", "shadow copies deleted", "bcdedit",
        "recovery disabled", "wbadmin delete",
    ]),
    "T1562": ("Impair Defenses", "Defense Evasion", [
        "av disabled", "defender disabled", "logging stopped",
        "agent uninstalled", "firewall rule added",
    ]),
    "T1070": ("Indicator Removal", "Defense Evasion", [
        "logs cleared", "event log cleared", "wevtutil", "timestomping",
        "artifacts deleted",
    ]),
    "T1105": ("Ingress Tool Transfer", "Command and Control", [
        "downloaded payload", "wget", "curl download", "certutil download",
        "bitsadmin",
    ]),
    "T1190": ("Exploit Public-Facing Application", "Initial Access", [
        "web shell", "sql injection", "public facing exploit", "cve-",
        "exploit attempt on server", "directory traversal",
    ]),
    "T1133": ("External Remote Services", "Initial Access", [
        "vpn login", "remote desktop gateway", " Citrix", "fortigate exploit",
    ]),
    "T1132": ("Data Encoding", "Command and Control", [
        "base64", "encoded traffic", "hex encoded",
    ]),
    "T1548": ("Abuse Elevation Control Mechanism", "Privilege Escalation", [
        "sudo", "uac bypass", "token manipulation", "kerberoasting",
    ]),
    "T1087": ("Account Discovery", "Discovery", [
        "net user enumeration", "account discovery", "whoami", "group enumeration",
    ]),
    "T1018": ("Remote System Discovery", "Discovery", [
        "network scan", "port scan", "ping sweep", "nmap",
    ]),
}


def map_attack(text, iocs=None):
    """Return sorted list of {id, name, tactic, score} matched in *text*."""
    if not text:
        return []
    low = text.lower()
    results = []
    for tid, (name, tactic, keywords) in ATTACK_DB.items():
        score = 0
        matched = []
        for kw in keywords:
            if kw.lower() in low:
                score += 2
                matched.append(kw)
        if tid == "T1190" and iocs and iocs.get("cves"):
            score += 3
        if score > 0:
            results.append({
                "id": tid,
                "name": name,
                "tactic": tactic,
                "score": score,
                "matched": matched[:6],
            })
    results.sort(key=lambda r: (-r["score"], r["id"]))
    return results


def top_attack(matches, n=5):
    return matches[:n]
