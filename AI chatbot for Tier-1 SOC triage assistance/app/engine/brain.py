"""Hybrid triage brain: offline deterministic engine + optional LLM enhancement.

The offline path ALWAYS works: IOC extraction, MITRE ATT&CK mapping, severity
scoring, skills analysis, playbook recommendation and executive summary.
If an LLM API key is configured, an extra analyst-narrative section is added.
"""
import json

from app.engine.ioc_extractor import extract_iocs, utc_now_iso
from app.engine.mitre_mapper import map_attack
from app.engine.severity_engine import compute_severity, SEVERITY_COLORS
from app.engine.skills_runner import run_analysis, run_responses, run_report_sections
from app.engine import llm


def triage(text, use_llm=None):
    """Full triage pipeline. Returns the analysis context dict."""
    text = (text or "").strip()
    iocs = extract_iocs(text)
    attack_matches = map_attack(text, iocs)
    severity = compute_severity(text, iocs, attack_matches)

    context = {
        "input_text": text,
        "timestamp": utc_now_iso(),
        "iocs": iocs,
        "attack_matches": attack_matches,
        "severity": severity,
        "llm_used": False,
    }

    analysis = run_analysis(text, iocs, context)
    # stash raw text for playbook ransomware shortcut
    analysis["_raw_text"] = text
    context["analysis"] = analysis

    skill_sections = run_report_sections(analysis)
    context["skill_sections"] = skill_sections

    # Optional LLM narrative (hybrid mode)
    should_use = llm.is_configured() if use_llm is None else bool(use_llm)
    if should_use and llm.is_configured() and text:
        narrative, meta = llm.enhance(text, iocs, severity, attack_matches)
        context["llm_narrative"] = narrative
        context["llm_meta"] = meta
        context["llm_used"] = narrative is not None

    return context


def chat_reply(context):
    """Build the markdown chat reply from the triage context."""
    sev = context.get("severity", {})
    iocs = context.get("iocs", {})
    matches = context.get("attack_matches", [])
    analysis = context.get("analysis", {})

    lines = []
    lines.append(
        f"## Triage Result — {sev.get('severity', 'UNKNOWN')} "
        f"(risk {sev.get('score', 0)}/100)")

    # IOC digest
    ioc_bits = []
    for kind, label in (("hashes", "hashes"), ("domains", "domains"),
                        ("urls", "URLs"), ("ips", "IPs"), ("emails", "emails"),
                        ("filenames", "files"), ("cves", "CVEs")):
        if iocs.get(kind):
            ioc_bits.append(f"{len(iocs[kind])} {label}")
    lines.append("**Indicators:** " + (", ".join(ioc_bits) if ioc_bits else "none detected"))

    if matches:
        tech = ", ".join(f"`{m['id']}` {m['name']}" for m in matches[:5])
        lines.append(f"**MITRE ATT&CK:** {tech}")

    # Skill narrative parts
    for part in run_responses(context.get("input_text", ""), iocs, analysis, context):
        lines.append("")
        lines.append(part)

    # LLM narrative if available
    if context.get("llm_used") and context.get("llm_narrative"):
        lines.append("")
        lines.append("**🤖 LLM Analyst Narrative**")
        lines.append(context["llm_narrative"])

    if sev.get("reasons"):
        lines.append("")
        lines.append("<details><summary>Scoring breakdown</summary>")
        for r in sev["reasons"]:
            lines.append(f"- {r}")
        lines.append("</details>")

    return "\n".join(lines)


def severity_color(sev_label):
    return SEVERITY_COLORS.get(sev_label, "#888888")


def compact_summary(context):
    """Small dict for the UI cards."""
    sev = context.get("severity", {})
    iocs = context.get("iocs", {})
    return {
        "severity": sev.get("severity"),
        "color": severity_color(sev.get("severity")),
        "score": sev.get("score"),
        "ioc_total": sum(len(v) for v in iocs.values() if isinstance(v, list)),
        "techniques": [m["id"] for m in context.get("attack_matches", [])[:5]],
        "llm_used": context.get("llm_used", False),
    }


def to_json(context):
    """JSON-safe view for the API."""
    payload = {
        "timestamp": context.get("timestamp"),
        "severity": context.get("severity"),
        "iocs": context.get("iocs"),
        "attack_matches": context.get("attack_matches"),
        "analysis": {k: v for k, v in context.get("analysis", {}).items()
                     if not k.startswith("_")},
        "skill_sections": context.get("skill_sections"),
        "chat_reply": chat_reply(context),
        "summary": compact_summary(context),
        "llm_used": context.get("llm_used", False),
    }
    return json.loads(json.dumps(payload, default=str))
