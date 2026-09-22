# Architecture

## 1. Overview

Single-page application (SPA), 100% static. No backend, no build
step, no external assets. The entire product lives in `index.html`
(embedded CSS + vanilla JavaScript). The doc engine generates
board-ready policy text from interview answers.

Because everything is local, the tool is safe for confidential
pre-interview data and works fully offline.

## 2. High-level data flow

```
   Interview UI            Policy Engine                Report Layer
 +---------------+   +------------------------+   +---------------------+
 | Guided wizard |-> | normalize answers      |-> | Board-ready preview  |
 | (seat/control |   | -> risk model          |   | (rendered in-app)    |
 |  settings)    |   | -> control gaps        |   +---------------------+
 +---------------+   | -> chapter composer    |   +---------------------+
        |            +------------------------+   | "Download HTML"     |
        +----> Live regeneration on every edit         (standalone file)|
                                                        + printable via   |
                                                        |   print dialog   |
                                                        +---------------------+
```

## 3. Modules (all inside index.html)

### 3.1 Wizard / Interview state  (`wizState`)
- Company identity, sector, size, geography, assets, compliance c h the board.
- Risk appetite sliders (confidentiality / integrity / availability).
- Per-domain posture ratings (residual risk per control family).
- Interview has fluid branching: e.g. if a sector implies PCI-DSS,
  payment-card questions appear automatically.

### 3.2 Policy engine  (`PolicyEngine`)
- `normalize()`          -> typed answers with defaults
- `regime()`             -> chooses regulator set from sector/geo/payments
- `policy.chapters()`    -> ordered list of chapters, each assembled from
  `sentence()` builders
- Domain modules (each a chapter factory):
  1. Access & Identity
  2. Data Protection & Privacy
  3. Endpoint & Workstation
  4. Network & Perimeter
  5. Application & SDLC Security
  6. Cloud & Infrastructure
  7. Third-Party / Supply Chain
  8. Incident Response
  9. Business Continuity / Disaster Recovery
  10. Logging, Monitoring & Audit
  11. Asset Management
  12. Acceptable Use & HR
- Every rule is written with **plain-language + technical depth**
  so the same text reads well for board members and auditors.

### 3.3 Risk & gap model
- Each control family computes a residual-risk score from the user's
  posture rating and target assurance level.
- Output: a heat table (probability x impact) shown to the board and
  a prioritized 90-day remediation list.
- Counters: % controls met, top 3 risks, key metrics.

### 3.4 Renderer  (`renderReport`)
- Creates the in-app "document preview" with cover page, metadata
  table, table of contents, charts (pure CSS/SVG) and sign-off block.
- `downloadHtmlReport()` serializes the same document into a
  fully standalone HTML file (embedded styles, no scripts) for
  distribution, printing and PDF export.

### 3.5 Report HTML export format
- Self-contained single file, printable A4, fonts degrade to system
  stack, table of contents with anchors, page-break rules.
- Filename: `CyberSecurity_Policy_<Company>_<yyyy-mm-dd>.html`

## 4. Desktop wrapper (EXE path)

`run_app.py` opens the same `index.html` in `pywebview`
Window(). `build_exe.ps1` freezes it with PyInstaller into a
single `dist\CyberPolicyGenerator.exe`. No server needed: the file
is loaded from disk.

## 5. Extension points
- New regulation  -> add to `frameworks` registry.
- New policy chapter -> add a factory in `domainModules` and a
  wizard page in the interview config.
- Localization -> move LNG map to module and load language variant.
- Server sync -> replace `save/load` local-storage calls with API calls;
  the rest of the pipeline is untouched.

## 6. Security notes
- Sensitive answers (contact names, sanction lists) are optional;
  stored only in browser localStorage, never transmitted anywhere.
- The exported report is static HTML with no scripts = safe to email.