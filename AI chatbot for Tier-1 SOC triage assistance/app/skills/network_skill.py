"""Skill: Network & C2 Analysis."""
import re

PRIORITY = 40
KEYWORDS = ["network", "c2", "c&c", "beacon", "traffic", "dns", "proxy",
            "firewall", "ids", "ips", "packet", "pcap", "flow", "zeek",
            "suricata", "port scan", "portscan", "lateral", "smb", "rdp",
            "exfiltration", "data transfer", "outbound", "inbound", "connection",
            "socket", "tunneling", "vpn", "tor", "sig p2p", "geo-ip"]

WELL_KNOWN_PORTS = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "dns", 67: "dhcp", 80: "http", 110: "pop3", 111: "rpcbind",
    135: "rpc", 137: "netbios-ns", 139: "netbios-ssn", 143: "imap",
    389: "ldap", 443: "https", 445: "smb", 465: "smtps", 587: "submission",
    636: "ldaps", 993: "imaps", 995: "pop3s", 1433: "mssql", 1521: "oracle",
    2049: "nfs", 3306: "mysql", 3389: "rdp", 5432: "postgres",
    5900: "vnc", 5985: "winrm", 5986: "winrm-ps", 8080: "http-alt",
    8443: "https-alt", 9200: "elasticsearch", 11211: "memcached",
}
RISKY_PORTS = {
    23: "Telnet — plaintext credentials",
    445: "SMB — lateral movement / worm propagation",
    135: "RPC — remote exec & lateral movement",
    3389: "RDP — brute force & lateral movement",
    5900: "VNC — weak auth remote control",
    1433: "MSSQL — xp_cmdshell abuse",
    4444: "Classic Metasploit handler port",
    5555: "Common Android/RAT C2 port",
    6667: "IRC — legacy botnet C2",
    8888: "Common alternate HTTP / C2",
}
RARE_PORTS = {4444, 5555, 6667, 8443, 8888, 4443, 8444}

NON_ROUTABLE_PREFIXES = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.",
    "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "127.", "169.254.",
)


def _is_internal(ip):
    return any(ip.startswith(p) for p in NON_ROUTABLE_PREFIXES)


def analyze(text, iocs, context):
    low = (text or "").lower()

    ips = iocs.get("ips", [])
    internal_ips = [ip for ip in ips if _is_internal(ip)]
    external_ips = [ip for ip in ips if not _is_internal(ip)]

    ports = []
    for m in re.finditer(r"(?:port\s+|:)(\d{1,5})\b", low):
        try:
            ports.append(int(m.group(1)))
        except ValueError:
            pass
    ports = sorted(set(ports))

    risky = [(p, RISKY_PORTS[p]) for p in ports if p in RISKY_PORTS]
    rare = [p for p in ports if p in RARE_PORTS]

    tunneling = any(k in low for k in ("dns tunnel", "dns exfil", "icmp tunnel",
                                       "tunneling", "doh", "dns over https"))
    beacon = any(k in low for k in ("beacon", "c2", "c&c", "command and control",
                                    "periodic callback", "jitter"))
    exfil = any(k in low for k in ("exfiltrat", "data uploaded", "large outbound",
                                   "data transfer", "upload", "data theft"))
    scan = any(k in low for k in ("port scan", "portscan", "nmap", "ping sweep",
                                  "network scan", "sweep"))

    risk = 0
    risk += 25 if tunneling else 0
    risk += 25 if beacon else 0
    risk += 25 if exfil else 0
    risk += 10 if scan else 0
    risk += 10 if risky else 0
    risk += 5 * len(rare)
    risk += 10 if external_ips and (beacon or exfil or tunneling) else 0

    return {
        "network": {
            "internal_ips": internal_ips,
            "external_ips": external_ips,
            "ports": ports,
            "risky_ports": risky,
            "rare_ports": rare,
            "tunneling": tunneling,
            "beaconing": beacon,
            "exfiltration": exfil,
            "scanning": scan,
            "risk_score": min(risk, 100),
        }
    }


def respond(text, iocs, analysis, context):
    n = analysis.get("network", {})
    if not n:
        return ""
    lines = ["**Network & C2 Analysis**"]
    if n.get("external_ips"):
        lines.append(f"- 🌐 External IP(s): {', '.join(n['external_ips'][:5])} — check TI reputation & geo-velocity.")
    if n.get("internal_ips"):
        lines.append(f"- 🖥️ Internal host(s): {', '.join(n['internal_ips'][:5])} — identify asset owner & isolate if needed.")
    if n.get("risky_ports"):
        for p, why in n["risky_ports"][:4]:
            lines.append(f"- 🚪 Port {p}: {why}")
    if n.get("rare_ports"):
        lines.append(f"- Rare/high ports observed: {', '.join(str(p) for p in n['rare_ports'][:6])}")
    if n.get("beaconing"):
        lines.append("- 📡 Beaconing indicators — pull proxy/NetFlow for periodicity, jitter & user-agent anomalies.")
    if n.get("tunneling"):
        lines.append("- 🕳️ Possible tunneling — inspect DNS query lengths, entropy, and TXT record volume.")
    if n.get("exfiltration"):
        lines.append("- 📤 Exfiltration pattern — quantify volume, identify data owner, engage legal/compliance if PII/PHI.")
    if n.get("scanning"):
        lines.append("- 🔍 Scanning activity — check whether source is internal or external and scope the sweep.")
    lines.append(f"- Network risk score: **{n.get('risk_score', 0)}/100**")
    return "\n".join(lines)


def report_section(analysis):
    n = analysis.get("network")
    if not n:
        return None

    def yn(v):
        return "Yes" if v else "No"

    rows = "".join([
        f"<tr><td class='k'>Internal IPs</td><td>{', '.join(n.get('internal_ips', [])) or '—'}</td></tr>",
        f"<tr><td class='k'>External IPs</td><td>{', '.join(n.get('external_ips', [])) or '—'}</td></tr>",
        f"<tr><td class='k'>Ports observed</td><td>{', '.join(str(p) for p in n.get('ports', [])) or '—'}</td></tr>",
        f"<tr><td class='k'>Risky ports</td><td>{'; '.join(f'{p} ({why})' for p, why in n.get('risky_ports', [])) or 'None'}</td></tr>",
        f"<tr><td class='k'>Beaconing</td><td>{yn(n.get('beaconing'))}</td></tr>",
        f"<tr><td class='k'>Tunneling</td><td>{yn(n.get('tunneling'))}</td></tr>",
        f"<tr><td class='k'>Exfiltration signals</td><td>{yn(n.get('exfiltration'))}</td></tr>",
        f"<tr><td class='k'>Scanning</td><td>{yn(n.get('scanning'))}</td></tr>",
        f"<tr><td class='k'>Network risk</td><td><b>{n.get('risk_score', 0)}/100</b></td></tr>",
    ])
    return {"title": "Network & C2 Analysis", "html": f"<table>{rows}</table>"}
