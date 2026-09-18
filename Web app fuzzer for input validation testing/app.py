"""
Web App Fuzzer for Input Validation Testing - Flask application.
Run:  python app.py   (or double-click run.bat)
"""

import os
import threading
import time
import urllib.parse

from flask import Flask, jsonify, render_template, request, send_file
from io import BytesIO

import fuzzer
from report import build_report, download_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

SCANS = {}
SCAN_LOCK = threading.Lock()
SCAN_ID = {"n": 0}

HELP_CATEGORY_NOTES = {
    "sql": "Sends boolean, union, error and time-based probes. Watch for status "
           "changes, SQL error text and >5s response delays.",
    "xss": "Checks whether payloads are echoed back unencoded. A reflection is "
           "a lead, not proof of exploitability.",
    "cmd": "Sends command separators with benign markers and timing sleeps. "
           "Reflection of the marker or a delay indicates a lead.",
    "traversal": "Uses encoded and plain traversal sequences seeking file "
                 "content such as /etc/passwd or win.ini.",
    "ldap": "Probes LDAP filter structure. Error responses may reveal filter "
            "processing.",
    "template": "{{7*7}} style probes. A computed value (49) in the response "
                "means server-side evaluation.",
    "ssrf": "Asks the server to fetch internal and cloud metadata addresses. "
            "Responses containing the target content confirm the lead.",
    "xml": "XXE payloads that attempt file or SSRF extraction through "
           "external entities.",
    "redir": "Checks redirect handling for open redirect vectors.",
    "format": "Format-string probes that may crash fragile parsers.",
    "jwt": "Auth and role tampering probes (JWT none algorithm, role spoofing).",
}

DEFAULT_ADVICE = (
    "This is an authorized scan. Only run against applications you own, have "
    "been contracted to test, or have explicit written permission to assess."
)


@app.route("/")
def index():
    return render_template("index.html",
                           version=fuzzer.APP_VERSION,
                           categories=fuzzer.PAYLOADS,
                           help_notes=HELP_CATEGORY_NOTES,
                           advice=DEFAULT_ADVICE)


@app.route("/api/categories", methods=["GET"])
def api_categories():
    return jsonify([{"id": cid, "name": c["name"], "description": c["description"],
                     "severity": c["severity"]}
                    for cid, c in fuzzer.PAYLOADS.items()])


@app.route("/api/suggest/<field>", methods=["GET"])
def api_suggest(field):
    """Suggest which payload categories best fit a field name."""
    field_low = field.lower()
    mapping = {
        "sql": ["id", "code", "value", "search", "query", "name", "user"],
        "xss": ["name", "comment", "message", "title", "search", "q", "bio", "note"],
        "cmd": ["cmd", "command", "exec", "ping", "host", "ip", "domain", "shell"],
        "traversal": ["file", "path", "dir", "read", "doc", "page", "download", "template"],
        "template": ["template", "theme", "view", "layout", "page"],
        "ssrf": ["url", "feed", "fetch", "proxy", "link", "img", "callback", "webhook"],
        "ldap": ["uid", "cn", "ou", "dn", "username", "login"],
        "redir": ["redirect", "next", "return", "url", "target", "goto", "dest"],
        "xml": ["xml", "soap", "body"],
        "jwt": ["token", "jwt", "auth", "session", "role"],
    }
    suggested = []
    for cid, kws in mapping.items():
        if any(kw in field_low for kw in kws):
            suggested.append(cid)
    return jsonify(suggested)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "A target URL is required."}), 400
    if not url.lower().startswith(("http://", "https://")):
        return jsonify({"error": "URL must start with http:// or https://."}), 400

    method = (data.get("method") or "GET").upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"):
        return jsonify({"error": "Unsupported HTTP method."}), 400

    categories = data.get("categories") or []
    categories = [c for c in categories if c in fuzzer.PAYLOADS]
    if not categories:
        return jsonify({"error": "Select at least one payload category."}), 400

    fields_source = (data.get("fields") or "").strip()
    fields = [f for f in re_split(fields_source) if f]
    fields = list(dict.fromkeys(fields))
    if not fields:
        return jsonify({"error": "Provide at least one field name to fuzz."}), 400

    params = parse_pairs(data.get("params") or "")
    data_body = parse_pairs(data.get("data") or "")
    headers = parse_headers(data.get("headers") or "")

    threads = clamp_int(data.get("threads"), 1, 12, 4)
    delay = clamp_int(data.get("delay"), 0, 60, 0)
    timeout = clamp_int(data.get("timeout"), 2, 120, 15)
    shuffle = bool(data.get("shuffle"))

    config = {
        "url": url,
        "method": method,
        "categories": categories,
        "fields": fields,
        "params": params,
        "data": data_body,
        "headers": headers,
        "threads": threads,
        "delay": delay,
        "timeout": timeout,
        "shuffle": shuffle,
        "cookies": parse_cookies(data.get("cookies") or ""),
        "user_agent": (data.get("user_agent") or "").strip()
                      or "WebAppFuzzer/%s" % fuzzer.APP_VERSION,
        "verify_ssl": bool(data.get("verify_ssl", False)),
        "inject_params": bool(data.get("inject_params", True)),
        "inject_data": bool(data.get("inject_data", True)),
        "inject_headers": bool(data.get("inject_headers", False)),
        "use_baseline": bool(data.get("use_baseline", True)),
    }

    with SCAN_LOCK:
        SCAN_ID["n"] += 1
        sid = SCAN_ID["n"]
        token = "%d-%d" % (int(time.time()), sid)

    cancel = threading.Event()
    progress = fuzzer.FuzzProgress(0)
    progress.add_log("Scan %s prepared. Target: %s (%s)  Fields: %s"
                     % (token, url, method, ", ".join(fields)))
    progress.add_log("Payload categories: %s"
                     % ", ".join(fuzzer.PAYLOADS[c]["name"] for c in categories))

    SCANS[token] = {
        "config": config,
        "progress": progress,
        "cancel": cancel,
        "done": False,
        "results": [],
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def worker():
        fz = fuzzer.Fuzzer(config, progress)
        try:
            results = fz.run(cancel)
            with SCAN_LOCK:
                SCANS[token]["results"] = results
                SCANS[token]["done"] = True
                SCANS[token]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as exc:  # noqa: BLE001
            progress.add_log("Scan failed: %s" % exc)
            with SCAN_LOCK:
                SCANS[token]["done"] = True
                SCANS[token]["failed"] = str(exc)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    return jsonify({"token": token})


@app.route("/api/scan/<token>", methods=["GET"])
def api_scan_status(token):
    with SCAN_LOCK:
        s = SCANS.get(token)
        if not s:
            return jsonify({"error": "Unknown scan token."}), 404
        config = s["config"]
        counts = {}
        for r in s["results"]:
            counts[r["severity"]] = counts.get(r["severity"], 0) + 1
        return jsonify({
            "token": token,
            "done": s["done"],
            "progress": {"done": s["progress"].done, "total": s["progress"].total},
            "log": s["progress"].log[-200:],
            "results": s["results"],
            "counts": counts,
            "config": {
                "url": config["url"],
                "method": config["method"],
                "fields": config["fields"],
                "categories": [fuzzer.PAYLOADS[c]["name"] for c in config["categories"]],
            },
            "started": s.get("started"),
            "finished": s.get("finished"),
        })


@app.route("/api/scan/<token>/cancel", methods=["POST"])
def api_scan_cancel(token):
    with SCAN_LOCK:
        s = SCANS.get(token)
        if not s:
            return jsonify({"error": "Unknown scan token."}), 404
        s["cancel"].set()
        s["progress"].abort = True
        s["progress"].add_log("Cancellation requested by user.")
        return jsonify({"ok": True})


@app.route("/api/report/<token>", methods=["GET"])
def api_report(token):
    """Generate and download a self-contained HTML report."""
    with SCAN_LOCK:
        s = SCANS.get(token)
        if not s:
            return jsonify({"error": "Unknown scan token."}), 404
        results = list(s["results"])
        config = dict(s["config"])

    html = build_report(results, config)
    filename = download_filename("fuzzer-report")
    data = BytesIO(html.encode("utf-8"))
    return send_file(
        data,
        mimetype="text/html",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/report", methods=["POST"])
def api_report_custom():
    """Generate an HTML report from results sent by the client."""
    data = request.get_json(silent=True) or {}
    results = data.get("results") or []
    config = data.get("config") or {}
    created = data.get("generated_at") or time.strftime("%Y-%m-%d %H:%M:%S")
    html = build_report(results, config, created=created)
    filename = download_filename("fuzzer-report")
    data = BytesIO(html.encode("utf-8"))
    return send_file(
        data,
        mimetype="text/html",
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# small parsing helpers
# ---------------------------------------------------------------------------

def re_split(text):
    """Split on commas and newlines, trimming whitespace."""
    out = []
    for chunk in text.replace(";", ",").replace("\n", ",").split(","):
        chunk = chunk.strip()
        if chunk and chunk not in out:
            out.append(chunk)
    return out


def parse_pairs(text):
    """name=value&name2=value2 -> dict"""
    result = {}
    for part in text.replace("\n", "&").split("&"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = vlit(v)
        else:
            result[part] = ""
    return result


def vlit(v):
    """Preserve URL-decoded intent but keep as ordinary string."""
    try:
        return urllib.parse.unquote_plus(v)
    except Exception:  # noqa: BLE001
        return v


def parse_cookies(text):
    cookies = {}
    for part in text.replace("\n", ";").split(";"):
        part = part.strip()
        if part and "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def parse_headers(text):
    headers = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


def clamp_int(value, lo, hi, default):
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("=" * 62)
    print("  Web App Fuzzer for Input Validation Testing  v%s" % fuzzer.APP_VERSION)
    print("  Open in your browser:  http://%s:%d" % (host, port))
    print("  Press Ctrl+C to stop.")
    print("=" * 62)
    app.run(host=host, port=port, debug=False, threaded=True)