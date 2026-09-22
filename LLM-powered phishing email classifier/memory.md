# Memory - Project Session Notes

Project: LLM-Powered Phishing Email Classifier
Location: F:\AI Training\Projects\1. Another 35 projects\LLM-powered phishing email classifier
Created: 2026-09-21

## Decisions (why)
- Hybrid pipeline chosen so the tool works out of the box with zero API
  keys, and becomes "smarter" only when the user opts into an LLM.
- Flask + vanilla JS over React/Vite to keep the build step trivial and
  allow clean PyInstaller one-file packaging.
- Verdict space kept to exactly three values (safe/suspicious/phishing)
  with a 0-100 risk index; avoids over-promising on confidence.
- Inlined CSS/JS in the downloadable HTML report so reports are portable
  and printable (file:// friendly).

## Gotchas learned (keep)
- Windows PowerShell doesn't support && in the shell here; chained
  build commands should use `; if ($?) { ... }`.
- Python 3.14 on this machine: ensure Flask version >= 3.0.3 and that
  PyInstaller 6.x is used (matches installed 6.22.3).
- Flask `__file__`-relative paths break under PyInstaller --onefile;
  paths to templates/static must be resolved via sys._MEIPASS when frozen.
- Brand scanning must run on URL-stripped text, or any URL containing
  "google"/"paypal" triggers BRAND_MISMATCH false positives.
- Leet-decode (1->i/l, 4->a, 0->o, ...) with a brand-at-start rule plus a
  TRUSTED_SENDER_DOMAINS allowlist keeps lookalike detection precise.
- PowerShell single-quoted strings don't expand `n - always test API via
  a .py script when the fixture contains newlines.
- Score mapping is exponential saturation (risk = 100*(1-e^(-points/48)));
  linear mapping was far too lenient for many-signal scams.

## Session log (2026-09-21)
- MVP built: classifier engine, Flask API, glassmorphism UI, HTML report
  download, PyInstaller EXE. Smoke-tested phish/safe/advance-fee samples.
  XSS escaping verified on report output; EXE boots and serves page 200.
- Remaining: persistence, unit tests, optional URL-reputation enrichment.

## Environment
- Python 3.14.7, pip 26.2.1
- Installed: flask 3.1.3, flask-cors 6.0.5, requests 2.34.2,
  pyinstaller 6.22.3