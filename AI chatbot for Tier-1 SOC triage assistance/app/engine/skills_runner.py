"""Skills loader for the SOC triage assistant.

Skills are modular capability modules in app/skills/. Each skill module can
export any of:
    PRIORITY   -> int, lower runs earlier
    KEYWORDS   -> list of trigger words; skill activates if any appear
    analyze(text, iocs, context) -> dict (merged into analysis)
    respond(text, iocs, analysis, context) -> str (markdown-ish chat reply part)
    report_section(analysis) -> dict {title, html} appended to reports
"""
import importlib
import pkgutil

from app.skills import __path__ as _SKILLS_PATH

# Explicit fallback for frozen (PyInstaller) builds where pkgutil cannot
# list archive contents. Keep in sync with app/skills/ contents.
_FALLBACK_MODULES = [
    "playbook_skill", "phishing_skill", "malware_skill", "credential_skill",
    "network_skill", "vulnerability_skill", "exfiltration_skill", "summary_skill",
]

_SKILLS = None


def _discover():
    mods = []
    try:
        for m in pkgutil.iter_modules(_SKILLS_PATH):
            if m.name.startswith("_"):
                continue
            mods.append(importlib.import_module(f"app.skills.{m.name}"))
    except Exception:
        mods = []
    if not mods:
        # Frozen exe fallback: import the known skills directly
        for name in _FALLBACK_MODULES:
            try:
                mods.append(importlib.import_module(f"app.skills.{name}"))
            except Exception:
                continue
    mods.sort(key=lambda x: getattr(x, "PRIORITY", 100))
    return mods


def get_skills():
    global _SKILLS
    if _SKILLS is None:
        try:
            _SKILLS = _discover()
        except Exception:
            _SKILLS = []
    return _SKILLS


def _matches(skill, text):
    keywords = getattr(skill, "KEYWORDS", None)
    if not keywords:
        return True
    low = (text or "").lower()
    return any(kw.lower() in low for kw in keywords)


def run_analysis(text, iocs, context):
    """Merge analyze() results from all matching skills."""
    analysis = {}
    for skill in get_skills():
        if not _matches(skill, text):
            continue
        fn = getattr(skill, "analyze", None)
        if not callable(fn):
            continue
        try:
            out = fn(text, iocs, context)
            if isinstance(out, dict):
                analysis.update(out)
        except Exception:
            continue
    return analysis


def run_responses(text, iocs, analysis, context):
    """Concatenate respond() markdown from all matching skills."""
    parts = []
    for skill in get_skills():
        if not _matches(skill, text):
            continue
        fn = getattr(skill, "respond", None)
        if not callable(fn):
            continue
        try:
            out = fn(text, iocs, analysis, context)
            if out:
                parts.append(out)
        except Exception:
            continue
    return parts


def run_report_sections(analysis):
    """Collect report_section() dicts from all skills."""
    sections = []
    for skill in get_skills():
        fn = getattr(skill, "report_section", None)
        if not callable(fn):
            continue
        try:
            out = fn(analysis)
            if isinstance(out, dict) and out.get("html"):
                sections.append(out)
        except Exception:
            continue
    return sections
