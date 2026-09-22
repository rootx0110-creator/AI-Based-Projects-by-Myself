# MITRE ATT&CK mapping (generated)

## Techniques available to red

| ID | Technique | Tactic | Module | Detected by |
| --- | --- | --- | --- | --- |
| T1053.005 | Scheduled Task/Job: Scheduled Task | Persistence | `sched_task` | RULE-SCHTASK, RULE-CHANGE |
| T1566.001 | Phishing: Spearphishing Attachment | Initial Access | `phish_attach` | RULE-DL-ATTACHMENT, RULE-CHANGE |
| T1547.001 | Boot or Logon Autostart: Registry Run Keys / Startup Folder | Persistence | `run_key` | RULE-AUTOSTART, RULE-CHANGE |
| T1059.001 | PowerShell | Execution | `powershell` | RULE-PS-OBFUSC, RULE-CHANGE |
| T1027 | Obfuscated Files or Information | Defense Evasion | `powershell` | RULE-PS-OBFUSC, RULE-CHANGE |
| T1082 | System Information Discovery | Discovery | `sysinfo` | RULE-DISCOVERY, RULE-CHANGE |
| T1105 | Ingress Tool Transfer | Command and Control | `tool_drop` | RULE-TOOL-DROP, RULE-CHANGE |
| T1036.005 | Masquerading: Match Legitimate Name or Location | Defense Evasion | `masquerade` | RULE-TOOL-DROP, RULE-CHANGE |
| T1041 | Exfiltration Over C2 Channel | Exfiltration | `c2_exfil` | RULE-EXFIL |
| T1106 | Native API | Execution | `native_api` | RULE-API-CALL, RULE-CHANGE |

## Detection rules (blue)

| Rule | Name | Data Source | Detects |
| --- | --- | --- | --- |
| RULE-SCHTASK | Scheduled Task Abuse / New Job | Windows Event Log (4698/4699) + File: Task Scheduler | T1053.005 |
| RULE-DL-ATTACHMENT | Suspicious Attachment in Downloads | File | T1566.001 |
| RULE-AUTOSTART | Logon Autostart / Run Key Change | Windows Registry | T1547.001 |
| RULE-PS-OBFUSC | Obfuscated PowerShell / Script Block Logging | PowerShell Script Block Logging (4104) | T1059.001, T1027 |
| RULE-DISCOVERY | System Discovery Sweep | Process + Command Execution | T1082 |
| RULE-TOOL-DROP | Unexpected Binary Drop / Masquerade | File + Process | T1105, T1036.005 |
| RULE-EXFIL | High-Entropy Outbound Transfer on C2 Port | Network Traffic | T1041 |
| RULE-API-CALL | Suspicious Native API Usage | Process API Monitoring | T1106 |
| RULE-CHANGE | Recent Suspicious File Creation (catch-all) | File | T1053.005, T1566.001, T1547.001, T1059.001, T1027, T1082, T1105, T1036.005, T1106 |

## Data-source notes

* File + Windows Event Log keep persistence & execution covered (high fidelity).
* Network exfiltration (T1041) relies on entropy/base64 heuristics over a local
  port - a real lab should add Zeek/Suricata.
* RULE-CHANGE is the intentional low-fidelity catch-all; it is *not* proof a
  dedicated signature exists.
