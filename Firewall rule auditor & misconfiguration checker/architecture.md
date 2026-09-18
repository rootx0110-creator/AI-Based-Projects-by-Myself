# Firewall Rule Auditor & Misconfiguration Checker — Architecture

## 1. Overview

The **Firewall Rule Auditor & Misconfiguration Checker** (FRAMC) is a self-contained
web application that ingests firewall configurations from multiple vendor formats,
parses them into a canonical rule model, scans for security misconfiguration
patterns, grades each rule and the overall posture, and presents a stylish,
filterable dashboard with exportable findings.

```
                          ┌──────────────────────────────────────────────┐
                          │                 CLIENT  (Browser)            │
                          │  Single-Page UI  ·  Chart.js  ·  CSS themes   │
                          └───────────────────────┬──────────────────────┘
                                                  │ HTTP/JSON (REST)
                          ┌───────────────────────▼──────────────────────┐
                          │            BACKEND  (Python / Flask)         │
                          │                                              │
                          │  ┌────────────┐ ┌────────────┐ ┌───────────┐ │
                          │  │ Parser     │ │ Detector   │ │ Scoring   │ │
                          │  │ Pipeline   │ │ Engine     │ │ Engine    │ │
                          │  └─────┬──────┘ └─────┬──────┘ └─────┬─────┘ │
                          │        └──────────────┴───────────────┘       │
                          └──────────────────────────────────────────────┘
```

- **Frontend** — `frontend/` static assets served by Flask. Zero build tools.
- **Backend** — `backend/` Flask app exposing a small REST API.
- **Analysis engine** — `backend/engine/` pure-Python, vendor-agnostic core.

The engine is **dependency-free on network access**; it can also run unit tests
and batch (CLI) analysis headlessly.

---

## 2. Component Diagram

```
┌───────────────────────────────┐
│ CLI runner  ──────────────┐   │
│ backend/cli.py            │   │
└───────────────────────────┘   │
                                ▼
                     ┌─────────────────────┐
                     │  Flask App          │
                     │  backend/app.py     │
                     │  · /api/analyze     │
                     │  · /api/formats     │
                     │  · /api/export      │
                     │  · / (static UI)    │
                     └─────────┬───────────┘
                               │
                 ┌─────────────▼──────────────┐
                 │      ENGINE                 │
                 │  backend/engine/            │
                 │  ┌───────────┐              │
                 │  │ rule.py   │  Rule model  │
                 │  │ iprange.py│  IP/port     │
                 │  │ parsers.py│  format      │
                 │  │           │  parsers     │
                 │  │ detectors │  checks      │
                 │  │  scoring  │  grading     │
                 │  └───────────┘              │
                 └─────────────────────────────┘
```

---

## 3. Layers & Responsibilities

### 3.1 Presentation Layer (`frontend/`)
- **index.html** — Single page with sidebar, dashboard cards, charts, rule
  tables, findings panels, upload/paste analyzer, export controls.
- **static/css/style.css** — Design system (CSS custom properties, dark theme,
  glassmorphism cards, glow accents, responsive grid).
- **static/js/app.js** — State store (ES modules), API client, chart rendering,
  table filtering, tab routing, drag-&-drop file handling.

### 3.2 API Layer (`backend/app.py`)
| Endpoint      | Method | Purpose                                        |
|---------------|--------|------------------------------------------------|
| `/`           | GET    | Serve the SPA                                   |
| `/api/formats`| GET    | List supported firewall formats + syntax gloss |
| `/api/analyze`| POST   | `{format, name, content}` → audit report        |
| `/api/export` | GET    | Export last report as `json` or `csv`           |

API responses follow a single envelope:

```json
{ "ok": true, "data": { ...report... }, "error": null }
```

### 3.3 Domain Layer (`backend/engine/`)
Pure Python, no Flask imports → independently testable.

| Module        | Responsibility                                             |
|---------------|------------------------------------------------------------|
| `rule.py`     | `FirewallRule`, `NatRule` dataclasses, severity enums      |
| `iprange.py`  | IP address/range/CIDR parsing + coverage algebra, port sets|
| `parsers.py`  | Vendor parsers → `ParseResult(rules, nats, warnings)`      |
| `detectors.py`| Deterministic misconfiguration check suite                  |
| `scoring.py`  | Rule risk + posture scoring + report assembly              |

---

## 4. Domain Model

```python
FirewallRule:
    rule_id      str        # R001, R002, …
    line_no      int        # source line number
    position     int        # evaluation order within the chain
    action       enum       # ALLOW | DENY | DROP | REJECT
    direction    enum       # IN | OUT | INOUT
    protocol     str        # tcp | udp | icmp | any
    src_ip       str        # canonical string
    src_port     str        # "any", "80", "80,443", "1024:65535"
    dst_ip       str
    dst_port     str
    interface    str|None
    log          bool
    enabled      bool
    description  str
    raw          str        # untouched source line
    chain        str|None   # iptables chain / asa extended acl
    rule_type    enum       # NORMAL | NAT | DEFAULT_DENY
```

```python
Finding:
    id            str
    category     str        # e.g. "shadowing"
    severity     enum       # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title        str
    detail       str
    recommendation str
    rule_ids     list[str]
    confidence   float      # 0..1
```

```python
AuditReport:
    meta       {name, format, generated_at, parsed, …}
    summary    {total_rules, by_action, by_protocol, …}
    posture    {overall, sub_scores: {category: score}}
    rules      list[FirewallRule]
    findings   list[Finding]
    nat        list[NatFinding]
    export     {json, csv}
```

---

## 5. Data Flow — an Analysis Request

```
User paste / upload
        │
        ▼
POST /api/analyze  {format, name, content}
        │
   ┌────▼─────┐
   │ SPA     │ validates size, picks parser
   └────┬─────┘
        ▼
  parsers.parse(format, content)
        │  returns rules, nats, warnings
        ▼
  detectors.scan(rules, nats)
        │  returns findings []
        ▼
  scoring.evaluate(rules, findings, nats)
        │  returns PostureReport
        ▼
  report = assemble(...)         JSON
        │
        ▼
  store last_report in memory    -> /api/export
  return 200 {ok, data: report}
```

---

## 6. Parsing Pipeline (vendor support)

Each parser is a function `parse(text) -> RuleList` wrapped by `parse()`
which normalizes:

1. **Strip comments/blank lines** (vendor-specific syntax).
2. **Tokenize** into a vendor `AccessRule`.
3. **Normalize fields** → canonical `FirewallRule`:
   - `any`,`all`,`*`,`""`  → `ANY`
   - CIDR validation + fixing (`/33` flagged as invalid, not crash)
   - port lists/ranges preserved as text + parsed intervals
   - interface / direction inference from context
4. **Order & ID**: rules keep positional order (used by shadow detector); each
   gets `R###`, `NAT###`.

Supported formats (detectable by content or explicit selection):

| Format            | Typical sources                              |
|-------------------|----------------------------------------------|
| `iptables`        | `iptables-save`, minimal `iptables -L`        |
| `cisco-asa`       | `access-list ACL extended permit/deny ...`   |
| `fortigate`       | `config firewall policy` / `config firewall addr` |
| `pfsense`         | pfSense `config.xml` `<rule>` blocks         |
| `windows`         | `netsh advfirewall firewall` / `Get-NetFirewallRule` CSV |
| `paloalto`        | `set security policies` (PA CLI)             |
| `plain`           | flexible `action|proto|src|sport|dst|dport` table |

---

## 7. Detection Suite (misconfiguration checks)

| Detector                    | Severity default | Description                                      |
|-----------------------------|------------------|--------------------------------------------------|
| Shadowed Rule               | HIGH             | Later rule never reached (earlier superset, same action) |
| Duplicate Rule             | MEDIUM           | Exact duplicate of an earlier rule               |
| Ordering Bypass            | CRITICAL         | `ALLOW` placed before covering `DENY` (override) |
| Any/Any Allow              | CRITICAL         | Rule allows all traffic in+out (world-facing)    |
| Permissive Network Expose  | HIGH             | Allow-to-internal / large subnets on sensitive ports |
| Missing Default-Deny       | HIGH             | No final catch-all DENY/REJECT rule              |
| Invalid CIDR / Range       | MEDIUM           | Malformed network notation (e.g. `/33`, bad range) |
| Non-Logged Allow           | LOW              | Allow rules with logging disabled                 |
| Port/Protocol Mismatch     | LOW              | fc/LDP/ICMP carrying ports, UDP rules on TCP-only services |
| NAT target mismatch        | MEDIUM           | NAT/PAT rule whose service has no permit at fw   |
| Dead/Unreferenced rules    | INFO             | Rules whose networks appear nowhere (informational) |

Detector pipeline is **deterministic** — same input → same output. Engine
tags each finding with the implicated `rule_ids` and `line_no`s.

---

## 8. Scoring Model

### 8.1 Rule risk score (0–100, higher = riskier)
```
base = 10
+ 45  if action=ALLOW and src=ANY and dst=ANY
+ 25  if action=ALLOW and (src=ANY or dst=ANY)
+ 15  if action=ALLOW and dst_port in SENSITIVE_PORTS (22, 23, 3389, 1433, 3306,…)
+ 10  if direction=IN and dst in internal nets
+  5  if protocol=any
+ 40  if finding CRITICAL attached
+ 20  if finding HIGH attached
+  5  if finding MEDIUM attached
- 30  if action in (DENY/DROP/REJECT)       # good hygiene reward
```

### 8.2 Posture score (0–100, higher = healthier)
```
posture = 100
- Σ (severity_weight × count) for severity buckets
   CRITICAL=18, HIGH=10, MEDIUM=5, LOW=2, INFO=0.5
+ 5 if default-deny present
+ 3 if every ALLOW logs traffic
clamp(0…100)
```

### 8.3 Grade bands
| Band   | Range   | Color   |
|--------|---------|---------|
| A      | 85–100  | green   |
| B      | 70–84   | teal    |
| C      | 55–69   | amber   |
| D      | 40–54   | orange  |
| F      | 0–39    | red     |

---

## 9. Persistence & State

There is **no database**. The application is intentionally stateless:
- The last full report is held in-process (`backend/app.py MemoryStore`) to
  serve `/api/export`.
- File uploads are validated, parsed, and discarded.
- Idempotent analysis → repeatable audits, ideal for CI-style batch runs
  (`backend/cli.py audit file.conf --format fortigate --json out.json`).

See `state.md` for the detailed state model, and `memory.md` for the
decision log and operational guidance.

---

## 10. Packaging & Deployment

### 10.1 Run as a web app (dev)
```bash
pip install -r requirements.txt
python run.py                 # http://127.0.0.1:8765
```

### 10.2 Run as an EXE (end-user, no Python needed)
```bash
python build_exe.py           # produces dist/FRAMC/FRAMC.exe
dist/FRAMC/FRAMC.exe --host 0.0.0.0 --port 8765
```
PyInstaller bundles the Flask runtime + static files; the EXE launches a local
HTTP server and auto-opens the browser via `webbrowser`.

### 10.3 Headless / CI
```bash
python backend/cli.py audit samples/iptables.txt --format iptables --json reports/out.json
```

---

## 11. Security Notes

- Server binds to `127.0.0.1` by default (override with `--host`).
- Input size capped (config text ≤ 2 MB) and time-boxed.
- Parsing is defensive; malformed lines degrade to warnings, never exceptions.
- No secrets, no external network calls at runtime.
- CSP header set on the SPA; Chart.js loaded from local asset when available.

---

## 12. Extension Points

1. **New vendor parser** → add a function to `parsers.py` + a row in
   `FORMATS`; UI auto-populates via `/api/formats`.
2. **New detector** → subclass/register a check in `detectors.py`;
   its `severity` feeds straight into scoring.
3. **New export** → add formatter to `AssembleReport.export`.
4. **New UI theme** → add a `[data-theme="name"]` block in `style.css`; the
   theme switcher is data-driven.