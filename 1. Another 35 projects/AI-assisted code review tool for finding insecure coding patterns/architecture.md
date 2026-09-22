# Architecture — SecuRevealer

AI-assisted code review tool that finds insecure coding patterns.

## 1. High-level overview

```
┌────────────────────────────────────────────────────────────────┐
│                        BROWSER (UI)                            │
│  public/index.html + public/style.css + public/app.js          │
│  - Drag & drop / file picker / paste code                      │
│  - Dashboard: severity rings, findings table, code viewer      │
│  - "Download HTML report" button                               │
└───────────────▲────────────────────────────┬───────────────────┘
                │ GET static files            │ POST /api/scan
                │                             │ (JSON: files[] / code)
┌───────────────┴─────────────────────────────▼───────────────────┐
│                     API SERVER (Node.js, zero deps)             │
│  backend/server.js — routing, multipart parsing, static files   │
├──────────────────────────────────────────────────────────────────┤
│  backend/analysis/                                               │
│    detectors.js   → 40+ insecure-pattern rules (regex engine)   │
│    ast.js         → tolerant JS/TS parser + FP validator         │
│    aiadvice.js    → AI-style advice: cause / exploit / fix      │
│    scanner.js     → orchestrates scan pipeline per file         │
├──────────────────────────────────────────────────────────────────┤
│  backend/report/reporter.js → standalone styled HTML report     │
└──────────────────────────────────────────────────────────────────┘
        demo fixtures: public/demo/*.js|py|php|env|sql
```

## 2. Scan pipeline

```
files[] ──► for each file:
  1. language sniff (extension + shebang)
  2. AST pass (JS/TS only): mark comment/string byte ranges
  3. detector pass: every rule regex runs over the code
  4. validation: drop matches inside comments/strings (FP filter),
     dedupe overlapping rules on same span
  5. AI advice enrichment: root cause, exploit scenario, fix snippet,
     references (CWE / OWASP) per finding
  6. severity roll-up: file score = weighted by CRITICAL>HIGH>MEDIUM>LOW
──► aggregate report JSON ──► UI  +  HTML report on demand
```

## 3. Detection model

- **Rules** are declarative objects: `{ id, title, severity, cwe, owasp,
  languages, pattern, advice }`. Adding a rule = adding one object.
- **Regex-first** for speed and language breadth (JS/TS, Python, Java,
  PHP, SQL, shell, Go, C#, config/.env, secrets).
- **AST-assisted validation** for JS/TS: a hand-rolled tolerant tokenizer
  identifies comments, template literals, and strings so regex hits inside
  them are discarded — kills the classic false-positive class without a
  heavyweight parser dependency.

## 4. Key modules

| Module | Responsibility |
|---|---|
| `backend/server.js` | HTTP server, static hosting, `/api/scan`, `/api/report`, multipart form parsing |
| `backend/analysis/scanner.js` | Pipeline orchestration, scoring, aggregation |
| `backend/analysis/detectors.js` | Rule catalogue (the "what to find") |
| `backend/analysis/ast.js` | Comment/string mapping + JS syntax sanity check |
| `backend/analysis/aiadvice.js` | Advice generation per rule id (the "AI assist") |
| `backend/report/reporter.js` | Self-contained HTML report (inline CSS, no CDN) |
| `public/app.js` | UI logic: fetch scan, render rings/table/viewer, download report |
| `public/style.css` | Dark "terminal-neon" theme, animated, responsive |
| `demo/scan-demo.js` | CLI smoke test scanning `public/demo/*` fixtures |

## 5. API

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/api/scan` | POST | JSON `{ files:[{name, content}] }` or multipart form-upload, or raw text `?name=x.js` | Full scan JSON |
| `/api/report` | POST | same as scan | `text/html` (Content-Disposition: attachment) |
| `/api/health` | GET | — | `{ ok: true }` |
| `/` , `/public/*` | GET | — | Static UI |

## 6. Severity & scoring

- CRITICAL = 10, HIGH = 7, MEDIUM = 4, LOW = 1.
- File risk score = min(100, Σ weighted findings).
- Overall grade: A (0) → F (≥60).

## 7. Non-goals (v1)

- No taint tracking / full dataflow — regex + AST validation is the model.
- No external AI API calls — advice engine is local, deterministic
  ("AI-assisted" = heuristic knowledge base shaped like an LLM reviewer).
