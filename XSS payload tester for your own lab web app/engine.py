# engine.py
# Request building + XSS detection engine used by the Flask app.

import html as html_lib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

import requests

UA = "Mozilla/5.0 (XSS-Payload-Tester/1.0; lab-only) AppleWebKit/537.36"

DANGEROUS_SINKS = [
    "onerror=", "onload=", "onclick=", "onmouseover=", "onfocus=",
    "srcdoc=\"", "javascript:", "document.write", "<script", "<svg",
    "<img", "iframe",
]


# --------------------------------------------------------------------------
# URL helpers
# --------------------------------------------------------------------------

def inject_query_param(url, param, value):
    """Return a copy of `url` with `param=value` added (or replaced)."""
    scheme, netloc, path, query, frag = urlsplit(url)
    params = parse_qsl(query, keep_blank_values=True)
    cleaned = [(k, v) for k, v in params if k != param]
    cleaned.append((param, value))
    new_query = urlencode(cleaned)
    return urlunsplit((scheme, netloc, path, new_query, frag))


def decode_variants(raw):
    """Return a list of (label, decoded) variants of the raw payload."""
    once = unquote(raw)
    twice = unquote(once)
    unesc = html_lib.unescape(raw)
    return [
        ("raw", raw),
        ("unquote-1x", once),
        ("unquote-2x", twice),
        ("html-unescaped", unesc),
        ("html-unescaped+unquote", html_lib.unescape(once)),
    ]


def body_variants(body):
    """Decoded copies of the response body used for marker searching."""
    yield ("raw", body.lower())
    try:
        yield ("url-decoded", unquote(body).lower())
        yield ("url-decoded-2x", unquote(unquote(body)).lower())
    except Exception:
        pass
    unesc = html_lib.unescape(body)
    yield ("html-unescaped", unesc.lower())
    yield ("js-unicode-unescaped", re.sub(r"\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}", _js_unesc, body).lower())


def _js_unesc(m):
    try:
        return chr(int(m.group(0)[2:], 16))
    except ValueError:
        return m.group(0)


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def context_of_reflection(response_body, match_start):
    """Heuristic: what HTML context surrounds the reflected match."""
    before = response_body[max(0, match_start - 400): match_start]
    after = response_body[match_start: match_start + 400]

    in_script = bool(re.search(r"<script\b", before, re.I)) and not re.search(r"</script>", after, re.I)
    in_tag = bool(re.search(r"<[a-z][^>]*$", before, re.I))
    prev_sink = None
    for tok in ["onerror=", "onload=", "onclick=", "onmouseover=", "onfocus=", "src=", "href=", "srcdoc="]:
        if tok in before[-260:]:
            prev_sink = tok.rstrip("=")
    return in_script, in_tag, prev_sink


# --------------------------------------------------------------------------
# Full test run
# --------------------------------------------------------------------------

def run_test(config):
    """
    Execute the test plan.

    config keys (from the UI):
      url, param, method (GET/POST), location (query/form/json),
      payload_ids, custom_payloads, headers (lines), concurrency,
      timeout, cookies (dict), follow_redirects (bool)
    """
    url = config["url"].strip()
    param = (config.get("param") or "q").strip() or "q"
    method = (config.get("method") or "GET").upper()
    location = config.get("location", "query").lower()
    timeout = float(config.get("timeout", 10))
    concurrency = min(int(config.get("concurrency", 5)), 16)
    follow = bool(config.get("follow_redirects", True))
    cookies = config.get("cookies") or {}

    headers = {"User-Agent": UA}
    for line in (config.get("headers") or []):
        if line and ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()

    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)
    session.max_redirects = 5 if follow else 0

    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url

    from payloads import get_payloads
    payloads = get_payloads(ids=config.get("payload_ids") or None)
    for i, cp in enumerate((config.get("custom_payloads") or [])):
        cp = cp.strip()
        if cp:
            payloads.append({
                "id": "C%03d" % (i + 1),
                "name": "Custom payload %d" % (i + 1),
                "category": "Custom",
                "payload": cp,
                "markers": extract_markers(cp) or [cp],
                "desc": "User-supplied payload.",
                "risk": "N/A",
            })

    baseline = None
    try:
        baseline = session.get(url, timeout=timeout)
    except requests.RequestException:
        baseline = None

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        future_map = {
            pool.submit(send_one, session, url, param, method, location, p, timeout): p
            for p in payloads
        }
        for fut in as_completed(future_map):
            results.append(fut.result())

    order = {p["id"]: i for i, p in enumerate(payloads)}
    results.sort(key=lambda r: order.get(r.get("id"), 999))

    summary = summarize(baseline, results)
    return {
        "config": config,
        "summary": summary,
        "results": results,
        "baseline": base_info(baseline),
    }


def send_one(session, url, param, method, location, p, timeout):
    raw = p["payload"]

    if method == "POST":
        target = url
        if location == "form":
            req_ctx = {"url": url, "method": "POST", "where": "form-data"}
        elif location == "json":
            req_ctx = {"url": url, "method": "POST", "where": "json-body"}
        else:
            target = inject_query_param(url, param, raw)
            req_ctx = {"url": target, "method": "POST", "where": "query-string"}
        try:
            if location == "json":
                resp = session.post(target, json={param: raw}, timeout=timeout,
                                    allow_redirects=session.max_redirects > 0)
            elif location == "form":
                resp = session.post(target, data={param: raw}, timeout=timeout,
                                    allow_redirects=session.max_redirects > 0)
            else:
                resp = session.post(target, timeout=timeout,
                                    allow_redirects=session.max_redirects > 0)
            return finalize(resp, p, req_ctx)
        except requests.RequestException as exc:
            return error_result(p, exc, req_ctx)

    target = inject_query_param(url, param, raw)
    req_ctx = {"url": target, "method": "GET"}
    try:
        resp = session.get(target, timeout=timeout, allow_redirects=session.max_redirects > 0)
        return finalize(resp, p, req_ctx)
    except requests.RequestException as exc:
        return error_result(p, exc, req_ctx)


def finalize(resp, p, ctx):
    body = resp.text or ""
    task = dict(p)
    task.update({
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "bytes": len(body),
        "url_final": resp.url,
        "context": ctx,
    })

    variants = decode_variants(task["payload"])
    markers = [m.lower() for m in task.get("markers", []) if m]

    best_index = -1
    match_variant = None
    reflected_snippet = None

    for label, decoded in variants:
        if not decoded:
            continue
        idx = body.lower().find(decoded.lower())
        if idx != -1 and (best_index == -1 or idx < best_index):
            best_index = idx
            match_variant = label

    if best_index != -1:
        reflected_snippet = body[max(0, best_index - 20): best_index + 80]

    marker_hits = [m for m in markers if m and m in body.lower()]
    flags = context_of_reflection(body, best_index) if best_index != -1 else None

    # marker detection across decoded body variants (catches HTML-entity and
    # JS-unicode-escaped payloads that execute but are not echoed literally)
    body_var_hits = []
    for bv_label, bv_lower in body_variants(body):
        for m in markers:
            if m and m.lower() in bv_lower and m.lower() not in [h[0].lower() for h in body_var_hits]:
                body_var_hits.append([m, bv_label])
    encoded_form_detected = bool(body_var_hits)
    decoded_marker_hits = [h[0] for h in body_var_hits]

    dangerous = [s for s in DANGEROUS_SINKS if s in body.lower()]
    has_alert = "alert(" in body.lower() or any("alert(" in h[0].lower() for h in body_var_hits)

    if (marker_hits or encoded_form_detected) and has_alert and any(s in body.lower() for s in ["<script", "onerror", "onload", "srcdoc", "iframe"]):
        verdict, confidence = "Executable XSS", "High"
    elif match_variant and flags and flags[0] and (marker_hits or decoded_marker_hits):
        verdict, confidence = "Executable XSS (script context)", "Medium"
    elif match_variant and flags and flags[2]:
        verdict, confidence = "Reflected in event-sink", "Medium"
    elif match_variant or encoded_form_detected:
        verdict, confidence = "Reflected", "Confirmed" if (marker_hits or decoded_marker_hits) else "Likely"
    elif marker_hits:
        verdict, confidence = "Partial reflection (markers)", "Weak"
    else:
        verdict, confidence = "Not reflected / filtered", "Confirmed"

    # merge decoded-marker evidence into the record
    combined_hits = list(dict.fromkeys(marker_hits + decoded_marker_hits))
    task.update({
        "verdict": verdict,
        "confidence": confidence,
        "marker_hits": combined_hits[:8],
        "reflection_variant": match_variant or (decoded_marker_hits and "decoded" or None),
        "reflected_snippet": reflected_snippet,
        "dangerous": dangerous[:4],
        "analysis": {
            "script_context": flags[0] if flags else None,
            "tag_context": flags[1] if flags else None,
            "prev_sink": flags[2] if flags else None,
        } if flags else None,
        "evidence": {
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type", ""),
            "bytes_returned": len(body),
            "url_final": resp.url,
            "markers_found": combined_hits[:8],
            "reflected_snippet": reflected_snippet,
            "dangerous_sinks": dangerous[:4],
            "page_head": redact_scripts(body[:600]),
        },
    })
    return task


def error_result(p, exc, ctx):
    task = dict(p)
    task.update({
        "status": str(exc.__class__.__name__),
        "verdict": "Connection error" if isinstance(exc, requests.exceptions.ConnectionError) else "Error",
        "confidence": "Info",
        "error": str(exc)[:180],
        "evidence": {"error": str(exc)[:180]},
    })
    return task


def redact_scripts(text):
    return re.sub(
        r"(?i)<script[\s\S]{0,200}?</script>",
        "<script>[executable block omitted for safety]</script>",
        text,
    )


def base_info(resp):
    if resp is None:
        return {"reachable": False, "status": None, "content_type": "", "final_url": "",
                "size": 0, "head": "Target unreachable."}
    head = redact_scripts((resp.text or "")[:400])
    return {
        "reachable": resp.status_code < 500,
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "final_url": resp.url,
        "size": len(resp.text or ""),
        "head": head,
    }


def summarize(baseline, results):
    total = len(results)
    exec_xss = [r for r in results if "Executable XSS" in r.get("verdict", "")]
    event_sink = [r for r in results if "event-sink" in r.get("verdict", "")]
    reflected = [r for r in results if r.get("verdict") == "Reflected"]
    partial = [r for r in results if "Partial" in r.get("verdict", "")]
    filtered = [r for r in results if "Not reflected" in r.get("verdict", "")]
    errors = [r for r in results if r.get("verdict") in ("Error", "Connection error")]

    return {
        "total": total,
        "executable": len(exec_xss),
        "event_sink": len(event_sink),
        "reflected": len(reflected),
        "partial": len(partial),
        "filtered": len(filtered),
        "errors": len(errors),
        "baseline_reachable": bool(baseline and baseline.status_code < 500),
    }


def extract_markers(raw):
    """Best-effort marker candidates for a custom payload."""
    import re as _re
    markers = []
    for m in _re.findall(r"alert\s*\(\s*[\w'\"]+\)", raw):
        markers.append(m)
    for m in ["<script", "onerror", "onload", "srcdoc", "javascript:", "svg", "img"]:
        if m.lower() in raw.lower():
            markers.append(m)
    return markers