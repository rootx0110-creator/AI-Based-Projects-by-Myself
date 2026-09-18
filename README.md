# AI-Based-Projects-by-Myself

A collection of cybersecurity, network, and AI-adjacent tools built by myself, each in its own folder.

## Projects

| Project | Description |
| --- | --- |
| Active Directory attack path visualizer | BloodHound-style path analysis for lab domains |
| ARP scanner / live-host discovery tool | Discover live hosts on the network |
| Automated incident response playbook runner | SOAR-lite playbook automation |
| Bandwidth monitor & traffic visualizer dashboard | Real-time bandwidth and traffic dashboard |
| Browser artifact extractor | History, cookies, and cache parser |
| Custom proxy server | HTTP/SOCKS5 proxy server |
| Custom vulnerability scanner | Banner grabbing + CVE matching |
| Deleted file recovery tool | FAT/NTFS carving recovery |
| Disk image acquisition & hashing toolkit | Chain-of-custody automation |
| Endpoint hardening & compliance checker | CIS benchmark automation |
| Firewall rule auditor | Misconfiguration checker |
| Honeypot (SSH-HTTP) | Attacker fingerprinting lab |
| Host-based intrusion detection agent | File integrity + process monitoring |
| Lightweight SIEM log correlator | Ingest → normalize → alert |
| Load balancer simulator | Health checks and failover simulation |
| Log anonymizer/redactor | Safe log sharing |
| Memory forensics analyzer | Volatility plugin workflow |
| Packet sniffer | Raw socket capture |
| Password strength auditor | Wordlist-based cracker (own hashes only) |
| Phishing email analyzer | Header/URL/attachment triage |
| Port scanner | TCP connect, SYN, service-version detection |
| Ransomware behavior analysis report | Encryption pattern study (public sample) |
| Real-time SOC dashboard | 3D network topology visualization |
| Red team engagement report generator | Findings → CVSS → executive summary |
| Reverse-engineering CTF solver toolkit | Ciphers, encodings, hex utilities |
| SOC alert triage dashboard | Severity scoring + dedup |
| Social engineering awareness simulator | Internal phishing test platform |
| SQL injection detection tool | Defensive-oriented param flagging |
| Threat-intel feed aggregator | IOC ingestion + auto-blocklist |
| Timeline builder | Filesystem + log artifacts |
| Web app fuzzer | Input validation testing |
| Windows Event Log correlation tool | Intrusion timeline |
| Wireless network auditor | WPA handshake capture (lab AP) |
| YARA rule generator | From malware sample sets |
| YARA-based malware family classifier | Family identification |

## Layout

```
/
  .gitignore
  README.md
  <project-name>/
    <source code and docs>
```

All tools were developed for legal, defensive, and lab/authorized use only.

## Usage

Each project folder contains its own `requirements.txt` (or `package.json`) and
a README or architecture doc with setup and usage instructions.