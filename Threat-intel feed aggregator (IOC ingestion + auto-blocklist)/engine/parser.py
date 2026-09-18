import csv
import io

from engine.extractor import extract_iocs


def _filter_items(items, filters):
    out = []
    seen = set()
    for value, kind in items:
        value = str(value).strip()
        if not value:
            continue
        if kind:
            if filters and kind not in filters:
                continue
            out.append((value, kind))
        else:
            extracted = extract_iocs(value, filters)
            for dtype, vals in extracted.items():
                for v in vals:
                    out.append((v, dtype))
    return out


def parse_txt(raw_text, type_hint=None, filters=None):
    """Plain text / blocklist style: one IOC (or space separated) per line."""
    items = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        line = line.split("#")[0].strip()
        if not line:
            continue
        tokens = [t for t in line.split() if t]
        if len(tokens) == 1:
            candidate = tokens[0]
        else:
            candidate = max(tokens, key=_score_token)
        items.append((candidate.rstrip(",.;:") .strip("]").strip("["), type_hint))
    return _filter_items(items, filters)


def _score_token(t):
    """Heuristic score: which whitespace-separated token is most IOC-like."""
    if "://" in t:
        return 4
    score = 0
    if any(c.isdigit() for c in t):
        score += 1
    if "." in t:
        score += 2
    if t.count(":") >= 2:
        score += 1
    if t.lower().startswith(("http", "www")):
        score += 2
    return score


def parse_csv(raw_text, value_cols, type_hint=None, filters=None):
    """Parse CSV; value_cols is a list of column names or indices to try."""
    items = []
    sample = raw_text[:4096].lower()
    lines = raw_text.splitlines()
    header_present = (
        ("ip" in sample and ("domain" in sample or "url" in sample or "host" in sample))
        or "value" in sample or "ioc" in sample
    )

    if header_present:
        reader = csv.DictReader(io.StringIO(raw_text))
        for row in reader:
            value = None
            for col in value_cols:
                if isinstance(col, str) and col in row and row[col]:
                    value = row[col]
                    break
            if value is None:
                for k, v in row.items():
                    if v and extract_iocs(v, None):
                        value = v
                        break
            if value:
                items.append((value, type_hint))
    else:
        reader = csv.reader(io.StringIO(raw_text))
        for row in reader:
            if not row:
                continue
            value = None
            for col in value_cols:
                if isinstance(col, int) and col < len(row) and row[col]:
                    value = row[col]
                    break
            if value is None:
                for cell in row:
                    if extract_iocs(cell, None):
                        value = cell
                        break
            if value:
                items.append((value, type_hint))
    return _filter_items(items, filters)


def parse_json(raw_text, value_keys, type_hint=None, filters=None):
    import json as _json

    items = []
    data = _json.loads(raw_text)
    rows = data if isinstance(data, list) else (data.get("items") or data.get("data") or data.get("iocs") or [data])
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = None
        for key in value_keys:
            if key in row and row[key]:
                value = row[key]
                break
        if value is None:
            for k, v in row.items():
                if isinstance(v, str) and extract_iocs(v, None):
                    value = v
                    break
        if not value:
            continue
        kind = type_hint
        if not kind:
            t = str(row.get("type", "")).upper()
            if "IP" in t:
                kind = "IP"
            elif "DOMAIN" in t or "HOST" in t:
                kind = "DOMAIN"
            elif "URL" in t:
                kind = "URL"
            elif "HASH" in t or "MD5" in t or "SHA" in t:
                kind = "HASH"
            elif "EMAIL" in t:
                kind = "EMAIL"
        items.append((value, kind))
    return _filter_items(items, filters)


def parse_by_format(raw_text, fmt, filters=None):
    """Dispatch to the correct parser based on format label.
    fmt: TXT | CSV | JSON.
    Returns list of (value, type_string, confidence_hint_to_ignore)."""
    fmt = fmt.upper()
    if fmt == "CSV":
        items = parse_csv(raw_text, ["ip", "host", "domain", "url", "ioc", "value", "src", "destination", 0, 1, 2], filters=filters)
    elif fmt == "JSON":
        items = parse_json(raw_text, ["ioc", "indicator", "value", "ip", "host", "url", "domain", "hash"], filters=filters)
    else:
        items = parse_txt(raw_text, filters=filters)
    return items