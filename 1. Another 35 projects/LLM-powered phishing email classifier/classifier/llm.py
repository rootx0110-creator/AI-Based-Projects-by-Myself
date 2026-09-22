"""Optional LLM deep-dive analyzer.

Talks to any OpenAI-compatible chat completions endpoint (cloud or
local). Results are cached by content hash so identical emails are not
re-sent. The model is forced to return strict JSON.

Config keys (config.ini under [llm] or runtime settings):
    enabled  0/1
    api_base https://...
    api_key  your key (use "ollama" for local Ollama)
    model    model name
    timeout  seconds
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

from .parser import ParsedEmail

MAX_BODY_CHARS = 4000

_built_defaults = {
    "enabled": "0",
    "api_base": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "timeout": "30",
}


def load_settings() -> dict:
    cfg = configparser.ConfigParser()
    settings = dict(_built_defaults)

    base_dir = Path(getattr(__import__("sys"), "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidates = [base_dir / "config.ini",
                  Path(__file__).resolve().parent.parent / "config.ini"]
    for c in candidates:
        try:
            if c.exists():
                cfg.read(c, encoding="utf-8")
                if cfg.has_section("llm"):
                    for k in settings:
                        if cfg.has_option("llm", k):
                            settings[k] = cfg.get("llm", k, fallback=settings[k])
                return settings
        except Exception:
            continue
    return settings


def save_settings(new_settings: dict) -> dict:
    """Persist LLM settings to config.ini in the app folder."""
    merged = load_settings()
    merged.update({k: str(v) for k, v in new_settings.items() if k in merged})

    output = Path(__file__).resolve().parent.parent / "config.ini"
    cfg = configparser.ConfigParser()
    cfg["llm"] = {
        "enabled": merged["enabled"],
        "api_base": merged["api_base"],
        "api_key": merged["api_key"],
        "model": merged["model"],
        "timeout": merged["timeout"],
    }
    with open(output, "w", encoding="utf-8") as fh:
        cfg.write(fh)
    return merged


_cache: dict[str, dict] = {}


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", "ignore")).hexdigest()


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
    return json.loads(text)


PROMPT = """You are a cybersecurity email analyst. Analyze the email below and classify it.

Return STRICT JSON only, no prose. Schema:
{{
  "verdict": "safe" | "suspicious" | "phishing",
  "confidence": <integer 0-100>,
  "reasons": [<array of short strings explaining signals>],
  "tactics": [<array of phishing tactics identified, or []>],
  "suggested_action": "<one sentence for the recipient>"
}}

Verdict guidance:
- phishing: strong indicators (spoofed brand, credential bait, urgency + link to unknown host, mismatched reply-to, executable attachment).
- suspicious: some mild indicators but not conclusive.
- safe: legitimate-looking, matches sender domain, no credential bait or deceptive links.

EMAIL:
From: {sender}
To: {rcpt}
Subject: {subject}
Date: {date}

BODY:
{body}
"""


def _is_boolish(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on", "enabled")


def is_available(settings: dict | None = None) -> bool:
    s = settings or load_settings()
    return _is_boolish(s.get("enabled", "0")) and bool(s.get("api_key") or "")


def analyze(email: ParsedEmail, settings: dict | None = None) -> dict | None:
    s = settings or load_settings()
    if not is_available(s):
        return None

    content = json.dumps(email.to_dict(), ensure_ascii=False)
    key = _content_hash(content)
    if key in _cache:
        return dict(_cache[key])

    base = (s.get("api_base") or "").rstrip("/") + "/"
    url = urljoin(base, "chat/completions")

    body_text = email.body or ""
    if len(body_text) > MAX_BODY_CHARS:
        body_text = body_text[:MAX_BODY_CHARS] + "\n[truncated]"

    payload = {
        "model": s.get("model", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": "You are a strict JSON-only security analyst."},
            {"role": "user", "content": PROMPT.format(
                sender=email.from_display or email.from_email,
                rcpt=email.to or "(unknown)",
                subject=email.subject or "(none)",
                date=email.date or "(none)",
                body=body_text)},
        ],
        "temperature": 0.1,
        "max_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {s.get('api_key', '')}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers,
                             timeout=int(s.get("timeout", "30")))
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = _extract_json(content)
        result.setdefault("verdict", "suspicious")
        result.setdefault("confidence", 50)
        result.setdefault("reasons", [])
        result.setdefault("tactics", [])
        result.setdefault("suggested_action", "")
        if result["verdict"] not in ("safe", "suspicious", "phishing"):
            result["verdict"] = "suspicious"
        result["confidence"] = int(max(0, min(100, int(result["confidence"]))))
        result["model"] = s.get("model")
        _cache[key] = result
        return dict(result)
    except Exception as exc:  # never break a scan because the LLM failed
        return {"error": str(exc), "verdict": "suspicious", "confidence": 0,
                "reasons": [f"LLM unavailable: {exc}"], "tactics": [],
                "suggested_action": "Run without LLM; rely on heuristic verdict."}


if __name__ == "__main__":
    print(json.dumps(load_settings(), indent=2))