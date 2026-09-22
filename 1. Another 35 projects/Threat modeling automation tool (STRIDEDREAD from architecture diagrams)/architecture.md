# STRIDEForge — Architecture

## Overview

STRIDEForge automates threat modeling (STRIDE categorization + DREAD risk
scoring) from a visual architecture diagram. It is a single Flask application
with a JavaScript-driven diagram canvas and a Python rules/scoring engine.

```
┌──────────────────────────── BROWSER ────────────────────────────┐
│  static/js/app.js          templates/index.html  static/css     │
│   diagram canvas (SVG)     tabbed UI            glass UI theme │
│   analysis view            report preview                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTP (JSON)
┌─────────────────────────────────▼───────────────────────────────┐
│                      Flask  (app.py)                            │
│   GET  /                  -> index.html                         │
│   POST /api/analyze       -> {summary, threats, ...}            │
│   POST /api/report        -> standalone HTML document           │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│  threat_engine/                                                 │
│   rules.py    STRIDE threat templates (+ DREAD bases)           │
│   analyzer.py pipeline: model -> zones -> threats -> scores     │
│   report.py   HTML report generator (embedded CSS)             │
└─────────────────────────────────────────────────────────────────┘
```

## Data model (sent as JSON to /api/analyze)

```json
{
  "name": "Architecture name",
  "description": "…",
  "elements": [
    {
      "id": "e1", "kind": "process", "type": "web_application",
      "label": "Web App", "zone": "dmz",
      "x": 600, "y": 300, "w": 150, "h": 70,
      "flags": { "internet": true, "pii": true, "authn": false,
                 "authz": false, "encrypted": false, "logged": false,
                 "rate_limited": false, "pci": false, "phi": false }
    }
  ],
  "flows": [
    { "id": "f1", "source": "e1", "target": "e2",
      "label": "HTTPS API", "encrypted": true, "authenticated": true }
  ],
  "boundaries": [
    { "id": "b1", "label": "Internet", "zone": "internet",
      "x": 0, "y": 0, "w": 300, "h": 500 }
  ]
}
```

Element kinds:
- `process`         (executing code: web app, API, worker, IdP, gateway…)
- `data_store`      (database, cache, queue, file storage, search index…)
- `external_entity` (users, partners, third-party systems, devices…)
- `data_flow` is modeled separately in the `flows` array.

Effective zone of an element = zone of the boundary rectangle that contains
its center, else its own `zone` attribute, else `"default"`. A data flow whose
source/target zones differ is a **trust-boundary crossing** (raises damage and
affected-users scores).

## Pipeline (threat_engine/analyzer.py)

1. **Zone resolution** — compute effective zones from boundaries.
2. **Rule selection** — for each element and each flow, and each of the six
   STRIDE letters, collect matching templates:
   - exact `(kind, type, stride)` rules, plus
   - wildcard `(kind, "any", stride)` rules.
   Duplicates (same title) are removed.
3. **Context modifiers** — adjust the base DREAD five-factor tuple:
   - `internet`  -> +2 exploitability, +2 discoverability, +1 affected users
   - `pii|pci|phi` -> +2 damage  (critical data)
   - boundary crossing (flows / EoP) -> +1 damage, +1 affected users
   - Controls lower **residual risk**:
     - `authn` (strong authentication)  -> S: -2 exploitability, -1 discoverability
     - `authz` (strict authorization)   -> E: -2 exploitability, -1 damage
     - `encrypted` (at rest / in transit) -> T,I: -1 damage, -2 exploitability
     - `logged` (audit logging)         -> R: -2 damage, -1 discoverability
     - `rate_limited`                   -> D: -2 exploitability, -1 affected users
   All factors clamped to [1,10]. Each applied modifier is recorded in
   `context_notes` for transparency.
4. **Risk tiering** from DREAD total (5..50):
   - Critical >= 40 · High >= 30 · Medium >= 18 · Low < 18
5. **Summary aggregation** — totals per STRIDE letter, per risk tier, overall
   project grade (highest present tier), top-5 threats, top recommendations
   (deduplicated mitigations of Critical/High threats).

## Rules engine (threat_engine/rules.py)

Templates keyed by `(element_kind, element_type, stride_letter)`. Wildcard
type `"any"` provides generic per-kind coverage; specific types add
identity-aware detail (e.g. database tampering -> SQL injection; web
application spoofing -> session hijacking; data flow info disclosure ->
cleartext transit). Each template: {title, description, mitigation, dread}.

Coverage:
- Components/processes: web_application, api_service, microservice,
  mobile_client, identity_provider, load_balancer, firewall, worker,
  frontend (SPA), desktop_client, iot_device, generic *.
- Data stores: database (sql & nosql), cache, message_queue, file_storage,
  search_index, config_store, generic *.
- External entities: user, admin, third_party, browser/mobile, partner_system.
- Data flows: generic *, including transit-type threats (MITM, cleartext,
  flooding, injection, log forgery, replay).

## Report generator (threat_engine/report.py)

Produces a **standalone HTML file** (all CSS embedded, no external assets) with:
- Title/date/architecture name.
- Executive summary cards (threats, critical, high, medium, low).
- Risk + STRIDE distribution bar charts (pure CSS).
- Recommendations block (from Critical/High mitigations).
- Component/data-flow inventory tables.
- Full threat register sorted by severity.
- Detailed per-threat cards (STRIDE badge, DREAD bars, risk, mitigation,
  context notes).
- Methodology appendix (STRIDE properties + DREAD factor definitions).

## Web layer (app.py)

- `resource_path()` helper makes Flask resolve templates/static correctly both
  when run from source and when frozen by PyInstaller (`sys._MEIPASS`).
- `POST /api/analyze` validates input and returns JSON.
- `POST /api/report` streams the generated HTML with `Content-Disposition:
  attachment` for direct download, and is also fetched client-side for the
  in-app preview.

## Frontend (static/js/app.js)

Vanilla JS, no frameworks. Responsibilities:
- SVG diagram canvas: grid, boundary rectangles, flows (bezier arrows),
  nodes (rounded rects / cylinders / entity shapes), badges (entry point,
  internet globe, lock), drag-to-move, tool-driven creation, delete tool,
  inline selection + properties panel binding.
- Trace mode: user-uploaded image is placed under the diagram at 50% opacity.
- Analysis rendering with STRIDE/risk/search filters and DREAD bars.
- Report preview via `iframe.srcdoc` and download via blob.
- JSON import/export, embedded sample architectures, toast notifications.

## Security considerations

- HTML report content is HTML-escaped server-side before embedding.
- The app binds to `127.0.0.1` by default (local tooling, not a public server).