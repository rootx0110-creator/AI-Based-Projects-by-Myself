import datetime as dt
import os
import re
import time as _time

EVENT_TYPES = ("created", "modified", "accessed", "log")

LONG_PREFIX = "\\\\?\\"


class TimelineEvent:
    __slots__ = ("ts", "type", "source", "label", "path", "details", "size")

    def __init__(self, ts, etype, source, label, path="", details="", size=None):
        self.ts = ts
        self.type = etype
        self.source = source
        self.label = label
        self.path = path
        self.details = details
        self.size = size

    def ts_ms(self):
        return int(self.ts.timestamp() * 1000)

    def to_dict(self):
        return {
            "ts": self.ts.isoformat(sep=" ", timespec="seconds"),
            "ms": self.ts_ms(),
            "type": self.type,
            "source": self.source,
            "label": self.label,
            "path": self.path,
            "details": self.details,
            "size": self.size,
        }


_ISO_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\s*(?:[zZ]|[+-]\d{2}:?\d{2})?"
)
_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})")
_DOT_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})")
_SLASH_DATE_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")
_YMD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_MONTHS = "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_RFC_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s+\d{1,2}\s+" + _MONTHS +
    r"\s+\d{4}\s+\d{2}:\d{2}:\d{2}"
)
_EPOCH_RE = re.compile(r"(?<![\d.])(\d{10}|\d{13}|\d{16})(?!\d)")
_EN_MS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

_EPOCH_MIN = 86400
_EPOCH_MAX = int(_time.time()) + 3 * 86400


def _parse_iso(s):
    s = s.strip().replace("T", " ").replace(",", ".")
    body = s
    mf = re.search(r"\.\d{1,6}", body)
    if mf:
        body = body[: mf.start()] + body[mf.end():].strip()
    tz = None
    mt = re.search(r"([zZ]|[+-]\d{2}:?\d{2})\s*$", body)
    if mt:
        tzs = mt.group(1).upper()
        body = body[: mt.start()].strip()
        if tzs == "Z":
            tz = dt.timezone.utc
        else:
            sign = 1 if tzs[0] == "+" else -1
            digits = tzs[1:].replace(":", "")
            tz = dt.timezone(sign * dt.timedelta(hours=int(digits[:2]),
                                                 minutes=int(digits[2:] or 0)))
    try:
        naive = dt.datetime.strptime(body, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    if tz is not None:
        try:
            naive = naive.replace(tzinfo=tz).astimezone().replace(tzinfo=None)
        except (ValueError, OverflowError):
            return None
    return naive


def _parse_rfc(s):
    try:
        return dt.datetime.strptime(s, "%a, %d %b %Y %H:%M:%S")
    except ValueError:
        return None


def _parse_epoch(s):
    n = int(s)
    if len(s) == 10:
        val = n
    elif len(s) == 13:
        val = n // 1000
    else:
        val = n // 1000000
    if val < _EPOCH_MIN or val > _EPOCH_MAX:
        return None
    try:
        return dt.datetime.fromtimestamp(val)
    except (ValueError, OverflowError, OSError):
        return None


def _parse_with(regexp, line, parser):
    m = regexp.search(line)
    if m is None:
        return None
    try:
        return parser(m.group(0))
    except (ValueError, OverflowError):
        return None


def extract_timestamp(line):
    line = line.strip("\r\n")
    if not line:
        return None
    m = _ISO_RE.search(line)
    if m:
        ts = _parse_iso(m.group(0))
        if ts:
            return ts
    ts = _parse_with(_RFC_RE, line, _parse_rfc)
    if ts:
        return ts
    m = _DATE_RE.search(line)
    if m:
        for fmt in ("%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return dt.datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue
    m = _DOT_RE.search(line)
    if m:
        ts = None
        for fmt in ("%d.%m.%Y %H:%M:%S", "%m.%d.%Y %H:%M:%S"):
            try:
                ts = dt.datetime.strptime(m.group(0), fmt)
                break
            except ValueError:
                continue
        if ts:
            return ts
    m = _SLASH_DATE_RE.search(line)
    if m:
        try:
            return dt.datetime.strptime(m.group(0), "%Y/%m/%d")
        except ValueError:
            pass
    m = _YMD_RE.search(line)
    if m:
        try:
            return dt.datetime.strptime(m.group(0), "%Y-%m-%d")
        except ValueError:
            pass
    m = _EPOCH_RE.search(line)
    if m:
        ts = _parse_epoch(m.group(1))
        if ts:
            return ts
    return None


LOG_EXTS = {".log", ".txt", ".jsonl", ".log.txt", ".trace", ".out"}
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_LINES = 100_000


def _is_log_file(name):
    low = name.lower()
    if low.endswith(".log"):
        return True
    if low.endswith(".txt") or low.endswith(".jsonl") or low.endswith(".out"):
        return True
    if low.endswith(".trace"):
        return True
    return False


def _parse_log_file(path, events):
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    if size > MAX_LOG_BYTES * 4:
        return 0
    count = 0
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_LOG_BYTES)
    except OSError:
        return 0
    text = ""
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if not text:
        return 0
    for line in text.splitlines():
        if count >= MAX_LOG_LINES:
            break
        line = line.strip()
        if not line:
            continue
        ts = extract_timestamp(line)
        if ts:
            snippet = line if len(line) <= 400 else line[:397] + "..."
            events.append(TimelineEvent(
                ts, "log", os.path.basename(path),
                "log line", path, snippet, size,
            ))
            count += 1
    return count


class Scanner:
    def __init__(self, include_accessed=True, parse_logs=True):
        self.include_accessed = include_accessed
        self.parse_logs = parse_logs

    def scan(self, root, progress=None):
        base = os.path.abspath(root)
        walk_root = base
        if os.name == "nt" and not base.startswith(LONG_PREFIX):
            walk_root = LONG_PREFIX + base
        events = []
        file_count = 0
        dir_count = 0
        total_bytes = 0
        log_files = 0
        log_events = 0
        errors = 0

        def emit(name, rel, st, etype, details=""):
            path = os.path.join(base, rel) if rel else base
            if etype == "modified":
                ts = dt.datetime.fromtimestamp(st.st_mtime)
            elif etype == "accessed":
                ts = dt.datetime.fromtimestamp(st.st_atime)
            else:
                ts = dt.datetime.fromtimestamp(st.st_ctime)
            events.append(TimelineEvent(
                ts, etype, name, etype + " " + name,
                path, details, int(st.st_size) if hasattr(st, "st_size") else None,
            ))

        for dirpath, dirnames, filenames in os.walk(walk_root,
                                                    topdown=True,
                                                    onerror=lambda e: None):
            rel_dir = dirpath[len(walk_root):].lstrip(os.sep)
            dstat = None
            try:
                dstat = os.stat(dirpath)
            except OSError:
                dstat = None
            if dstat is not None:
                dir_count += 1
                emit(os.path.basename(dirpath) or base, rel_dir, dstat, "created",
                     "folder")
                emit(os.path.basename(dirpath) or base, rel_dir, dstat, "modified",
                     "folder")
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.join(rel_dir, fname) if rel_dir else fname
                file_count += 1
                try:
                    st = os.stat(full)
                except OSError:
                    errors += 1
                    continue
                total_bytes += st.st_size
                emit(fname, rel, st, "created", "file")
                emit(fname, rel, st, "modified", "file")
                if self.include_accessed:
                    emit(fname, rel, st, "accessed", "file")
                if self.parse_logs and _is_log_file(fname):
                    log_files += 1
                    if progress:
                        progress("Parsing " + rel[:120])
                    n = _parse_log_file(os.path.join(base, rel), events)
                    log_events += n
            if progress:
                progress("Scanned " + (rel_dir or base)[:120])
        if progress:
            progress("Sorting events")
        events.sort(key=lambda e: e.ts)
        stats = {
            "root": base,
            "scan_time": dt.datetime.now().isoformat(sep=" ", timespec="seconds"),
            "files": file_count,
            "dirs": dir_count,
            "bytes": total_bytes,
            "log_files": log_files,
            "log_lines": log_events,
            "errors": errors,
        }
        return events, stats


def build_stats(events, extra=None):
    stats = {"total": len(events)}
    counts = {}
    for t in EVENT_TYPES:
        counts[t] = 0
    for e in events:
        counts[e.type] = counts.get(e.type, 0) + 1
    stats["counts"] = counts
    if events:
        stats["first"] = events[0].ts.isoformat(sep=" ", timespec="seconds")
        stats["last"] = events[-1].ts.isoformat(sep=" ", timespec="seconds")
        stats["span_days"] = round((events[-1].ts - events[0].ts).total_seconds() / 86400.0, 1)
    else:
        stats["first"] = stats["last"] = None
        stats["span_days"] = 0.0
    if extra:
        stats.update(extra)
    return stats


def filter_events(events, types=None, start=None, end=None, query=None, limit=None):
    out = []
    for e in events:
        if types is not None and e.type not in types:
            continue
        if start is not None and e.ts < start:
            continue
        if end is not None and e.ts > end:
            continue
        if query:
            q = query.lower()
            hay = (e.label + " " + e.path + " " + e.details + " " + e.source).lower()
            if q not in hay:
                continue
        out.append(e)
    out.sort(key=lambda e: e.ts)
    if limit and len(out) > limit:
        out = out[: limit]
    return out