"""Input parsing: URLs, raw HTTP requests, JSON bodies, uploads and log dumps.

Produces a normalized collection of "targets", each carrying a list of
parameter observations: {name, value, location, raw} which the analyzer can
score and, in live mode, probe.
"""

import json
import re
import urllib.parse
from collections import OrderedDict

from .payloads import NETLOC_RESERVED


class ParseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


def looks_like_url(text):
    return bool(_URL_RE.match(text.strip()))


def parse_url(target):
    """Extract scheme/host/path and query params from a URL string.

    Returns a dict with 'method', 'url', 'host', 'path' and 'params'.
    """
    raw = target.strip()
    if not _URL_RE.match(raw):
        raw = "http://" + raw
    parsed = urllib.parse.urlsplit(raw)

    params = OrderedDict()
    for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        params.setdefault(k, []).append(v)

    segments = [s for s in parsed.path.split("/") if s]
    return {
        "method": "GET",
        "url": parsed.geturl(),
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path or "/",
        "path_segments": segments,
        "params": params,
        "source": "url",
    }


# ---------------------------------------------------------------------------
# Raw HTTP request parsing
# ---------------------------------------------------------------------------
def parse_raw_request(text):
    """Parse a raw HTTP request (F5/Fiddler/ZAP or curl-style) or a curl line.

    Supports GET/POST with urlencoded, multipart and JSON bodies plus headers.
    """
    lines = text.splitlines()
    # trim empty leading lines
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        raise ParseError("Empty request")

    head = lines[0].strip()
    m = re.match(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)\s+HTTP/\d", head, re.I)
    if not m:
        # try to auto-detect a URL on the first non-blank line
        if not looks_like_url(head):
            raise ParseError("First line must be a request line (METHOD URL HTTP/x) or a URL")
        return parse_url(head)

    method = m.group(1).upper()
    target = m.group(2)

    headers = {}
    body_lines = []
    in_body = False
    for raw_line in lines[1:]:
        if not in_body:
            if not raw_line.strip():
                in_body = True
                continue
            if re.match(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+:", raw_line):
                k, _, v = raw_line.partition(":")
                headers[k.strip().lower()] = v.strip().lstrip()
        else:
            body_lines.append(raw_line)

    body = "\n".join(body_lines)

    params = OrderedDict()
    base = parse_url(target)  # includes query params
    params = base["params"]

    ctype = headers.get("content-type", "").lower()
    if body:
        if "json" in ctype or (body.lstrip().startswith("{") and not params):
            try:
                data = json.loads(body)
            except Exception:
                data = None
            if isinstance(data, dict):
                for k, v in data.items():
                    params.setdefault(k, []).append(_flatten(v))
            elif isinstance(data, list):
                params.setdefault("_json", []).append(json.dumps(data))
        elif "multipart" in ctype:
            for _k, _v in _parse_multipart(body):
                params.setdefault(_k, []).append(_v)
        else:
            for k, v in urllib.parse.parse_qsl(body, keep_blank_values=True):
                params.setdefault(k, []).append(v)

    # cookies -> params
    if "cookie" in headers:
        cow = headers["cookie"]
        params.setdefault("__cookie__", []).append(cow)
        for ck, cv in _parse_cookie(cow):
            params.setdefault("cookie:" + ck, []).append(cv)

    result = {
        "method": method,
        "url": base["url"],
        "scheme": base["scheme"],
        "host": base["host"],
        "path": base["path"],
        "path_segments": base["path_segments"],
        "params": params,
        "headers": headers,
        "body_preview": body[:2000],
        "source": "raw_request",
    }
    return result


def _flatten(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _parse_cookie(value):
    out = []
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        out.append((k.strip(), v.strip()))
    return out


def _parse_multipart(body):
    """Best-effort multipart field extraction."""
    boundary = re.search(r'bname="([^"]+)"', body) or re.search(r"--(\S+)\r\n", body)
    if not boundary:
        for pair in re.findall(r'name="([^"]+)"\r\n\r\n(.*?)\r\n', body, re.S):
            yield pair
        return
    sep = boundary.group(1)
    for block in body.split("--" + sep):
        m = re.search(r'name="([^"]+)"(?:; filename="([^"]*)")?\r\n\r\n(.*)', block, re.S)
        if m:
            yield m.group(1), (m.group(2) or m.group(3)).strip()[:2000]


# ---------------------------------------------------------------------------
# Log / list parsing (uploads or pastes)
# ---------------------------------------------------------------------------
def parse_list(text):
    """Parse a list of URLs -- one per line, comments (#) and blank lines ignored.

    Lines that look like raw request/curl lines are handed to parse_raw_request.
    Returns a list of target dicts.
    """
    targets = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if looks_like_url(line) or re.match(r"^(GET|POST|PUT|DELETE|PATCH)\s+\S+\s+HTTP", line, re.I):
            try:
                if looks_like_url(line):
                    targets.append(parse_url(line))
                else:
                    targets.append(parse_raw_request(line))
                continue
            except ParseError:
                pass
        m = re.search(r"https?://\S+", line)
        if m:
            q = m.group(0)
            if q.endswith((")", "]", "}", ",", "\"", "'")):
                q = q[:-1]
            targets.append(parse_url(q))
    return targets


# ---------------------------------------------------------------------------
# Convenience bundle: normalize whatever the user supplied
# ---------------------------------------------------------------------------
def build_targets(mode, data):
    """Return a list of target dicts from a scan request.

    mode: 'url' | 'raw' | 'list'
    """
    data = (data or "").strip()
    if not data:
        raise ParseError("No input provided")

    if mode == "url":
        if "\n" in data or "," in data:
            return parse_list(data)
        return [parse_url(data)]

    if mode == "raw":
        return [parse_raw_request(data)]

    if mode == "list":
        targets = parse_list(data)
        if not targets:
            raise ParseError("No URLs found in the file")
        return targets

    raise ParseError("Unknown scan mode: %s" % mode)