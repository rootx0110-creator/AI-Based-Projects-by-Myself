# State - LLM-Powered Phishing Email Classifier

Date: 2026-09-21
Milestone: MVP complete (web app + standalone EXE)

## Current status
- Heuristic engine + extractor: DONE. 25+ signals incl. brand lookalike
  detection with leet-decode (paypa1 -> paypal), trusted-domain allowlist,
  URL/header/attachment/phrase analysis, financial-lure patterns.
- Scoring: exponential saturation risk mapping (lam=48), verified against
  sample sets below.
- LLM deep-dive: DONE (OpenAI-compatible, cached, strict-JSON, opt-in).
- Flask app: DONE - /api/scan, /api/report/<id> (HTML download),
  /api/health, /api/settings GET/POST, /api/recent.
- UI: glassmorphism dark theme, animated risk gauge, verdict glow,
  settings modal, sample demo mode (?demo=1).
- Packaging: PyInstaller one-file EXE BUILT & VERIFIED
  (dist/PhishGuard.exe ~17.7 MB, serves on 127.0.0.1:5000).

## Verified sample results (no-LLM mode)
| sample              | verdict    | risk |
|---------------------|------------|------|
| paypal lookalike+URL| phishing   | 93   |
| Apple-ID clone      | phishing   | 87   |
| advance-fee wire    | suspicious | 58   |
| normal link digest  | safe       | 18   |
| legit paypal receipt| safe       |  3   |
| clean internal mail | safe       |  0   |

Security checks passed: report HTML escapes script/img payloads; settings
round-trip; EXE boots and serves.

## Known issues / next
- No persistent scan history (in-memory only).
- Not uploaded to git; dist/ and build artifacts excluded on intent.
- Possible: train offline model for stronger no-LLM mode.