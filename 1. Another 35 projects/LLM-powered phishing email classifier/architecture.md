# Architecture - LLM-Powered Phishing Email Classifier

## 1. Overview

Web application that classifies emails as SAFE / SUSPICIOUS / PHISHING.
It combines a deterministic heuristic engine with an optional LLM
deep-dive, fuses both signals into a single verdict, and renders a
downloadable HTML security report.

```
                     +-----------------------------------------------------+
                     |                    BROWSER                          |
                     |  glassmorphism dark UI + report viewer/download     |
                     +--------------------------+--------------------------+
                                                | HTTP (Flask)
                     +--------------------------v--------------------------+
                     |                      app.py                         |
                     |  routes: GET / , POST /api/scan , GET /api/health  |
                     +----------+---------------------------+-------------+
                                |                           |
                 +--------------v--------------+   +--------v--------+
                 |  classifier/service.py     |   | report/render.py |
                 |  orchestrates the pipeline |   | HTML report      |
                 +--------------+--------------+   +-----------------+
                                |
                 +--------------v----------------------------------+
                 |                SCORING PIPELINE                 |
                 |                                                 |
                 |  1. parser        -> normalized email fields     |
                 |  2. extractor     -> 25+ signal features         |
                 |  3. heuristic     -> weighted risk score + flags  |
                 |  4. LLM (opt.)    -> analysis + verdict (cached) |
                 |  5. fusion        -> final verdict + confidence   |
                 +-------------------------------------------------+
```

## 2. Components

### 2.1 Parser - `classifier/parser.py`
Splits raw email text into header fields (From, To, Subject, Date) and
body. Handles both plain raw text and basic EML-ish input.

### 2.2 Extractor - `classifier/extractor.py`
Builds feature set for one email:
- URL inventory (http/https, shorteners, IP-literal hosts, @ in URL)
- Sender-domain lookalike checks (e.g. "paypal-security.com" vs paypal.com)
- Brand-impersonation keywords (paypal, apple, microsoft, bank, ...)
- Suspicious phrase battery (urgent, verify, password expired, ...)
- Credential-bait pattern (password reset, account locked, wire transfer)
- Attachment hints (invoice.PDF.exe-style names)
- Header red flags (Reply-To mismatch, mismatched sender domain)

### 2.3 Heuristic Engine - `classifier/heuristic.py`
Each detected signal has a weight. Weights sum to a raw score that is
mapped to a 0-100 risk index and a preliminary verdict:
  risk < 35  -> SAFE
  < 70       -> SUSPICIOUS
  else       -> PHISHING
Returns flags (why) so the UI/report can list evidence.

### 2.4 LLM Analyzer - `classifier/llm.py`
If an OpenAI-compatible endpoint is configured (config.ini or UI
settings), asks the model to output strict JSON:
  {"verdict": "phishing|suspicious|safe",
   "confidence": 0-100,
   "reasons": [...], "tactics": [...], "suggested_action": "..."}
Responses are cached by content hash (SHA-256) in an in-memory keyed
cache to avoid repeated calls.

### 2.5 Fusion - `classifier/fusion.py`
Fusion decides the final verdict and confidence:
- If LLM is off  -> verdict from heuristics.
- If LLM is on   -> weighted combination where heuristic risk
  dominates at extremes and the LLM shifts the confidence band
  otherwise. Reasons from both are merged and de-duplicated.

### 2.6 Report - `report/render.py`
Generates a fully self-contained HTML document: verdict banner,
risk gauge, confidence, evidence table, tactic tags, LLM reasoning
and the analyzed email body. Styles are inlined so the file is
portable/printable.

## 3. Data flow (a scan)

1. Client POSTs {email, from, to, subject, options} to /api/scan.
2. Parser normalizes input.
3. Extractor computes feature vector.
4. Heuristic engine scores it.
5. (Optional) LLM analyzes; result cached.
6. Fusion returns {verdict, confidence, risk, flags, evidence,
   llm, analysis_id} + signed report content.
7. Client renders verdict with animation; user may download the
   HTML report (GET /api/report/<analysis_id>).

## 4. Tech choices

| Concern          | Choice                          | Why                          |
|------------------|---------------------------------|------------------------------|
| Server           | Flask (single file)             | Zero DB, easy EXE packaging  |
| Frontend         | Vanilla JS + CSS                | No node build step           |
| ML heuristics    | Weighted rule engine            | Deterministic, explainable   |
| LLM              | HTTP OpenAI-compatible API      | Works with cloud + local     |
| Packaging        | PyInstaller onefile (windowed)  | Ships static/templates       |
| Styling          | Glassmorphism + neon gradients  | "wow" factor, dark UI        |

## 5. Threat model considered

- XSS: rendered report content is HTML-entity escaped before injection
  into templates.
- Prompt injection: LLM prompt bounds the model's output to strict
  JSON; sample content is truncated to a max length before sending.
- Data privacy: no persistence of email content by default; hashing is
  one-way for cache keys. LLM use is opt-in.

## 6. Future evolution

- Add an EMAIL-PARSED upload path and batch mode.
- Swap rule weights to a trained Logistic Regression model over the
  feature vector (keep explainability by reporting SHAP-like weights).
- Enrich with URL reputation APIs behind an optional toggle.