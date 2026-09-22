"""Demo alert presets shipped with the application.

Rendered as one-click chips in the UI so testers/analysts can try the
assistant without crafting sample alerts. Kept in Python (not JS) so the
data is always present inside the PyInstaller bundle.
"""

DEMOS = [
    {
        "label": "🎯 Phishing / BEC",
        "text": (
            "SIEM Alert #44821 - Possible phishing email delivered to 25 users.\n"
            "Sender: ceo@micros0ft-secure-login.com\n"
            "Subject: URGENT: Wire transfer approval required immediately\n"
            "URL: https://micros0ft-secure-login.com/index.php?action=login\n"
            "Attachment: Invoice_2026.xlsm\n"
            "Gateway verdict: spam suspected, detonation pending."
        ),
    },
    {
        "label": "🦠 Malware / EDR",
        "text": (
            "EDR Detection: Trojan:Win32/Emotet!MTB on FIN-WS-42 (10.10.2.15), user jdoe\n"
            "File: invoice_scanner.exe\n"
            "SHA256: 44d88612fea8a8f36de82e1278abb02f9a7151b9ba1d4d64d3b1e2c5d4a6b8c1\n"
            "Behavior: LSASS access attempt, scheduled task persistence created,\n"
            "C2 beacon to 45.33.32.156:4444,\n"
            "Powershell -enc downloadstring observed in process lineage."
        ),
    },
    {
        "label": "🔐 Credentials",
        "text": (
            "Identity protection alert: Impossible travel detected for user a.nguyen@company.com\n"
            "- Sign-in from Rotterdam, NL 12 min after successful sign-in from Singapore\n"
            "- MFA fatigue push bombing pattern (14 pushes in 5 minutes)\n"
            "- Mimikatz binary detected later on host HR-LT-08, pass-the-hash activity observed\n"
            "- Brute force against VPN portal from 203.0.113.77"
        ),
    },
    {
        "label": "🌐 Network / C2",
        "text": (
            "NDR alert: Periodic beaconing from host 192.168.4.21 to 45.33.32.156 every 60s +/- jitter\n"
            "Port 4444 and 8888 observed, user-agent anomalies in proxy logs.\n"
            "DNS tunneling suspected: unusually long TXT queries to data-exfil-server.top\n"
            "Large outbound transfer to external IP 185.220.101.45 - possible exfiltration."
        ),
    },
    {
        "label": "💥 Vulnerability",
        "text": (
            "Scanner finding (Qualys): Public facing Exchange server EXCH-01 affected by\n"
            "ProxyLogon (CVE-2021-26855). Also missing patch for PrintNightmare (CVE-2021-34527).\n"
            "Actively exploited per CISA KEV.\n"
            "Web shell suspected: new aspx file in \\inetpub\\wwwroot\\aspnet_client\\\n"
            "POST exploitation: CVE-2024-3400 on PAN-OS edge firewall."
        ),
    },
    {
        "label": "🔒 Ransomware",
        "text": (
            "CRITICAL EDR ALERT: LockBit ransomware executing on FS01 (file server)\n"
            "Files encrypted with .lockbit extension, ransom note dropped.\n"
            "vssadmin delete shadows /all executed, shadow copies deleted.\n"
            "Lateral movement from 10.10.2.15 via SMB, large outbound data transfer\n"
            "before encryption. Domain admin account used on FS01."
        ),
    },
    {
        "label": "📤 Insider / Exfil",
        "text": (
            "DLP alert: departing user m.sales (resignation notice period, last day Friday)\n"
            "uploaded 4.2 GB of customer data including PII to personal Dropbox,\n"
            "7z password protected archive created, sensitive data marked confidential.\n"
            "Bulk download from SharePoint CRM export, USB removable media connected."
        ),
    },
]
