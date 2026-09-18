# Firewall Rule Auditor — Project Memory (`memory.md`)

This file is the long-term **operational memory** of the project: what is being
built, why, what was decided, constraints, gotchas, and how to resume work
cheaply after a break. Treat it as the single source of truth for context.

---

## 1. Project Identity

- **Name:** FRAMC — Firewall Rule Auditor & Misconfiguration Checker
- **Verdict of intent:** a self-contained web app (also shippable as a Windows
  EXE) that audits firewall rule-sets for shadowing, ordering, permissiveness,
  duplication and other misconfigurations, and grades the fence.
- **Audience:** security engineers auditing config dumps, ops teams reviewing
  change requests, pentest prep, compliance evidence.
- **Constraint:** no database, no login, no cloud dependencies. Runs offline.
  Deterministic. Simple to hand to a non-technical reviewer.

---

## 2. Current State (Resume Here)

Everything in this repository works toward **v1.0**:

- ✅ Repo layout, `architecture.md`, `state.md`, `memory.md`
- ✅ Engine: `rule.py`, `iprange.py`, `parsers.py`, `detectors.py`, `scoring.py`
- ✅ Flask API: `/api/formats`, `/api/analyze`, `/api/export`, static SPA host
- ✅ Frontend SPA: dashboard, rules table, findings, report, analyzer, themes
- ✅ Sample configs (iptables / cisco-asa / fortigate / pfsense / windows)
- ✅ `run.py` dev server, `backend/cli.py` headless auditor
- ✅ `build_exe.py` PyInstaller bundle

**Next milestone (v1.1, optional):**
- [ ] Comparison mode: analyze two configs, emit posture delta
- [ ] More exports: PDF, HTML report
- [ ] Rule-simulator: "does this packet match?" checker

---

## 3. Key Decisions (decision log)

### D1 — No database, in-memory last-report only
*Why:* the app is a point tool; persisting its output contradicts "auditor =
stateless oracle". `MemoryStore` keeps only the most recent report for export.
Revisit only if trend history becomes a feature.

### D2 — Python engine, Flask thin API, vanilla JS SPA frontend
*Why:* maximal deployability (one `requirements.txt`), zero build tooling,
PyInstaller-friendly. Chart.js is vendored locally to keep offline behavior.

### D3 — Canonical rule model with positional ordering
Shadowing detection needs evaluation order; therefore **order is preserved**
and every rule carries `position` and `line_no`. Never sort rules by
"security" in the model — sorting is a view concern.

### D4 — Any/Any ALLOW ⇒ CRITICAL, always
Even though some environments legitimately open outbound any/all, the tool
flags it and lets the reviewer classify. Better to over-flag than miss.

### D5 — Shadowing = same-action superset earlier; Ordering-bypass = ALLOW before DENY superset
A later DENY after an ALLOW covering it is a real splice risk — classified
`CRITICAL` (override). A later same-action rule covered by an earlier one is
`HIGH` (shadowed). These are treated distinctly and earn distinct
recommendations.

### D6 — Deterministic audits
`same input → same report` is a hard requirement (supports `diff`-based change
review and CI). The only non-deterministic field allowed is `generated_at`.

### D7 — Bounds: 2 MB input cap, 2 s scan budget
Parser is defensive; oversized input is rejected with 413. Detector pipeline
is O(n²) over rules but n is bounded (≤ ~5,000 rules) so acceptable.

### D8 — Severity buckets feed posture with fixed weights
CRITICAL=18, HIGH=10, MEDIUM=5, LOW=2, INFO=0.5, rewards for default-deny
(+5) and universal logging (+3). Centralised so re-weighting is one-line.

---

## 4. Conventions & Gotchas

- **Python:** ≥3.9 target (3.10+ recommended for `match`); dataclasses + typing.
  No third-party deps in the engine. Flask + Waitress optional for runtime.
- **Naming:** rules `R001…`, NAT `NAT001…`; findings `F001…` (stable: derived
  from category+position, so identical audits give identical IDs).
- **Parsing rule of thumb:** *tolerate, warn, never crash.* Malformed line →
  `Warning` + INFO finding. `0.0.0.0/33` → downgrade to `ANY` + warning, never
  raise.
- **Canonical action verbs:** normalize vendor verbs to
  `ALLOW|DENY|DROP|REJECT` (e.g. FortiGate `accept`→`ALLOW`,
  ASA `permit`→`ALLOW`, Cisco `deny`/`remark`→`DENY`).
- **Ports:** keep both a display string and parsed interval list; ranges like
  `1024:65535`, lists `80,443`, `*:22` normalised.
- **Frontend:** no framework; JS modules; all charts must tolerate `report=null`.
  Theme switching via `data-theme` on `<html>`; persist to `localStorage`.
- **Windows dev:** paths use `/` in docs; dev server binds 127.0.0.1:8765;
  firewall prompts for the EXE are expected and harmless (bind loopback).

---

## 5. Testing & Verification Playbook

| What                           | Command                                                        |
|--------------------------------|----------------------------------------------------------------|
| Dev server                     | `pip install -r requirements.txt; python run.py`              |
| Unit tests                     | `python -m unittest discover -s backend/tests -p "test_*.py"`  |
| Engine sanity (all samples)    | `python backend/cli.py audit samples --all-formats --json out/report.json` |
| Manual UI check                | open `http://127.0.0.1:8765`, paste each sample, verify counts |
| Build EXE                      | `python build_exe.py && dist\FRAMC\FRAMC.exe`                  |

Sanity numbers to re-verify after engine edits (golden checks):

- `samples/iptables.txt` — 14 rules parsed; ≥1 CRITICAL; posture ≈ 0 (F).
- `samples/cisco_asa.txt` — 5 rules; HIGH shadow finding; posture ≈ 45 (D).
- `samples/fortigate.txt` — 5 rules, address objects resolved (10.0.0.0/8);
  ALLOW-overrides-DENY found; posture ≈ 31 (F).
- `samples/windows.txt` — 5 rules (1 disabled skipped); duplicate + non-logged found.
- `samples/pfsense.txt` — 4 rules; world-open ANY/ANY flagged; posture ≈ 70 (B).
- `samples/paloalto.txt` — 5 rules; override + world-open found.
- `samples/plain.txt` — 7 rules; shadow finding present.

---

## 6. File Map

```
- architecture.md            system design (start here for big questions)
- state.md                   state model & invariants (engineering contract)
- memory.md                  this file (context + decisions)
- README.md                  quickstart
- requirements.txt           flask, waitress (optional), pyinstaller (build)
- run.py                     dev entrypoint
- build_exe.py               PyInstaller packaging
- backend/
    app.py                   Flask app + MemoryStore + routes
    cli.py                   headless auditor
    engine/
        __init__.py
        rule.py              FirewallRule / NatRule / Finding / severity enums
        iprange.py           IP & port algebra (coverage, parse, canonical)
        parsers.py           vendor parsers + FORMATS registry + normalize
        detectors.py         check suite (shadow, dup, permiss, order, …)
        scoring.py           posture + rule-risk scoring + report assembly
    tests/                   unit tests (mirror the golden checks)
- frontend/
    index.html               SPA shell
    static/
        css/style.css        design system + themes
        js/app.js            state, API, charts, tables
- samples/                   vendor configs for testing
- .gitignore
```

---

## 7. Git / Collaboration Notes

- Project is not yet a git repo; `git init` + first commit is a good first
  action after verification.
- Commit granularity: doc files / engine / api / ui / packaging as separate
  commits.
- Never commit real customer configs into `samples/` — synthetic only.

---

## 8. Open Questions / Risks

1. **Vendor coverage depth** — we parse enough for a strong v1; exotic
   constructs (rule `set` in PA, `nat pool` ranges, `%` quoted objects) are
   documented as limitations.
2. **False positives on outbound any/any** — acceptable; reviewer classifies.
3. **O(n²) shadow check** — bounded to 5k rules; if larger configs appear,
   switch to an interval-tree index (see architecture §12).
4. **EXE size** — PyInstaller bundles Python runtime (~45 MB); acceptable for
   internal tooling; alternatively ship `.zip`.

---

## 9. How to Get Help in Repo

- Understand behaviour → `architecture.md` §3–§8.
- Change state handling → `state.md` (invariants section).
- Add parser/detector → `architecture.md` §12, follow detector/parser shape in
  `backend/engine/`.
- Missing feature beats doc → update `architecture.md` + this file together.