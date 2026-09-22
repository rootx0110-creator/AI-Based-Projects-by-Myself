"""Optional LLM enhancement (hybrid mode).

Supports OpenAI-compatible APIs (OpenAI, OpenRouter, Azure-style gateways,
local Ollama/vLLM with /v1/chat/completions). Configure via env vars:

    LLM_API_KEY   -> API key (required to enable)
    LLM_BASE_URL  -> default https://api.openai.com/v1
    LLM_MODEL     -> default gpt-4o-mini

Everything degrades gracefully: if unset or the call fails, the offline
deterministic analysis is used unchanged.
"""
import os

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
TIMEOUT = 25


def is_configured():
    return bool(os.environ.get("LLM_API_KEY"))


def _base_url():
    return (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _model():
    return os.environ.get("LLM_MODEL") or DEFAULT_MODEL


SYSTEM_PROMPT = (
    "You are a Tier-1 SOC triage assistant. You receive an alert and a "
    "deterministic analysis (IOCs, MITRE ATT&CK matches, severity). Write a "
    "concise analyst narrative (max 180 words): what likely happened, why it "
    "matters, biggest risk, and the single most important next step. Use plain "
    "professional language. Do not invent IOCs that are not listed. Never claim "
    "certainty the evidence does not support."
)


def _build_user_prompt(text, iocs, severity, attack_matches):
    ioc_lines = []
    for kind in ("hashes", "domains", "urls", "ips", "emails", "filenames", "cves"):
        vals = iocs.get(kind) or []
        if vals:
            ioc_lines.append(f"{kind}: {', '.join(vals[:8])}")
    tech = ", ".join(f"{m['id']} {m['name']} ({m['tactic']})" for m in attack_matches[:5]) or "none"
    return (
        f"ALERT:\n{text[:2000]}\n\n"
        f"DETERMINISTIC ANALYSIS:\n"
        f"Severity: {severity.get('severity')} ({severity.get('score')}/100)\n"
        f"IOCs:\n" + ("\n".join(ioc_lines) or "none") + "\n"
        f"ATT&CK techniques: {tech}\n"
    )


def enhance(text, iocs, severity, attack_matches):
    """Return (narrative|None, meta_dict). Never raises."""
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None, {"enabled": False, "reason": "no API key"}

    url = f"{_base_url()}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(text, iocs, severity, attack_matches)},
        ],
        "temperature": 0.2,
        "max_tokens": 350,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        narrative = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        if not narrative:
            return None, {"enabled": True, "reason": "empty response"}
        return narrative.strip(), {
            "enabled": True, "model": _model(),
            "base_url": _base_url(),
        }
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        return None, {"enabled": True, "reason": f"error: {exc.__class__.__name__}"}
