# =============================================================================
#  Entity extraction from natural language
#
#  Pulls structured artifacts out of free text:
#    ipv4, domains, urls, file paths, process binaries, hashes, registry keys,
#    ports, mutexes, usernames, scheduled task names, event IDs, MITRE IDs,
#    shell commands, OPS strings.
# =============================================================================
import re

from .lexicon import KNOWN_PROCESSES

# Regex library -------------------------------------------------------------
RE_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\b"
)
RE_DOMAIN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|ru|cn|xyz|top|info|biz|cc|tv|me|co|uk|onion|github\.io)\b",
    re.IGNORECASE,
)
RE_URL = re.compile(
    r"\b(?:https?|ftp)://[^\s\"']+",
    re.IGNORECASE,
)
RE_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
RE_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
RE_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
RE_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
RE_PORT = re.compile(r"\bport\s+(\d{1,5})\b", re.IGNORECASE)
RE_PORT_NUM = re.compile(r"\b(?:tcp|udp)[/:]\s*(\d{1,5})\b", re.IGNORECASE)
RE_EVENTID = re.compile(r"\b(?:event\s*id\s*|eid\s*|eventid\s*)[#:\s]*(\d{3,5})\b",
                        re.IGNORECASE)
RE_MITRE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
RE_USERNAME = re.compile(r"\b(?:user|username|user account|account)\s+(?:called\s+|named\s+|is\s+)?"
                         r"['\"]?([a-zA-Z0-9_.\\-]{3,32})['\"]?", re.IGNORECASE)
RE_MUTEX = re.compile(r"\b(?:mutex|named mutex|global\\?)\b\s*['\"]?([a-zA-Z0-9_\-\\]{3,64})['\"]?",
                      re.IGNORECASE)
RE_PIPE = re.compile(r"\bnamed pipe\b\s*['\"]?([a-zA-Z0-9_\-\\.]{3,64})['\"]?",
                     re.IGNORECASE)
RE_CMD = re.compile(r"\b(cmd\s*\/c|powershell\s+-[a-z]|certutil\s|regsvr32\s|schtasks\s|"
                    r"wmic\s|bitsadmin\s|rundll32\s|mshta\s|whoami\s|net\s+user\s)")
# Windows paths: C:\... , C:/..., env vars like %APPDATA%\, named temp dirs
RE_WINPATH = re.compile(
    r"\b(?:[A-Za-z]:[\\/][^\s\"',;]+|%[A-Z_]+%[\\/][^\s\"',;]+)",
    re.IGNORECASE,
)
# Unix-ish paths
RE_UNIXPATH = re.compile(r"\b(?:/tmp/|/var/|/etc/|/home/|/usr/)[^\s\"',;]*")
RE_BINARY = re.compile(r"\b([\w.+-]{2,30}\.(?:exe|dll|ps1|bat|cmd|vbs|js|hta|scr|lnk|msi|"
                       r"py|jar|sh|bin|so|drv|sys))\b", re.IGNORECASE)
RE_SCHEDTASK = re.compile(r"\b(?:scheduled task|task)\s+(?:called|named|titled)\s*['\"]?"
                          r"([\w.\\-]{2,64})['\"]?", re.IGNORECASE)
RE_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
RE_IPRANGE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\s*-\s*(?:\d{1,3}\.){3}\d{1,3}\b")


class EntitySet:
    """Collects and dedups extracted entities by category."""

    def __init__(self):
        self._store = {}

    def add(self, category, value, hint=""):
        if category not in self._store:
            self._store[category] = []
        key = str(value).strip().lower()
        for existing in self._store[category]:
            if existing["value"].lower() == key:
                return existing
        entry = {"category": category, "value": str(value).strip(), "hint": hint}
        self._store[category].append(entry)
        return entry

    def merge(self, other):
        for category, items in other._store.items():
            for entry in items:
                self.add(category, entry["value"], entry.get("hint", ""))
        return self

    def items(self):
        out = []
        for items in self._store.values():
            out.extend(items)
        return out

    def categories(self):
        return list(self._store.keys())

    def get(self, category):
        return self._store.get(category, [])

    def count(self):
        return sum(len(v) for v in self._store.values())

    def to_dict(self):
        return {k: v for k, v in self._store.items()}


def _unique(seq):
    seen = set()
    out = []
    for x in seq:
        key = x if isinstance(x, str) else str(x)
        if key.lower() not in seen:
            seen.add(key.lower())
            out.append(x)
    return out


def _split_fields(dest, field, text, hint=""):
    for item in _unique([m.strip() for m in text.split(",") if m.strip()]):
        if re.fullmatch(r"[\w.\\:#=%+\- ]+", item, re.IGNORECASE):
            dest.add(field, item, hint)


def extract_entities(text):
    """Return an EntitySet populated with artifacts found in `text`."""
    ent = EntitySet()
    t = text

    # --- hashes (longest first so sha256 wins over sha1/md5 substrings) ----
    for h in re.findall(RE_SHA256, t):
        ent.add("hash_sha256", h, "SHA256 checksum")
    for h in re.findall(RE_SHA1, t):
        ent.add("hash_sha1", h, "SHA1 checksum")
    for h in re.findall(RE_MD5, t):
        ent.add("hash_md5", h, "MD5 checksum")
    for h in re.findall(RE_UUID, t):
        ent.add("uuid", h, "GUID/UUID")

    # --- URLs & domains -----------------------------------------------------
    for u in re.findall(RE_URL, t):
        ent.add("url", u.rstrip(".,;:)'\" "), "Full URL")
        m = re.match(r"https?://([^/]+)/?", u)
        if m:
            ent.add("domain", m.group(1), "URL host")
    for d in _unique(re.findall(RE_DOMAIN, t)):
        ent.add("domain", d, "Domain name")

    # --- network ------------------------------------------------------------
    for ip in re.findall(RE_IPV4, t):
        ent.add("ip", ip, "IPv4 address")
    for rng in re.findall(RE_IPRANGE, t):
        ent.add("ip_range", rng, "IP range")
    for m in re.finditer(RE_PORT, t):
        ent.add("port", m.group(1), "Network port")
    for m in re.finditer(RE_PORT_NUM, t):
        ent.add("port", m.group(1), "Network port")
    for m in re.finditer(RE_EVENTID, t):
        ent.add("event_id", m.group(1), "Windows Event ID")
    for m in re.finditer(RE_MITRE, t):
        ent.add("mitre_id", m.group(1).upper(), "MITRE ATT&CK technique")

    # --- file / process -----------------------------------------------------
    for p in re.findall(RE_WINPATH, t):
        ent.add("file_path", p.rstrip(".,;:)'\" "), "Windows file path")
    for p in re.findall(RE_UNIXPATH, t):
        ent.add("file_path", p.rstrip(".,;:)'\" "), "Unix file path")
    for b in re.findall(RE_BINARY, t):
        hint = ""
        name = b.lower()
        if name in KNOWN_PROCESSES:
            hint = KNOWN_PROCESSES[name][0]
        elif b.lower().endswith(".exe"):
            hint = "Binary"
        ent.add("process", b, hint)
    # bare known processes without extension (powershell, mimikatz, ...)
    for token in re.findall(r"\b([a-zA-Z0-9_.-]{2,40})\b", t):
        low = token.lower()
        stem = low[:-4] if low.endswith(".exe") else low
        if stem in KNOWN_PROCESSES and stem not in ("cmd", "net", "reg", "at", "ssh"):
            hint = KNOWN_PROCESSES[stem][0]
            ent.add("process", token, hint)
    # commands
    for m in re.finditer(RE_CMD, t):
        join = m.group(1).strip().lower()
        word = join.split()[0].strip("-/")
        if word:
            ent.add("command", join, f"Command: {word}")

    # --- registry -----------------------------------------------------------
    for m in re.finditer(
        r"\b(HKEY_[A-Z0-9_]+|HKLM|HKCU|HKCR|HKU|HKCC)[\\/][^\s\"',;]+",
        t, re.IGNORECASE,
    ):
        ent.add("registry_key", m.group(0).rstrip(".,;:)"), "Registry path")

    # --- identity & objects -------------------------------------------------
    for m in re.finditer(RE_USERNAME, t):
        ent.add("user", m.group(1), "Account name")
    for m in re.finditer(RE_MUTEX, t):
        ent.add("mutex", m.group(1), "Named mutex")
    for m in re.finditer(RE_PIPE, t):
        ent.add("pipe", m.group(1), "Named pipe")
    for m in re.finditer(RE_SCHEDTASK, t):
        ent.add("scheduled_task", m.group(1), "Scheduled task name")
    for m in re.finditer(RE_EMAIL, t):
        ent.add("email", m.group(0), "Email address")

    # --- quoted strings as candidate OPS/hardcoded values -------------------
    for m in re.finditer(r"['\"]([^'\"]{2,90})['\"]", t):
        cand = m.group(1)
        if re.search(r"\s", cand) and not re.search(r"(executable|file|server|folder|process|port|domain|host)", cand, re.I):
            continue
        ent.add("string", cand, "Quoted string / IOC")

    # IPv4 appearing inside a range should not duplicate as ip
    return ent


def summarize(entities):
    """Return a compact dict used by the UI overview."""
    cats = {
        "process": "Processes",
        "ip": "IP addresses",
        "domain": "Domains",
        "url": "URLs",
        "file_path": "File paths",
        "registry_key": "Registry keys",
        "hash_sha256": "SHA256 hashes",
        "hash_sha1": "SHA1 hashes",
        "hash_md5": "MD5 hashes",
        "port": "Ports",
        "user": "Accounts",
        "mutex": "Mutexes",
        "pipe": "Named pipes",
        "command": "Commands",
        "scheduled_task": "Scheduled tasks",
        "event_id": "Event IDs",
        "email": "Emails",
        "mitre_id": "MITRE IDs",
        "string": "IOC strings",
        "uuid": "UUIDs",
    }
    return {cats.get(c, c): items for c, items in entities.to_dict().items()} if entities else {}