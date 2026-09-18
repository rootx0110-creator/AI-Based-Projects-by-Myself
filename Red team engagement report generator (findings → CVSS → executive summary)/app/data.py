"""Findings data model and JSON persistence."""

import json
import os
import re
import sys
import uuid
from datetime import date

from . import cvss

SEVERITIES = ["Critical", "High", "Medium", "Low", "None"]
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "None": 4}

STATUSES = ["Open", "In Progress", "Fixed", "Accepted", "Closed"]


def app_dir():
    """Directory where the app / exe lives (writable for the JSON store)."""
    if hasattr(sys, "frozen"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_file():
    return os.path.join(app_dir(), "redteam_data.json")


def default_engagement():
    return {
        "engagement_title": "",
        "client_name": "",
        "assessor": "",
        "start_date": date.today().strftime("%Y-%m-%d"),
        "end_date": date.today().strftime("%Y-%m-%d"),
        "scope": "",
        "summary_notes": "",
    }


class Finding:
    def __init__(self, title="", cvss_vector="", affected_assets="",
                 description="", impact="", evidence="", remediation="",
                 references="", status="Open"):
        self.id = uuid.uuid4().hex[:12]
        self.title = title
        self.cvss_vector = cvss_vector
        self.affected_assets = affected_assets
        self.description = description
        self.impact = impact
        self.evidence = evidence
        self.remediation = remediation
        self.references = references
        self.status = status

    @property
    def score(self):
        _, score, _, _ = cvss.calculate_base(self.cvss_vector)
        return score

    @property
    def severity(self):
        _, _, sev, _ = cvss.calculate_base(self.cvss_vector)
        return sev

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "cvss_vector": self.cvss_vector,
            "affected_assets": self.affected_assets,
            "description": self.description,
            "impact": self.impact,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "references": self.references,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d):
        f = cls()
        f.id = d.get("id", uuid.uuid4().hex[:12])
        f.title = d.get("title", "")
        f.cvss_vector = d.get("cvss_vector", "")
        f.affected_assets = d.get("affected_assets", "")
        f.description = d.get("description", "")
        f.impact = d.get("impact", "")
        f.evidence = d.get("evidence", "")
        f.remediation = d.get("remediation", "")
        f.references = d.get("references", "")
        f.status = d.get("status", "Open")
        return f


class ReportStore:
    """Holds engagement settings + findings, persists to JSON."""

    def __init__(self, path=None):
        self.path = path or data_file()
        self.engagement = default_engagement()
        self.findings = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            eng = raw.get("engagement", {})
            for key in self.engagement:
                if key in eng:
                    self.engagement[key] = eng[key]
            self.findings = [Finding.from_dict(x) for x in raw.get("findings", [])]
        except (FileNotFoundError, json.JSONDecodeError):
            self.findings = []

    def save(self):
        payload = {
            "engagement": self.engagement,
            "findings": [f.to_dict() for f in self.findings],
        }
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def add(self, finding):
        self.findings.append(finding)
        self.save()

    def remove(self, finding):
        if finding in self.findings:
            self.findings.remove(finding)
            self.save()

    def update(self):
        self.save()

    def severity_counts(self):
        counts = {s: 0 for s in SEVERITIES}
        for f in self.findings:
            counts[f.severity if f.severity in counts else "None"] += 1
        return counts

    def sorted_findings(self):
        order = SEVERITY_ORDER
        return sorted(self.findings,
                      key=lambda f: (order.get(f.severity, 9), -f.score))


def slugify(text):
    text = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower())
    return text.strip("_") or "report"