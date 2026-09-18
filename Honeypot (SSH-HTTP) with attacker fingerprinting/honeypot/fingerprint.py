import hashlib
import json
import re
from datetime import datetime

KNOWN_BOTS = {
    "nmap": ["nmap", "Nmap", "zgrab", "ZGrab"],
    "masscan": ["masscan", "Masscan"],
    "gobuster": ["gobuster", "Gobuster"],
    "nikto": ["nikto", "Nikto"],
    "sqlmap": ["sqlmap", "SQLMap"],
    "hydra": ["hydra", "THC-Hydra"],
    "medusa": ["medusa", "Medusa"],
    "curl": ["curl/", "Wget/"],
    "python": ["python-requests", "Python-urllib", "Go-http-client"],
    "metasploit": ["Metasploit", "msf"],
    "cobaltStrike": ["cobaltstrike", "CobaltStrike"],
    "mirai": ["Mirai", "mirai"],
    "cowrie": ["Cowrie"],
}

SUSPICIOUS_PATHS = [
    "/admin", "/wp-admin", "/phpmyadmin", "/.env", "/config",
    "/backup", "/.git", "/wp-login.php", "/xmlrpc.php",
    "/wp-content", "/cgi-bin", "/shell", "/cmd", "/console",
    "/actuator", "/debug", "/trace", "/swagger", "/api-docs",
    "/server-status", "/.htaccess", "/web.config", "/crossdomain.xml",
    "/.well-known", "/robots.txt", "/sitemap.xml",
]

SSH_DUMMY_VERSIONS = [
    "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1",
    "SSH-2.0-OpenSSH_9.3p1 Ubuntu-1ubuntu3.1",
    "SSH-2.0-OpenSSH_8.4p1 Debian-5+deb11u1",
]

HTTP_DUMMY_RESPONSES = {
    200: "<html><head><title>Welcome</title></head><body><h1>Corporate Portal</h1></body></html>",
    301: "Moved Permanently",
    302: "Found",
    404: "<html><head><title>404</title></head><body><h1>Not Found</h1></body></html>",
}


class AttackerFingerprint:
    def __init__(self, src_ip, user_agent="", headers=None, ssh_client_version="",
                 extra_signals=None):
        self.src_ip = src_ip
        self.user_agent = user_agent
        self.headers = headers or {}
        self.ssh_client_version = ssh_client_version
        self.extra_signals = extra_signals or []
        self.signals = []
        self.tool_matches = []
        self.risk_factors = []
        self.risk_score = 0.0

    def analyze(self):
        self._detect_tools()
        self._analyze_user_agent()
        self._analyze_ssh_version()
        self._analyze_headers()
        self._analyze_behavior()
        self._calculate_risk()
        return self.get_result()

    def _detect_tools(self):
        combined = f"{self.user_agent} {self.ssh_client_version}"
        for tool_name, signatures in KNOWN_BOTS.items():
            for sig in signatures:
                if sig.lower() in combined.lower():
                    self.tool_matches.append(tool_name)
                    self.signals.append(f"Detected tool: {tool_name}")
                    break

    def _analyze_user_agent(self):
        if not self.user_agent:
            self.risk_factors.append("No user agent")
            return
        if len(self.user_agent) < 10:
            self.risk_factors.append("Unusually short user agent")
        if re.search(r"python|perl|ruby|go-http|java", self.user_agent, re.I):
            self.risk_factors.append("Script-based user agent")
        if any(bot in self.user_agent for bot in ["sqlmap", "nikto", "hydra"]):
            self.risk_factors.append("Known attack tool UA")

    def _analyze_ssh_version(self):
        if not self.ssh_client_version:
            return
        if "libssh" in self.ssh_client_version:
            self.risk_factors.append("libssh library detected")
        if "paramiko" in self.ssh_client_version.lower():
            self.risk_factors.append("Paramiko SSH client")
        if re.search(r"SSH-\d\.\d-\d+$", self.ssh_client_version):
            self.risk_factors.append("Minimal SSH version string")

    def _analyze_headers(self):
        if not self.headers:
            return
        accept = self.headers.get("Accept", "")
        if not accept or accept == "*/*":
            self.risk_factors.append("Generic Accept header")
        if "X-Forwarded-For" in self.headers:
            self.risk_factors.append("Proxy headers present")
        if len(self.headers) < 3:
            self.risk_factors.append("Minimal HTTP headers")

    def _analyze_behavior(self):
        for signal in self.extra_signals:
            self.risk_factors.append(signal)

    def _calculate_risk(self):
        score = 0.0
        if self.tool_matches:
            score += len(self.tool_matches) * 15
        if self.risk_factors:
            score += len(self.risk_factors) * 8
        if "nmap" in self.tool_matches or "masscan" in self.tool_matches:
            score += 20
        if "hydra" in self.tool_matches or "medusa" in self.tool_matches:
            score += 25
        if "sqlmap" in self.tool_matches or "nikto" in self.tool_matches:
            score += 20
        if "metasploit" in self.tool_matches or "cobaltStrike" in self.tool_matches:
            score += 30
        if "mirai" in self.tool_matches:
            score += 35
        if not self.user_agent and not self.ssh_client_version:
            score += 10
        self.risk_score = min(100.0, score)

    def get_fingerprint_hash(self):
        raw = f"{self.src_ip}|{self.user_agent}|{json.dumps(self.headers, sort_keys=True)}|{self.ssh_client_version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get_result(self):
        return {
            "src_ip": self.src_ip,
            "fingerprint_hash": self.get_fingerprint_hash(),
            "tool_matches": self.tool_matches,
            "signals": self.signals,
            "risk_factors": self.risk_factors,
            "risk_score": self.risk_score,
            "user_agent": self.user_agent,
            "ssh_client_version": self.ssh_client_version,
            "classification": self._classify(),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    def _classify(self):
        if self.risk_score >= 70:
            return "CRITICAL"
        if self.risk_score >= 50:
            return "HIGH"
        if self.risk_score >= 25:
            return "MEDIUM"
        if self.risk_score > 0:
            return "LOW"
        return "UNKNOWN"


def analyze_request(src_ip, user_agent="", headers=None, ssh_version="",
                    extra_signals=None):
    fp = AttackerFingerprint(src_ip, user_agent, headers, ssh_version, extra_signals)
    return fp.analyze()


def is_suspicious_path(path):
    path_lower = path.lower()
    for sp in SUSPICIOUS_PATHS:
        if sp in path_lower:
            return True, sp
    return False, None


def classify_event(event_type, username=None, password=None, path=None):
    risk = 0.0
    tags = []
    if event_type == "ssh_auth":
        risk += 5
        if username in ["root", "admin", "test", "ubuntu", "pi"]:
            risk += 10
            tags.append("common_username")
        if password and len(password) < 8:
            risk += 5
            tags.append("short_password")
    elif event_type == "http_probe":
        risk += 3
        if path:
            suspicious, matched = is_suspicious_path(path)
            if suspicious:
                risk += 15
                tags.append(f"path_probe:{matched}")
    return risk, tags
