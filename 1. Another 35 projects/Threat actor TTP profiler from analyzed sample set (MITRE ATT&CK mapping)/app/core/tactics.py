"""ATT&CK tactic ordering and display colors (Navigator palette)."""

TACTIC_ORDER = [
    "reconnaissance",
    "resource-development",
    "initial-access",
    "execution",
    "persistence",
    "privilege-escalation",
    "defense-evasion",
    "credential-access",
    "discovery",
    "lateral-movement",
    "collection",
    "command-and-control",
    "exfiltration",
    "impact",
]

TACTIC_LABELS = {
    "reconnaissance": "Reconnaissance",
    "resource-development": "Resource Development",
    "initial-access": "Initial Access",
    "execution": "Execution",
    "persistence": "Persistence",
    "privilege-escalation": "Privilege Escalation",
    "defense-evasion": "Defense Evasion",
    "credential-access": "Credential Access",
    "discovery": "Discovery",
    "lateral-movement": "Lateral Movement",
    "collection": "Collection",
    "command-and-control": "Command and Control",
    "exfiltration": "Exfiltration",
    "impact": "Impact",
}

# green-ish scale used by the ATT&CK Navigator for technique scores
HEATMAP_SCALE = [
    "#fefefe",  # 0 - none
    "#9fce63",  # low
    "#77b2de",  # medium-ish
    "#8bafe9",
    "#5f9cd4",
    "#fceb3a",
    "#f5b731",
    "#f08228",
    "#e5412c",
]


def heat_color(value: float) -> str:
    """Map a 0..100 score to a Navigator-style color."""
    if value <= 0:
        return HEATMAP_SCALE[0]
    if value >= 100:
        return HEATMAP_SCALE[-1]
    idx = 1 + int((value / 100) * (len(HEATMAP_SCALE) - 2))
    idx = max(1, min(len(HEATMAP_SCALE) - 1, idx))
    return HEATMAP_SCALE[idx]