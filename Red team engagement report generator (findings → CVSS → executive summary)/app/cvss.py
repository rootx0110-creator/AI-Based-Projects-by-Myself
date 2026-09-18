"""CVSS v3.1 vector parser and base score calculator."""

import math
import re

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

METRIC_ORDER = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]

METRIC_NAMES = {
    "AV": "Attack Vector",
    "AC": "Attack Complexity",
    "PR": "Privileges Required",
    "UI": "User Interaction",
    "S": "Scope",
    "C": "Confidentiality",
    "I": "Integrity",
    "A": "Availability",
}

METRIC_HELP = {
    "AV": "The context in which the vulnerable component is exploitable.\n"
          "N=Network, A=Adjacent, L=Local, P=Physical",
    "AC": "Conditions beyond the attacker's control that must exist to exploit.\n"
          "L=Low, H=High",
    "PR": "Level of privileges an attacker must possess before exploiting.\n"
          "N=None, L=Low, H=High (values depend on Scope)",
    "UI": "Whether the attack requires a human user to participate.\n"
          "N=None, R=Required",
    "S": "Whether a vulnerability in one component impacts resources beyond its scope.\n"
          "U=Unchanged, C=Changed",
    "C": "Impact to confidentiality of the impacted component.\n"
          "H=High, L=Low, N=None",
    "I": "Impact to integrity of the impacted component.\n"
          "H=High, L=Low, N=None",
    "A": "Impact to availability of the impacted component.\n"
          "H=High, L=Low, N=None",
}

METRIC_OPTIONS = {
    "AV": ["N", "A", "L", "P"],
    "AC": ["L", "H"],
    "PR": ["N", "L", "H"],
    "UI": ["N", "R"],
    "S": ["U", "C"],
    "C": ["H", "L", "N"],
    "I": ["H", "L", "N"],
    "A": ["H", "L", "N"],
}

METRIC_VALUE_NAMES = {
    "AV": {"N": "Network", "A": "Adjacent", "L": "Local", "P": "Physical"},
    "AC": {"L": "Low", "H": "High"},
    "PR": {"N": "None", "L": "Low", "H": "High"},
    "UI": {"N": "None", "R": "Required"},
    "S": {"U": "Unchanged", "C": "Changed"},
    "C": {"H": "High", "L": "Low", "N": "None"},
    "I": {"H": "High", "L": "Low", "N": "None"},
    "A": {"H": "High", "L": "Low", "N": "None"},
}

_VECTOR_RE = re.compile(r"^CVSS:3\.1/(" + r"/".join(
    metric + ":[A-Z]" for metric in METRIC_ORDER) + r")$")


def _roundup(value):
    return math.ceil(value * 10.0) / 10.0


def parse_vector(vector_text):
    """Parse a CVSS:3.1 vector string.

    Returns (metrics_dict, error_message). metrics_dict is None on error.
    On success metrics_dict maps metric abbreviation -> value letter.
    """
    if not vector_text:
        return None, "Vector is empty. Format: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    text = vector_text.strip()
    m = _VECTOR_RE.match(text)
    if not m:
        return None, ("Invalid CVSS v3.1 vector.\n"
                      "Use: CVSS:3.1/AV:x/AC:x/PR:x/UI:x/S:x/C:x/I:x/A:x")
    parts = text.split("/")[1:]
    metrics = {}
    for part in parts:
        k, v = part.split(":")
        metrics[k] = v
    return metrics, None


def calculate_base(vector_text):
    """Calculate CVSS v3.1 base score and severity.

    Returns (metrics, score, severity, error). metrics is None on error.
    """
    metrics, error = parse_vector(vector_text)
    if error:
        return None, 0.0, "None", error

    try:
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}[metrics["AV"]]
        ac = {"L": 0.77, "H": 0.44}[metrics["AC"]]
        scope = metrics["S"]
        pr_tab = {"U": {"N": 0.85, "L": 0.62, "H": 0.27},
                  "C": {"N": 0.85, "L": 0.68, "H": 0.50}}[scope]
        pr = pr_tab[metrics["PR"]]
        ui = {"N": 0.85, "R": 0.62}[metrics["UI"]]
        c = {"H": 0.56, "L": 0.22, "N": 0.00}[metrics["C"]]
        i = {"H": 0.56, "L": 0.22, "N": 0.00}[metrics["I"]]
        a = {"H": 0.56, "L": 0.22, "N": 0.00}[metrics["A"]]
    except KeyError:
        return None, 0.0, "None", "Vector contains an unknown metric value."

    iss = 1 - (1 - c) * (1 - i) * (1 - a)
    if scope == "C":
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    else:
        impact = 6.42 * iss
    exploitability = 8.22 * av * ac * pr * ui

    if impact <= 0:
        score = 0.0
    else:
        score = min(impact + exploitability, 10.0)
        score = _roundup(score)

    return metrics, round(score, 1), severity_from_score(score), None


def severity_from_score(score):
    if score >= 9.0:
        return "Critical"
    if score >= 7.0:
        return "High"
    if score >= 4.0:
        return "Medium"
    if score > 0.0:
        return "Low"
    return "None"


def cvss_metrics_table(text):
    """Return rows (metric, value, score-value) for report tables."""
    metrics, error = parse_vector(text)
    if error or not metrics:
        return []
    rows = []
    for m in METRIC_ORDER:
        name = METRIC_NAMES[m]
        val = METRIC_VALUE_NAMES[m].get(metrics[m], metrics[m])
        rows.append((name, val))
    return rows