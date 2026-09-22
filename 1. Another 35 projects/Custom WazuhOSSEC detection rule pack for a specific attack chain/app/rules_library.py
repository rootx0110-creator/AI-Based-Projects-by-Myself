"""Embedded seed library: 26 detection rules for the Web Kill Chain.

Target estate: Windows hosts (Windows Eventlog / Sysmon) + Linux app servers
(apache access log, syslog/auditd) behind a public web application. IDs are
drawn from the OSSEC/Wazuh custom range 100000+ (local_rules.xml convention).
"""
from __future__ import annotations

from .rules_core import build_rule

_L = [
    # ------------------------------------------------------------- RECON (TA0043)
    dict(id=100001, level=5, stage="recon", mitre="T1595", source="apache_access",
         description="Web scanner probing known application paths.",
         xml='<rule id="100001" level="5">\n'
             '  <decoded_as>apache</decoded_as>\n'
             '  <regex>GET /(view|include|modules|admin|\\.\\./)</regex>\n'
             '  <description>Web scanner probing known application paths.</description>\n'
             '  <group>web_access,recon,</group>\n'
             '</rule>'),
    dict(id=100002, level=5, stage="recon", mitre="T1595.002", source="apache_access",
         description="Known vulnerability scanner user agent observed.",
         xml='<rule id="100002" level="5">\n'
             '  <decoded_as>apache</decoded_as>\n'
             '  <regex>sqlmap|nikto|masscan|acunetix|burp|nmap_</regex>\n'
             '  <description>Known vulnerability scanner user agent observed.</description>\n'
             '  <group>web_access,recon,</group>\n'
             '</rule>'),
    # ------------------------------------------------------- INITIAL ACCESS (TA0001)
    dict(id=100003, level=10, stage="initial", mitre="T1190", source="apache_access",
         description="Likely command injection pattern in web request.",
         xml='<rule id="100003" level="10">\n'
             '  <decoded_as>apache</decoded_as>\n'
             '  <regex>(cmd|exec|system|eval|wget|curl|/bin/(sh|bash)|powershell|cmd\\.exe)</regex>\n'
             '  <description>Likely command injection pattern in web request.</description>\n'
             '  <group>web_access,rce,</group>\n'
             '</rule>'),
    dict(id=100004, level=8, stage="initial", mitre="T1505.003", source="syscheck",
         description="Script file created inside a monitored webroot.",
         xml='<rule id="100004" level="8">\n'
             '  <if_sid>554</if_sid>\n'
             '  <regex>\\.(php|jsp|jspx|aspx|asp|pl|cgi)$</regex>\n'
             '  <description>Script file created inside a monitored webroot.</description>\n'
             '  <group>syscheck,web_upload,</group>\n'
             '</rule>'),
    dict(id=100005, level=10, stage="initial", mitre="T1190", source="apache_access",
         description="Log4Shell JNDI lookup pattern detected in request.",
         xml='<rule id="100005" level="10">\n'
             '  <decoded_as>apache</decoded_as>\n'
             '  <regex>\\$\\{jndi:(ldap|rmi|dns)://</regex>\n'
             '  <description>Log4Shell JNDI lookup pattern detected in request.</description>\n'
             '  <group>web_access,rce,</group>\n'
             '</rule>'),
    # ------------------------------------------------------------ EXECUTION (TA0002)
    dict(id=100006, level=7, stage="execution", mitre="T1059.001", source="windows_security",
         description="cmd.exe spawning a powershell child process.",
         xml='<rule id="100006" level="7">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>cmd\\.exe</regex>\n'
             '  <match>powershell</match>\n'
             '  <description>cmd.exe spawning a powershell child process.</description>\n'
             '  <group>windows,execution,</group>\n'
             '</rule>'),
    dict(id=100007, level=12, stage="execution", mitre="T1059.001", source="windows_security",
         description="Obfuscated powershell or in-memory download cradle.",
         xml='<rule id="100007" level="12">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>(hide-window|bypass|-enc|frombase64|iex|downloadstring)</regex>\n'
             '  <description>Obfuscated powershell or in-memory download cradle.</description>\n'
             '  <group>windows,execution,</group>\n'
             '</rule>'),
    dict(id=100008, level=12, stage="execution", mitre="T1059", source="sysmon",
         description="Web server process spawned a shell or utility child.",
         xml='<rule id="100008" level="12">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <field name="win.eventdata.parentImage">w3wp.exe</field>\n'
             '  <regex>(cmd|powershell|rundll32|bitsadmin|mshta)\\.exe</regex>\n'
             '  <description>Web server process spawned a shell or utility child.</description>\n'
             '  <group>windows,execution,</group>\n'
             '</rule>'),
    # ----------------------------------------------------------- PERSISTENCE (TA0003)
    dict(id=100009, level=9, stage="persistence", mitre="T1543.003", source="windows_security",
         description="Suspicious windows service installed from writable path.",
         xml='<rule id="100009" level="9">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">7045</field>\n'
             '  <regex>(powershell|\\\\temp|\\\\tmp|\\\\appdata|\\\\users)</regex>\n'
             '  <description>Suspicious windows service installed from writable path.</description>\n'
             '  <group>windows,persistence,</group>\n'
             '</rule>'),
    dict(id=100010, level=10, stage="persistence", mitre="T1547.001", source="sysmon",
         description="Persistence attempt via a registry Run key modification.",
         xml='<rule id="100010" level="10">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">13</field>\n'
             '  <match>CurrentVersion\\Run</match>\n'
             '  <description>Persistence attempt via a registry Run key modification.</description>\n'
             '  <group>windows,persistence,</group>\n'
             '</rule>'),
    dict(id=100011, level=8, stage="persistence", mitre="T1053", source="syslog",
         description="Scheduled job installed or edited (cron).",
         xml='<rule id="100011" level="8">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <regex>(crontab|at(\\.| |\\d))</regex>\n'
             '  <match>crontab</match>\n'
             '  <description>Scheduled job installed or edited (cron).</description>\n'
             '  <group>local,persistence,</group>\n'
             '</rule>'),
    # --------------------------------------------------- PRIVILEGE ESCALATION (TA0004)
    dict(id=100012, level=4, stage="priv_esc", mitre="T1548.003", source="syslog",
         description="Sudo privilege elevation event observed.",
         xml='<rule id="100012" level="4">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <match>sudo</match>\n'
             '  <description>Sudo privilege elevation event observed.</description>\n'
             '  <group>local,privilege_escalation,</group>\n'
             '</rule>'),
    dict(id=100013, level=10, stage="priv_esc", mitre="T1548.002", source="windows_security",
         description="UAC bypass stub or elevated binary invocation.",
         xml='<rule id="100013" level="10">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>(\\\\sysnative\\\\cmd|fodhelper|eventvwr\\.exe|sdclt\\.exe)</regex>\n'
             '  <description>UAC bypass stub or elevated binary invocation.</description>\n'
             '  <group>windows,privilege_escalation,</group>\n'
             '</rule>'),
    # ----------------------------------------------------- DEFENSE EVASION (TA0005)
    dict(id=100014, level=12, stage="defense_evasion", mitre="T1070.001", source="windows_security",
         description="Windows security event log was cleared.",
         xml='<rule id="100014" level="12">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">1102</field>\n'
             '  <description>Windows security event log was cleared.</description>\n'
             '  <group>windows,defense_evasion,</group>\n'
             '</rule>'),
    dict(id=100015, level=7, stage="defense_evasion", mitre="T1070.004", source="syslog",
         description="Attempted removal or truncation of system logs.",
         xml='<rule id="100015" level="7">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <regex>(rm .*(auth\\.log|syslog|messages|wazuh)|truncate -s 0 /var/log)</regex>\n'
             '  <description>Attempted removal or truncation of system logs.</description>\n'
             '  <group>local,defense_evasion,</group>\n'
             '</rule>'),
    dict(id=100016, level=10, stage="defense_evasion", mitre="T1562.001", source="syslog",
         description="Security agent or detection service targeted for termination.",
         xml='<rule id="100016" level="10">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <regex>(kill|pkill|killall).*(ossec|wazuh|auditd|falcon|defender)</regex>\n'
             '  <description>Security agent or detection service targeted for termination.</description>\n'
             '  <group>local,defense_evasion,</group>\n'
             '</rule>'),
    # ----------------------------------------------------- CREDENTIAL ACCESS (TA0006)
    dict(id=100017, level=12, stage="cred_access", mitre="T1003.001", source="sysmon",
         description="Potential credential dumping of the lsass process.",
         xml='<rule id="100017" level="12">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">10</field>\n'
             '  <field name="win.eventdata.targetImage">lsass.exe</field>\n'
             '  <regex>(mimikatz|procdump|comsvcs|rundll32)</regex>\n'
             '  <description>Potential credential dumping of the lsass process.</description>\n'
             '  <group>windows,credential_access,</group>\n'
             '</rule>'),
    dict(id=100018, level=10, stage="cred_access", mitre="T1003.008", source="syslog",
         description="Credential store file accessed on a local host.",
         xml='<rule id="100018" level="10">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <regex>(cat|less|tail|dd|strings).*(/etc/shadow|/etc/passwd)</regex>\n'
             '  <description>Credential store file accessed on a local host.</description>\n'
             '  <group>local,credential_access,</group>\n'
             '</rule>'),
    # ------------------------------------------------------------- DISCOVERY (TA0007)
    dict(id=100019, level=5, stage="discovery", mitre="T1082", source="windows_security",
         description="Batch of local host or network enumeration commands.",
         xml='<rule id="100019" level="5">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>(whoami|systeminfo|ipconfig /all|tasklist|\\?netstat)</regex>\n'
             '  <description>Batch of local host or network enumeration commands.</description>\n'
             '  <group>windows,discovery,</group>\n'
             '</rule>'),
    dict(id=100020, level=5, stage="discovery", mitre="T1087.002", source="windows_security",
         description="Active directory or local account enumeration.",
         xml='<rule id="100020" level="5">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>net (user|group|localgroup).* /</regex>\n'
             '  <description>Active directory or local account enumeration.</description>\n'
             '  <group>windows,discovery,</group>\n'
             '</rule>'),
    # ----------------------------------------------------- LATERAL MOVEMENT (TA0008)
    dict(id=100021, level=12, stage="lateral_move", mitre="T1021.002", source="windows_security",
         description="Access to an administrative share over the network.",
         xml='<rule id="100021" level="12">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">5140</field>\n'
             '  <regex>(admin\\$|c\\$)</regex>\n'
             '  <description>Access to an administrative share over the network.</description>\n'
             '  <group>windows,lateral_movement,</group>\n'
             '</rule>'),
    dict(id=100022, level=8, stage="lateral_move", mitre="T1110.001", source="windows_security",
         description="Failed RDP logon attempt from a network source.",
         xml='<rule id="100022" level="8">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4625</field>\n'
             '  <field name="win.eventdata.logonType">10</field>\n'
             '  <description>Failed RDP logon attempt from a network source.</description>\n'
             '  <group>windows,lateral_movement,</group>\n'
             '</rule>'),
    # ----------------------------------------------------------- COMMAND & CONTROL (TA0011)
    dict(id=100023, level=8, stage="c2", mitre="T1071", source="sysmon",
         description="Outbound connection to an atypical service port.",
         xml='<rule id="100023" level="8">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">3</field>\n'
             '  <field name="win.eventdata.state">Connect</field>\n'
             '  <regex>(:4444|:8080|:8443|:53)</regex>\n'
             '  <description>Outbound connection to an atypical service port.</description>\n'
             '  <group>windows,c2,</group>\n'
             '</rule>'),
    dict(id=100024, level=7, stage="c2", mitre="T1573", source="syslog",
         description="Potential dns tunneling or encrypted dns resolver use.",
         xml='<rule id="100024" level="7">\n'
             '  <decoded_as>syslog</decoded_as>\n'
             '  <regex>(dns\\.(google|cloudflare|nextdns)|kryptos|\\.top|\\.xyz|\\.link)</regex>\n'
             '  <description>Potential dns tunneling or encrypted dns resolver use.</description>\n'
             '  <group>local,c2,</group>\n'
             '</rule>'),
    # ------------------------------------------------------------- EXFILTRATION (TA0010)
    dict(id=100025, level=10, stage="exfil", mitre="T1048", source="windows_security",
         description="Exfiltration or transfer utility executed on host.",
         xml='<rule id="100025" level="10">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>(certutil -urlcache|b64decode|scp|ftp\\.exe|nc\\.exe)</regex>\n'
             '  <description>Exfiltration or transfer utility executed on host.</description>\n'
             '  <group>windows,exfiltration,</group>\n'
             '</rule>'),
    dict(id=100026, level=9, stage="exfil", mitre="T1560.001", source="windows_security",
         description="User document directory staged into an archive.",
         xml='<rule id="100026" level="9">\n'
             '  <decoded_as>windows_eventchannel</decoded_as>\n'
             '  <field name="win.system.eventID">4688</field>\n'
             '  <regex>(7z|rar|zip|tar).*(Documents|Downloads|Desktop|AppData)</regex>\n'
             '  <description>User document directory staged into an archive.</description>\n'
             '  <group>windows,exfiltration,</group>\n'
             '</rule>'),
]


def library_rules() -> list:
    rules = []
    for d in _L:
        rules.append(build_rule(
            rid=d["id"], level=d["level"], stage=d["stage"], mitre=d["mitre"],
            source=d["source"], description=d["description"], xml=d["xml"],
            group=d["xml"].split("<group>")[1].split("</group>")[0],
            created_by="library",
        ))
    return rules


def library_pack() -> "RulePack":
    from .rules_core import RulePack
    pack = RulePack()
    pack.load_library(library_rules())
    return pack