import json
import urllib.request
import urllib.error

SYSTEM_PROMPT = (
    "You are an experienced CTF coach inside a cybersecurity training platform. "
    "A trainee is stuck on a challenge and asked for a hint. You must help them "
    "learn WITHOUT giving them the answer outright.\n"
    "Rules:\n"
    "1. Give ONE short, actionable hint (2-4 sentences).\n"
    "2. Escalate help with each hint level: level 1 = gentle nudge, level 2 = the idea/technique, "
    "level 3 = concrete step-by-step approach, level 4+ = near-solution but NEVER the flag itself.\n"
    "3. Never reveal the flag value. Guide them to compute it themselves.\n"
    "4. Mention tools or concepts by name (e.g. CyberChef, strings, volatility, Burp).\n"
    "5. Prefer teaching over spoon-feeding.\n"
    "6. If the trainee already received hints, build on them and avoid repeating them."
)

CATEGORY_FALLBACKS = {
    "Web": [
        "Review every input the page accepts: query strings, paths, headers, cookies, and forms. "
        "A trainer-lab challenge hides the answer in client-side behavior.",
        "Intercept the traffic with Burp Suite or the browser DevTools network tab. Inspect what the "
        "server replies when an unexpected input is sent.",
        "Compare your payload against a known-good one for this category in the training guide, and "
        "make sure special characters survive every layer (URL encoding!).",
    ],
    "Crypto": [
        "Identify the encoding/encryption family from shape: base64 letter set, hex pairs, or "
        "frequency distribution of letters.",
        "Try CyberChef's 'Magic' recipe — it auto-detects common encodings and simple ciphers.",
        "For any custom scheme, brute force small key spaces (or frequencies) mentally or with a "
        "short script.",
    ],
    "Forensics": [
        "First, always run `file` (or examine magic bytes) and `strings` on a suspect file.",
        "Extract embedded content: check for hidden archives, appended data, or trailing bytes "
        "after a known marker.",
        "Use the category's dedicated tool from the lab guide, then look for a human-readable "
        "trail (hex editor search for 'ctf{' or readable ASCII).",
    ],
    "Reversing": [
        "Study the compare: find WHERE input is validated and WHAT it is compared against "
        "(a constant, a transformed copy, a hash...).",
        "Trace backwards from the 'granted' branch to the data it depends on.",
        "If a transformation is applied to input, apply its inverse to the expected value to "
        "recover the flag.",
    ],
    "OSINT": [
        "Search the exact strings you have, one at a time, plus the platform this lab simulates.",
        "Look one hop deeper: profiles link to archives/repositories which link onward.",
        "Flags in OSINT are often constructed from initials or abbreviations in the found text.",
    ],
    "Pwn": [
        "When you crash a program, ask what the crash tells you: which function, which buffer, "
        "which offset?",
        "Control the instruction pointer on purpose: overflow + return address = code execution.",
        "If the binary has protections, pick the simplest lab target path the guide suggests and "
        "follow its exploit template.",
    ],
    "Misc": [
        "Misc is where encodings hide. Run the blob through an automatic decoder first.",
        "If a pattern repeats, suspect base variants, ROT shifts, or binary packing.",
        "Pack every decoded byte into ASCII and look for the ctf{ bracket.",
    ],
}

GENERIC = [
    "You have used every prepared hint. Switch strategy: restate what the challenge literally "
    "asks for, then list every input the problem gives you.",
    "Ask yourself what a trainer would automate to verify this. The verification step usually "
    "mirrors the attack step.",
    "Read the lab guide notes for this category — the intended tool is named there.",
]


def _settings_for(settings):
    return {
        "provider": settings.get("provider", "local"),
        "base_url": (settings.get("base_url") or "").strip().rstrip("/"),
        "api_key": settings.get("api_key") or "",
        "model": settings.get("model") or "",
        "enabled": str(settings.get("enabled", "0")) in ("1", "true", "True"),
    }


def _call(settings, system, user, timeout=45):
    cfg = _settings_for(settings)
    if cfg["provider"] in ("openai", "openai_compatible"):
        endpoint = (cfg["base_url"] or "https://api.openai.com/v1") + "/chat/completions"
        body = json.dumps({
            "model": cfg["model"] or "gpt-4o-mini",
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.7,
            "max_tokens": 400,
        }).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, method="POST", headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
            "User-Agent": "CTFHintEngine/1.0",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    if cfg["provider"] == "anthropic":
        endpoint = (cfg["base_url"] or "https://api.anthropic.com") + "/v1/messages"
        body = json.dumps({
            "model": cfg["model"] or "claude-sonnet-4-20250514",
            "max_tokens": 400,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, method="POST", headers={
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": "CTFHintEngine/1.0",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"]

    raise ValueError(f"Unsupported provider: {cfg['provider']}")


def _local_hint(challenge, level):
    idx = min((level - 4), 2) if level >= 4 else 0
    bucket = CATEGORY_FALLBACKS.get(challenge["category"], GENERIC)
    if level >= 4:
        start = max(0, idx)
        texts = bucket + GENERIC
        return texts[min(level - 4, len(texts) - 1)]
    return GENERIC[level - 1]


def make_hint(store, challenge, history, settings):
    authored = challenge.get("hints_json") or []
    level = len(history) + 1

    if len(history) < len(authored):
        text = authored[len(history)]
        return {"level": level, "source": "authored", "content": text}

    cfg = _settings_for(settings)
    if cfg["enabled"] and cfg["api_key"]:
        prior = "\n".join(f"Hint {h['level']} ({h['source']}): {h['content']}" for h in history) or "none yet"
        user = (
            f"Challenge: {challenge['title']}\n"
            f"Category: {challenge['category']}\n"
            f"Difficulty: {challenge['difficulty']}\n"
            f"Description:\n{challenge['description']}\n\n"
            f"Hints already given:\n{prior}\n\n"
            f"Create hint level {level}."
        )
        try:
            text = _call(settings, SYSTEM_PROMPT, user)
            text = " ".join(text.split())
            if len(text) > 1200:
                text = text[:1200] + "..."
            if text:
                return {"level": level, "source": "ai", "content": text}
        except Exception:
            pass

    fallback = _local_hint(challenge, level)
    return {"level": level, "source": "local", "content": fallback}


def test_connection(settings):
    cfg = _settings_for(settings)
    if not cfg["enabled"]:
        return {"ok": False, "error": "AI engine is disabled."}
    if not cfg["api_key"]:
        return {"ok": False, "error": "No API key configured."}
    try:
        text = _call(settings, "Reply with the single word OK.",
                     "Connection test from CTF Hint Engine.", timeout=30)
        return {"ok": True, "reply": " ".join(text.split())[:300]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Network error: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}