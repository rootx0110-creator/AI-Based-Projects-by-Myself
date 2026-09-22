# 🛡 SOC Triage Assistant — AI Chatbot for Tier-1 SOC Triage

A self-contained **web application** (packagable to a single **.exe**) that helps
Tier-1 SOC analysts triage alerts faster. Paste any alert (SIEM, EDR, email
gateway, firewall) and the assistant:

- 🔍 **Extracts IOCs** — file hashes (MD5/SHA1/SHA256), domains, URLs, IPs,
  emails, filenames, CVE IDs
- 🎯 **Maps MITRE ATT&CK techniques** with tactics and match strength
- 🚦 **Scores severity 0–100** with a transparent scoring breakdown
- 🧠 **Runs 8 modular skills**: phishing, malware, credential/identity, network/C2,
  vulnerability, exfiltration/insider, playbook advisor, executive summary
- 📋 **Recommends a response playbook** matched to the alert category
- 📄 **Generates a downloadable HTML report** (single file, print/PDF-ready)
- 🤖 **Hybrid AI**: fully offline deterministic engine + optional LLM narrative
  (OpenAI/OpenRouter/Ollama — any OpenAI-compatible endpoint)

## Quick Start

```bash
pip install -r requirements.txt
python run.py
# Opens http://127.0.0.1:8756 automatically (set PORT env var to change)
```

## Build a single .exe

```bash
pip install -r requirements.txt   # includes pyinstaller
python build_exe.py
# Produces dist/SOC_Triage_Assistant.exe
# Run it → browser opens automatically at http://127.0.0.1:8756
```

## Optional: enable LLM enhancement

The app works 100% offline by default. To add LLM narrative analysis:

```bash
export LLM_API_KEY=sk-...          # required
export LLM_BASE_URL=https://api.openai.com/v1   # or https://openrouter.ai/api/v1 or http://localhost:11434/v1
export LLM_MODEL=gpt-4o-mini       # or any chat model your endpoint serves
```

When the key is present, the UI badge switches to **“LLM connected”** and chat
replies include an analyst narrative. If the API errors or the key is absent,
the deterministic engine response is returned unchanged — never a failure.

## Project Layout

```
app/
  server.py            Flask routes (/ , /health, /api/chat, /api/report)
  report_generator.py  Self-contained HTML report builder
  engine/
    ioc_extractor.py   Regex IOC extraction (hash/domain/URL/IP/email/file/CVE)
    mitre_mapper.py    ATT&CK technique keyword mapping
    severity_engine.py 0–100 scoring with reasons
    skills_runner.py   Discovers & runs skill modules
    brain.py           Orchestrates full triage pipeline
    llm.py             Optional OpenAI-compatible LLM client
  skills/              8 modular skills (auto-discovered)
    phishing_skill.py
    malware_skill.py
    credential_skill.py
    network_skill.py
    vulnerability_skill.py
    exfiltration_skill.py
    playbook_skill.py
    summary_skill.py
templates/index.html  Chat UI (dark smart-color theme)
tests/                Unit tests (engine + skills)
run.py                Entry point (python run.py)
build_exe.py          PyInstaller single-exe build script
```

## API

| Route | Method | Body | Response |
|-------|--------|------|----------|
| `/` | GET | — | Chat UI |
| `/health` | GET | — | `{status, llm_available}` |
| `/api/chat` | POST | `{"message": "alert text"}` | Full triage JSON + `chat_reply` |
| `/api/report` | POST | `{"message": "alert text"}` | `text/html` attachment download |

## Skills Contract

Drop a new `*_skill.py` into `app/skills/` and it is auto-discovered. Optional
exports:

```python
PRIORITY = 100              # lower runs earlier
KEYWORDS = ["c2", "beacon"] # skill activates when any appear (omit = always)
def analyze(text, iocs, context) -> dict   # merged into analysis
def respond(text, iocs, analysis, context) -> str  # markdown chat section
def report_section(analysis) -> {"title": str, "html": str}
```

## Notes

- Scoring is decision-support: always validate before disposition.
- No data leaves the machine unless `LLM_API_KEY` is set.
- Reports are single-file HTML — safe to attach to tickets or email.
