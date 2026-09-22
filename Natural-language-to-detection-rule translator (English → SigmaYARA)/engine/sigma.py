# =============================================================================
#  Sigma rule generation
# =============================================================================
import re
import uuid
from datetime import date, datetime

from .entities import extract_entities
from .lexicon import DETECTION_CONCEPTS, KNOWN_PROCESSES

# Fields useful for network / file / registry selections
FIELD_MAP = {
    "ip": "DestinationIp",
    "domain": "QueryName",
    "url": "Url",
    "port": "DestinationPort",
    "process": "Image",
    "file_path": "TargetFilename",
    "registry_key": "TargetObject",
    "command": "CommandLine",
}

# Keywords expected inside command lines per concept
CONCEPT_CMDLINE_KEYWORDS = {
    "powershell_execution": ["powershell"],
    "cmd_execution": ["cmd", "/c", "cmd.exe"],
    "obfuscation": ["encodedcommand", "base64", "-enc", "frombase64string",
                    "xor", "$([text.encoding]", "iex"],
    "scheduled_task": ["schtasks", "/create", "/sc", "onlogon", "onstart"],
    "credential_dumping": ["sekurlsa", "lsass", "priviledge::debug",
                           "sekurlsa::logonpasswords", "dump", "minidump"],
    "network_connection": ["invoke-webrequest", "downloadstring", "downloadfile",
                           "net.tcp", "tcpclient", "socket"],
    "download": ["iwr", "curl", "wget", "invoke-webrequest", "downloadfile",
                 "downloadstring", "bitsadmin", "certutil -urlcache"],
    "upload_exfiltration": ["upload", "curl", "invoke-restmethod", "webclient"],
    "file_creation": ["out-file", "set-content", "add-content", "export-csv",
                      "new-item", "copy-item", ">"],
    "registry_modification": ["reg add", "set-itemproperty", "new-itemproperty",
                              "hkcu", "hklm", "run", "runonce"],
    "startup_persistence": ["startup", "appdata", "all users", "start menu"],
    "defense_disabling": ["set-mppreference", "disable", "netsh advfirewall",
                          "reagentc /disable", "sc stop", "net stop", "wevtutil cl"],
    "recon_discovery": ["whoami", "hostname", "net user", "net group",
                        "domain admins", "ipconfig /all", "systeminfo",
                        "tasklist", "net localgroup", "get-aduser"],
    "lateral_movement": ["psexec", "winrm", "wmic /node", "net use",
                         "mstsc", "schtasks /s", "sc \\\\"],
    "injection": ["virtualalloc", "writeprocessmemory", "createremotethread",
                  "queueuserapc", "ntmapviewofsection"],
    "scripting": ["-windowstyle hidden", "wscript", "cscript", "mshta",
                  "regsvr32", "rundll32", "powershell -windowstyle"],
    "data_destruction": ["rm -rf", "del /s", "format ", "cipher /w", "wevtutil cl"],
    "c2_beaconing": ["c2", "beacon", "callback", ".dll", "inject", "beacon_"],
    "keylog": ["getasynckeystate", "setwindowshookex", "keylogger"],
}

# Prevent nonsense keywords from creating useless rules
STOPWORDS_FOR_CMDLINE = {"process", "the", "a", "an", "file", "files", "windows",
                         "system", "executable", "machine", "computer", "network"}


def _safe(value):
    """Return a quoted YAML scalar when needed."""
    if isinstance(value, list):
        return value
    if value is None:
        return ""
    value = str(value)
    if not value:
        return ""
    if re_needs_quote(value):
        return f'"{value}"'
    return value


_re_needs_quote = re.compile(r"[:#&\-{}\[\],!\*\?|>@`%'\"]|\s|^\d+$|^$")


def re_needs_quote(v):
    return bool(_re_needs_quote.search(v))


def _dump_yaml(mapping, indent=0):
    """Minimal ordered YAML writer that respects the Sigma flavour."""
    pad = "  " * indent
    lines = []
    for key, value in mapping.items():
        if value is None or value == [] or value == {} or value == "":
            continue
        key_str = _safe(key)
        if isinstance(value, dict):
            lines.append(f"{pad}{key_str}:")
            lines.extend(_dump_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{pad}{key_str}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{pad}  - ")
                    sub = _dump_yaml(item, indent + 2)
                    # indent continuation lines under the dash
                    for i, line in enumerate(sub):
                        if i == 0:
                            lines[-1] = f"{pad}  - {line.strip()}"
                        else:
                            lines.append(line)
                else:
                    lines.append(f"{pad}  - {_safe(item)}")
        else:
            lines.append(f"{pad}{key_str}: {_safe(value)}")
    return lines


def _process_selection(processes):
    """Build a Sigma process-image selection from detected binaries."""
    image_names = []
    for p in processes:
        name = p["value"]
        stem = name.lower()[:-4] if name.lower().endswith(".exe") else name.lower()
        if stem in KNOWN_PROCESSES or name.lower().endswith((".exe", ".dll", ".ps1")):
            image_names.append(name if name.lower().endswith(".exe") else name + ".exe")
    if not image_names:
        return None
    return {"Image|endswith": sorted(set(n.lower() for n in image_names))}


def _commandline_selection(concepts, processes, entities, text):
    """Build CommandLine keyword selection from concepts and command entities."""
    values = []
    # entity commands carry full-ish text, keep recognizable parts
    for cmd in entities.get("command"):
        frag = cmd["value"]
        head = frag.split()[0] if frag.split() else frag
        if head and head not in STOPWORDS_FOR_CMDLINE:
            values.append(head)
    for concept in concepts:
        for kw in CONCEPT_CMDLINE_KEYWORDS.get(concept, []):
            values.append(kw)
    for proc in processes:
        name = proc["value"].lower()
        if name not in STOPWORDS_FOR_CMDLINE:
            values.append(name)
    # avoid emitting boolean-ish single words like "dump>/run"
    cleaned = []
    for v in values:
        v = v.strip('"')
        if not v or v in STOPWORDS_FOR_CMDLINE:
            continue
        if v not in cleaned:
            cleaned.append(v)
    # Trim to keep output compact & meaningful
    if not cleaned:
        return None
    return {"CommandLine|contains": cleaned[:14]}


class SigmaRule:
    """A slim wrapper producing standard Sigma YAML."""

    def __init__(self, title, rule_id, status, description, logsource,
                 detection, false_positives, level, tags, author, created):
        self.title = title
        self.rule_id = rule_id
        self.status = status
        self.description = description
        self.logsource = logsource or {"category": "process_creation",
                                       "product": "windows"}
        self.detection = detection
        self.false_positives = false_positives
        self.level = level
        self.tags = tags
        self.author = author
        self.created = created

    def to_yaml(self):
        rule = {
            "title": self.title,
            "id": self.rule_id,
            "status": self.status,
            "description": self.description,
            "author": self.author,
            "date": self.created,
            "modified": datetime.utcnow().strftime("%Y/%m/%d"),
            "logsource": self.logsource,
            "detection": self.detection,
            "falsepositives": self.false_positives or ["Unknown"],
            "level": self.level,
            "tags": sorted(self.tags) if self.tags else [],
        }
        text = "\n".join(_dump_yaml(rule)).rstrip() + "\n"
        return text

    def to_dict(self):
        return {
            "title": self.title,
            "id": self.rule_id,
            "status": self.status,
            "description": self.description,
            "logsource": self.logsource,
            "level": self.level,
            "tags": sorted(self.tags) if self.tags else [],
        }


def build_sigma(text, entities, hits, created=None):
    """Build one coherent Sigma rule from detected concepts + entities."""
    concept_keys = hits.concept_keys()
    processes = entities.get("process")
    ip = entities.get("ip")
    domains = entities.get("domain")
    urls = entities.get("url")
    ports = entities.get("port")
    file_paths = entities.get("file_path")
    registry_keys = entities.get("registry_key")

    # detection: start with a process selection if binaries were found
    selection = {}
    if processes:
        img_sel = _process_selection(processes)
        if img_sel:
            selection["selection_img"] = img_sel

    cmd_sel = _commandline_selection(concept_keys, processes, entities, text)
    if cmd_sel:
        selection["selection_cmd"] = cmd_sel

    # network selections
    if ip and "network_connection" in concept_keys or (ip and (urls or domains)):
        dest = {"DestinationIp": sorted(ip[i]["value"] for i in range(min(len(ip), 6)))}
        if ports:
            dest["DestinationPort"] = sorted(set(p["value"] for p in ports))[:6]
        selection["selection_net"] = dest

    if domains and "dns_query" in concept_keys:
        whole = [d["value"] for d in domains[:8]]
        selection["selection_dns"] = {"QueryName|endswith": whole}

    if urls:
        url_vals = [u["value"] for u in urls[:8]]
        # dns_query -> QueryName (host portion), else Url
        if "dns_query" in concept_keys:
            selection["selection_dns"] = selection.get("selection_dns") or {"QueryName|contains": url_vals}
        elif "network_connection" in concept_keys or "http_request" in concept_keys:
            selection["selection_http"] = {"Url|contains": url_vals}

    # file / registry selections
    if file_paths and ("file_creation" in concept_keys or "file_event" in concept_keys or
                       "startup_persistence" in concept_keys or "data_destruction" in concept_keys):
        target = [f["value"] for f in file_paths[:8]]
        selection["selection_file"] = {"TargetFilename|contains": target}

    if registry_keys and ("registry_modification" in concept_keys or
                          "startup_persistence" in concept_keys):
        reg = [r["value"] for r in registry_keys[:8]]
        selection["selection_reg"] = {"TargetObject|contains": reg}

    # If nothing rose to the surface, fall back to a keyword rule on the input
    if not selection:
        tokens = _keywords_from_text(text)
        if tokens:
            selection["selection_keyword"] = {"CommandLine|contains": tokens}

    if not selection:
        selection["selection"] = {"CommandLine|contains": ["suspicious"]}

    # condition
    all_names = list(selection.keys())
    condition = " or ".join(f"{n}" for n in all_names)
    condition = f"1 of ({', '.join(all_names)})" if len(all_names) > 1 else f"{all_names[0]}"
    detection = {"condition": condition, **selection}

    title = _make_title(concept_keys, processes, domains or entities.get("ip"))
    logsource = _logsource_for(concept_keys, entities)
    level = _level_for(hits)
    mitre_tags = sorted({t for hit in hits.hits for t in hit.get("mitre", [])})

    return SigmaRule(
        title=title,
        rule_id=str(uuid.uuid4()),
        status="experimental",
        description=f"Translation from natural language: '{_snip(text, 110)}'. "
                    f"Generated by NL2Rule Translator.",
        logsource=logsource,
        detection=detection,
        false_positives=_false_positives(concept_keys),
        level=level,
        tags=mitre_tags,
        author="NL2Rule Translator",
        created=created or date.today().strftime("%Y/%m/%d"),
    )


def _keywords_from_text(text):
    from .lexicon import DETECTION_CONCEPTS
    stop = STOPWORDS_FOR_CMDLINE | {
        "installed", "installs", "install", "created", "creates", "create",
        "running", "runs", "run", "executed", "executes", "execute", "used",
        "uses", "use", "using", "with", "from", "into", "onto", "then", "and",
        "that", "this", "which", "its", "their", "them", "they", "you", "his",
        "her", "has", "have", "had", "was", "were", "been", "being", "be",
        "for", "over", "under", "through", "during", "while", "when", "contact",
    }
    words = []
    for tok in re.findall(r"\b[a-zA-Z0-9._-]{3,28}\b", text.lower()):
        if tok not in stop and re.fullmatch(r"[a-z0-9._-]+", tok):
            low = tok.rstrip(".")
            if low and low not in words:
                words.append(low)
    return words[:12]


def _make_title(concepts, processes, net):
    parts = []
    for c in ("credential_dumping", "c2_beaconing", "lateral_movement", "ransomware",
              "powershell_execution", "cmd_execution", "obfuscation", "scheduled_task",
              "service_creation", "injection", "keylog"):
        if c in concepts:
            parts.append(DETECTION_CONCEPTS[c]["label"])
    if not parts:
        parts = [DETECTION_CONCEPTS[c]["label"]
                 for c in concepts if c in DETECTION_CONCEPTS] or ["Suspicious"]
    detail = ""
    if processes:
        detail = " ".join(p["value"] for p in processes[:3]).strip()
    elif net:
        detail = " ".join(i["value"] for i in net[:2]).strip()
    if detail and len(detail) < 60:
        parts.append(f"with {detail}")
    title = "Suspicious " + " ".join(parts)
    title = title.replace("  ", " ")
    if len(title) > 90:
        title = title[:90].rsplit(" ", 1)[0]
    return title


def _logsource_for(concepts, entities):
    if "network_connection" in concepts and ("download" in concepts or
                                             "upload_exfiltration" in concepts):
        return {"category": "network_connection", "product": "windows"}
    if "dns_query" in concepts:
        return {"category": "dns_query", "product": "windows"}
    if "registry_modification" in concepts or "startup_persistence" in concepts:
        return {"category": "registry_set", "product": "windows"}
    if "file_creation" in concepts or "file_event" in concepts or \
            "data_destruction" in concepts:
        return {"category": "file_event", "product": "windows"}
    if "network_connection" in concepts and ("c2_beaconing" in concepts or
                                             "http_request" in concepts):
        return {"category": "network_connection", "product": "windows"}
    if "lateral_movement" in concepts:
        return {"category": "process_creation", "product": "windows"}
    return {"category": "process_creation", "product": "windows"}


def _level_for(hits):
    sev = "medium"
    for h in hits.hits:
        lvl = DETECTION_CONCEPTS.get(h["concept"], {}).get("severity", "medium")
        if lvl == "critical":
            return "critical"
        if lvl == "high":
            sev = "high"
    return sev


def _false_positives(concepts):
    fp = []
    if "powershell_execution" in concepts or "cmd_execution" in concepts:
        fp.append("Legitimate administrative automation scripts")
    if "network_connection" in concepts or "download" in concepts:
        fp.append("Authorized remote access or software update traffic")
    if "registry_modification" in concepts:
        fp.append("Approved software installer registry changes")
    if "file_creation" in concepts:
        fp.append("Routine application file writes")
    if "scheduled_task" in concepts:
        fp.append("Administered maintenance tasks")
    return fp or ["Unknown"]


def _snip(text, n):
    text = " ".join(str(text).split())
    return text[:n] + ("..." if len(text) > n else "")