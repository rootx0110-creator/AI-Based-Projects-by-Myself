"""Tests for skill modules and the skills runner."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.skills_runner import get_skills, run_analysis, run_responses  # noqa: E402
from app.engine.ioc_extractor import extract_iocs                            # noqa: E402


def test_skills_discovered():
    names = [s.__name__ for s in get_skills()]
    for expected in ("phishing_skill", "malware_skill", "credential_skill",
                     "network_skill", "vulnerability_skill", "exfiltration_skill",
                     "playbook_skill", "summary_skill"):
        assert any(n.endswith(expected) for n in names), f"missing {expected}"


def test_phishing_skill_lookalike():
    text = "Phishing email from ceo@micros0ft-secure-login.com with URGENT wire transfer request, attachment Invoice.xlsm"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    p = analysis["phishing"]
    assert p["lookalike_of"] == "microsoft"
    assert p["risk_score"] >= 60


def test_credential_skill():
    text = "Mimikatz detected on DC01, LSASS dump, pass-the-hash activity observed"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    c = analysis["credential"]
    assert c["dumping_tools"]
    assert c["pass_the_hash"]
    assert c["risk_score"] >= 60


def test_network_skill():
    text = "C2 beacon to 45.33.32.156 port 4444, dns tunneling suspected"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    n = analysis["network"]
    assert n["beaconing"]
    assert n["tunneling"]
    assert 4444 in n["ports"]


def test_vulnerability_skill():
    text = "Public facing server hit by ProxyLogon exploitation attempt, web shell dropped"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    v = analysis["vulnerability"]
    assert any(n["cve"] == "CVE-2021-26855" for n in v["named_vulns"])
    assert v["web_shell"]


def test_exfiltration_skill():
    text = "DLP alert: user uploaded PII customer data to personal Dropbox, encrypted archive, leaving company"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    e = analysis["exfiltration"]
    assert e["risk_score"] >= 60


def test_summary_and_playbook_present():
    text = "Ransomware LockBit detected, files encrypted, shadow copies deleted on FS01"
    iocs = extract_iocs(text)
    analysis = run_analysis(text, iocs, {})
    responses = "\n".join(run_responses(text, iocs, analysis, {}))
    assert "Playbook" in responses
    assert "Executive Triage Summary" in responses
