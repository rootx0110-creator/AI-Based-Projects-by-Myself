# =============================================================================
#  Concept detection: natural language -> detection concepts + MITRE ATT&CK
# =============================================================================
import re

from .entities import extract_entities
from .lexicon import DETECTION_CONCEPTS, KNOWN_PROCESSES, MITRE_NAMES, LOGSOURCE_PRESETS

# Patterns that describe a command line so rich sigma selections can be built
RE_POWERSHELL_OPTS = re.compile(
    r"(?<![\w])-(e[a-z]*ncodedcommand|enc|windowstyle|noprofile|nop|noninteractive|"
    r"hidden|ex|executionpolicy|bypass|w|window)", re.IGNORECASE
)
RE_ENCODED_CMD = re.compile(
    r"(encodedcommand|base64|frombase64string|-enc\b|wmi\s+process|invoke|"
    r"downloadstring|downloadfile|iwr|curl|the tcp|net.tcp|socket|frombase64)",
    re.IGNORECASE,
)


class ConceptHits:
    def __init__(self):
        self.hits = []          # list of {concept, matches, mitre}
        self.mitre = {}         # technique -> {name, targets:{concept:score}}

    def add(self, concept_key, matches, mitre_techniques):
        self.hits.append({"concept": concept_key, "matches": matches,
                          "mitre": list(mitre_techniques)})
        for tech in mitre_techniques:
            node = self.mitre.setdefault(tech, {"name": MITRE_NAMES.get(tech, tech),
                                                "targets": {}, "score": 0})
            node["targets"][concept_key] = node["targets"].get(concept_key, 0) + 1
            node["score"] += 1

    def concept_keys(self):
        return list(dict.fromkeys(h["concept"] for h in self.hits))

    def technique_list(self):
        return list(self.mitre.keys())

    def top_techniques(self):
        return sorted(self.mitre.items(), key=lambda kv: kv[1]["score"], reverse=True)


def detect_concepts(text, entities):
    """Return ConceptHits plus entity backing for the translation."""
    hits = ConceptHits()
    low = text.lower()
    used_words = set()

    for key, concept in DETECTION_CONCEPTS.items():
        matched = []
        for word in concept.get("words", []):
            if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", low):
                matched.append(word)
        # Favour specific concepts over generic ones: powershell_execution over
        # execution, c2_beaconing over network_connection, etc.
        if matched:
            hits.add(key, matched, concept.get("mitre", []))
            used_words.update(matched)

    # Refine with entity knowledge -------------------------------------------
    for proc in entities.get("process"):
        stem = proc["value"].lower()[:-4] if proc["value"].lower().endswith(".exe") \
            else proc["value"].lower()
        info = KNOWN_PROCESSES.get(stem) or KNOWN_PROCESSES.get(proc["value"].lower())
        if not info:
            continue
        technique = info[2]
        mitre = [technique] if technique else []
        if "_" not in stem and stem in ("powershell", "pwsh", "powershell_ise"):
            hits.add("powershell_execution", [proc["value"]], mitre or ["T1059.001"])
        elif stem in ("mimikatz", "procump", "procdump", "procdump64", "dumpit",
                      "secretsdump", "pwdump", "wce", "ntdsutil"):
            hits.add("credential_dumping", [proc["value"]], mitre or ["T1003"])
        elif stem in ("schtasks", "sc", "reg"):
            hits.add("scheduled_task", [proc["value"]], mitre or ["T1053.005"])
        elif stem == "whoami":
            hits.add("recon_discovery", [proc["value"]], ["T1033"])
        elif stem == "certutil":
            hits.add("obfuscation", [proc["value"]], ["T1140"])

    # Encoded / obfuscated PowerShell always implies execution colouring
    if re.search(RE_ENCODED_CMD, low):
        hits.add("obfuscation", ["encoded command-line hints"], ["T1027", "T1059.001"])

    # Network indicators
    has_ip = bool(entities.get("ip"))
    has_url = bool(entities.get("url") or entities.get("domain"))
    if has_ip or has_url:
        if not (set(hits.concept_keys()) & {"network_connection", "c2_beaconing",
                                            "dns_query", "http_request", "download"}):
            hits.add("network_connection", ["network indicator present"],
                     ["T1071"])

    # Registry keys strengthen registry concept
    if entities.get("registry_key") and "registry_modification" not in hits.hits:
        hits.add("registry_modification", ["registry key path present"], ["T1112"])

    # Event IDs strengthen capability
    if entities.get("event_id"):
        if "credential_dumping" not in hits.concept_keys() and \
                any(int(e["value"]) in (4688, 4104, 4103) for e in entities.get("event_id")):
            hits.add("powershell_execution", ["event ID hint"], ["T1059.001"])

    # Deduplicate: drop generic 'execution' if a more specific execution flavour exists
    specific_exec = {"powershell_execution", "cmd_execution", "scheduled_task",
                     "service_creation", "scripting"}
    execs = [h for h in hits.hits if h["concept"] == "execution"]
    present_specific = set(hits.concept_keys()) & specific_exec
    if execs and present_specific:
        hits.hits = [h for h in hits.hits if h["concept"] != "execution"]
        hits.mitre = {k: v for k, v in hits.mitre.items()
                      if k not in ("T1059",)}

    return hits


def resolve_logsource(hits, entities):
    """Pick the best Sigma logsource for a rule based on detected concepts."""
    order = ["network_connection", "dns_query", "file_creation", "file_event",
             "registry_modification", "startup_persistence", "scheduled_task",
             "service_creation", "upload_exfiltration", "download", "c2_beaconing",
             "http_request", "lateral_movement", "process_creation"]
    keys = hits.concept_keys()
    for key in order:
        if key in keys:
            preset = LOGSOURCE_PRESETS.get(key, LOGSOURCE_PRESETS["default"])
            return dict(preset)
    return dict(LOGSOURCE_PRESETS["process_creation"])


def severity_for(hits):
    sev = "medium"
    for key in hits.concept_keys():
        csev = DETECTION_CONCEPTS.get(key, {}).get("severity", "medium")
        if csev == "critical":
            return "critical"
        if csev == "high":
            sev = "high"
    return sev


def coverage_ratio(hits, entities, words_in_input):
    """Rough heuristic confidence of translation quality (0..1)."""
    signal = 0.0
    if hits.hits:
        signal += min(1.0, len(hits.concept_keys()) * 0.22)
    if entities.items():
        signal += min(1.0, entities.count() * 0.06)
    if entities.get("process") or entities.get("ip") or entities.get("domain") or \
            entities.get("file_path") or entities.get("registry_key"):
        signal += 0.2
    return round(min(0.99, max(0.35, signal)), 3)


def summarize_hits(hits):
    """Human friendly summary of what the engine understood (deduped)."""
    merged = {}
    for hit in hits.hits:
        key = hit["concept"]
        if key not in merged:
            merged[key] = {"matches": [], "mitre": hit.get("mitre", [])}
        for m in hit.get("matches", []):
            if m not in merged[key]["matches"]:
                merged[key]["matches"].append(m)
    lines = []
    for key, data in merged.items():
        concept_label = DETECTION_CONCEPTS[key]["label"]
        chain = ", ".join(data["matches"][:4])
        mitre = ", ".join(data["mitre"][:3])
        lines.append({"label": concept_label, "phrase": data["matches"][:4],
                      "mitre": mitre})
    return lines