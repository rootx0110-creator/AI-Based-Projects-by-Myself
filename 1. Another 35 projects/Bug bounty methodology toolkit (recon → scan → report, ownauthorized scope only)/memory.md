# Memory — Bug Bounty Methodology Toolkit

Persistent project context for future sessions. Update this file when decisions change.

## Project identity
- **Name:** Bug Bounty Methodology Toolkit (recon → scan → report)
- **Policy:** OWN / AUTHORIZED SCOPE ONLY — the app refuses to run without a user attestation and refuses any target outside the declared scope.
- **Type:** Local web application (browser UI + Python stdlib backend), optional single-file `.exe` via PyInstaller.
- **Location:** `F:\AI Training\Projects\1. Another 35 projects\Bug bounty methodology toolkit (recon → scan → report, ownauthorized scope only)`

## Tech stack (decided)
- Python 3.14, **stdlib only** — no pip dependencies (deliberate: portability + easy exe packaging).
- `http.server.ThreadingHTTPServer` for the API/static server (default port **8765**).
- Persistence: `data/state.json` written atomically (tmp file + `os.replace`).
- Reports: self-contained HTML string with embedded CSS → `reports/bug-bounty-report-YYYYMMDD-HHMMSS.html`, served with `Content-Disposition: attachment`.
- Frontend: hand-rolled SPA in `static/` (index.html + css + js), dark glassmorphism theme, cyan/violet accents, live terminal-style log, animated background orbs.
- External scanners (subfinder, amass, httpx, nuclei, nmap, feroxbuster, sqlmap…) are **command templates only** — copy/paste, never executed by the app.

## Key implementation facts
- **Authorization gate:** `state.authorization.confirmed` must be `true` or `/api/recon/start` returns HTTP 403. Attestation stores statement text + timestamp.
- **Scope engine:** entry types `domain`, `wildcard` (`*.example.com`), `ip`, `cidr`, `url`. Matching order: out-of-scope wins → in-scope must match → else refused. Hostnames normalized to lowercase, IDNA-encoded when needed.
- **Pipeline stages (in order):**
  1. `validate-scope` 2. `dns-enum` 3. `http-probe` 4. `headers-audit`
  5. `exposed-files` (robots.txt / sitemap.xml / security.txt) 6. `tls-inspect`
  7. `fingerprint` 8. `consolidate-findings`
- **Passive-only network I/O:** DNS (custom UDP client for A/AAAA/MX/NS/TXT/CNAME) + HTTP(S) GET/HEAD. Rate limit: 0.4 s delay between requests, 8 s timeout, 200 KB body cap, 50 hosts/run max.
- **User-Agent:** `BBMToolkit/1.0 (authorized-testing; +local)` — deliberate, so target defenders can identify the tool.
- **Findings severities used:** `info < low < medium < high`. Header gaps → info/low; cert problems → medium/high; exposed sensitive files in robots → low/medium.
- **Worker model:** pipeline runs in a daemon thread; `status` endpoint polls shared `RUNTIME` dict under a `threading.Lock`; log lines capped (~400) in memory and mirrored to `state.runs[].log` on completion.
- **Server startup:** `python app.py [--port 8765] [--no-browser]`. On start it tries to open the browser (skipped with `--no-browser`).
- **Cancellation:** `POST /api/recon/stop` sets a cancel flag checked between stages/hosts.

## Conventions
- Docs required in project root: `architecture.md`, `memory.md`, `state.md`, `todo.txt`, `readme.txt` (all present).
- No emojis in code or docs.
- UI copy is English, professional/engagement tone.
- Findings IDs: `F-001`, `F-002`, … per run.

## Do not
- Do not add active exploitation, fuzzing, password spraying, or auto-execution of scanners.
- Do not remove the authorization gate or scope checks — they are the product's core constraint.
- Do not introduce pip dependencies without updating this file, readme.txt, and the exe build path.
