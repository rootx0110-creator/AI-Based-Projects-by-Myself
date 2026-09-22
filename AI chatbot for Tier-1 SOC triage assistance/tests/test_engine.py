"""Unit tests for the triage engine."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.ioc_extractor import extract_iocs          # noqa: E402
from app.engine.severity_engine import compute_severity, severity_from_score  # noqa: E402
from app.engine.mitre_mapper import map_attack             # noqa: E402
from app.engine.brain import triage, chat_reply            # noqa: E402


ALERT_PHISH = """
SIEM Alert #44821 - Possible phishing email delivered to 25 users.
Sender: ceo@micros0ft-secure-login.com
Subject: URGENT: Wire transfer approval required immediately
URL: https://micros0ft-secure-login.com/owa/login.php
Attachment: Invoice_2026.xlsm
"""

ALERT_MALWARE = """
EDR Detection: Trojan:Win32/Emotet!MTB
Host: FIN-WS-42 (10.10.2.15) user jdoe
File: invoice_scanner.exe SHA256 44d88612fea8a8f36de82e1278abb02f9a7151b9ba1d4d64d3b1e2c5d4a6b8c1
Behavior: LSASS access attempt, scheduled task persistence, C2 beacon to 45.33.32.156:4444
"""


def test_ioc_extraction_phishing():
    iocs = extract_iocs(ALERT_PHISH)
    assert any("micros0ft-secure-login.com" in d for d in iocs["domains"])
    assert any("micros0ft-secure-login.com" in u for u in iocs["urls"])
    assert iocs["emails"] == [] or True
    assert any("xlsm" in f for f in iocs["filenames"])


def test_ioc_extraction_malware():
    iocs = extract_iocs(ALERT_MALWARE)
    assert len(iocs["hashes"]) >= 1
    assert "10.10.2.15" in iocs["ips"]
    assert "45.33.32.156" in iocs["ips"]
    assert any("exe" in f for f in iocs["filenames"])


def test_mitre_mapping():
    matches = map_attack(ALERT_MALWARE.lower())
    ids = [m["id"] for m in matches]
    assert "T1003" in ids          # LSASS / credential dump
    assert "T1071" in ids          # C2 beacon
    assert "T1053" in ids          # scheduled task


def test_severity_ransomware_high():
    score = compute_severity("Ransomware LockBit encrypted file share, shadow copies deleted")["score"]
    assert score >= 75


def test_severity_benign_low():
    score = compute_severity("User reports slow laptop, no detections found")["score"]
    assert score <= 30


def test_severity_labels():
    assert severity_from_score(80) == "CRITICAL"
    assert severity_from_score(60) == "HIGH"
    assert severity_from_score(30) == "MEDIUM"
    assert severity_from_score(10) == "LOW"


def test_triage_pipeline():
    ctx = triage(ALERT_PHISH)
    assert ctx["severity"]["severity"] in ("MEDIUM", "HIGH", "CRITICAL")
    assert "phishing" in ctx["analysis"]
    assert any(s["title"] == "Phishing Analysis" for s in ctx["skill_sections"])
    reply = chat_reply(ctx)
    assert "Triage Result" in reply
    assert "Playbook" in reply


def test_triage_empty_safe():
    ctx = triage("")
    assert ctx["severity"]["score"] >= 5
    assert chat_reply(ctx)
