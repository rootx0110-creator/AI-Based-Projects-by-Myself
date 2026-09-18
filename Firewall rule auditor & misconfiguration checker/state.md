# Firewall Rule Auditor — State Model (`state.md`)

This document specifies **every stateful behaviour** of FRAMC: backend memory
state, frontend UI state, analysis state (rule model invariants), and the
stateless/CI contract.

---

## 1. Backend State

The backend is **stateless by design** except for one in-memory object used to
serve `/api/export`.

### 1.1 `MemoryStore` (in-process)

| Field          | Type            | Purpose                                        | Reset on |
|----------------|-----------------|------------------------------------------------|----------|
| `last_report`  | `AuditReport`\|`None` | The most recent `/api/analyze` output  | new analyze |
| `last_meta`    | `dict`          | name/format/generated_at snapshot              | new analyze |
| `analyzed`     | `bool`          | whether a report exists for `/api/export`      | new analyze |

Rules (state transitions):

- **Server start** → all fields `None`/`False`.
- **`POST /api/analyze` succeeds** → replace `last_report`, set `analyzed=True`.
- **`POST /api/analyze` fails (parse error)** → keep previous `last_report`,
  return `error`; client decides to clear its UI store.
- **`GET /api/export?format=…`** → derives CSV/JSON from `last_report`; returns
  `404 {ok:false}` when `analyzed=False`.

### 1.2 Invariants

- Analysis is a **pure function** of `(format, content)`: same input ⇒ same
  `AuditReport` (required for deterministic audits & CI). Clock fields
  (`generated_at`) are the only non-deterministic addition.
- A single worker serves the SPA; no shared mutable state besides `MemoryStore`.
- No writes to disk for reports (exports are streamed on demand).

---

## 2. Frontend State (UI Store)

`frontend/static/js/app.js` keeps the client state in a plain object:

```js
state = {
  route: 'dashboard',            // active sidebar section
  formats: [],                   // from /api/formats
  format: 'iptables',            // selected
  fileName: '',                  // source label
  analyzing: false,              // in-flight request
  report: null,                  // last AuditReport (domain mirror)
  posture: null,                 // posture card numbers
  rulesView: { search:'', filter:{action:null,severity:null,proto:''}, page:1 },
  findingsView:{ filter:{severity:'ALL'}, shown:20 },
  theme: 'cyber',                // data-theme, persisted in localStorage
  chartState: { built:false, charts:{} }
}
```

### 2.1 Navigation / Route rules

- `setRoute(name)` toggles sections (`data-route` panels); only one visible.
- Route names: `dashboard`, `rules`, `findings`, `report`, `analyze`, `about`.
- If `report === null` and route ∈ `{rules,findings,report}` → render empty-state
  panel with a `Go to Analyze` CTA (no dangling charts).

### 2.2 Analyze → dashboard flow

1. User selects a file (drag-drop or input) **or** pastes text.
2. `analyzing=true`; lock form; show spinner overlay.
3. `POST /api/analyze`:
   - **200** → `report = data`; rebuild rules table, findings, charts,
     posture card; route → `dashboard`.
   - **error** → toast; keep prior `report`; unlock form.
4. `analyzing=false`; reset dropzone to *idle*.

### 2.3 Rules view state

- `rulesView.search` filters by src/dst/port/description (case-insensitive).
- `rulesView.filter.action` ∈ {null, `ALLOW`, `DENY`, `DROP`, `REJECT`}.
- `rulesView.filter.severity` ∈ {null, CRITICAL…INFO} — derived from the worst
  finding attached to each rule.
- Pagination: `pageSize=12`, `page` clamps to `ceil(filtered/12)`.
- Sorting: by `line_no` asc (fixed by content), optional severity desc.

### 2.4 Findings view state

- Severity filter incl. `ALL`; default shows 20 findings, `Load more` +20.
- Grouping toggles `GROUP` (top-level cards) vs `LIST` (table).

### 2.5 Persistence

`localStorage` keys (all optional, safe to clear):

| Key                 | Content                     |
|---------------------|-----------------------------|
| `framc.theme`       | theme name (e.g. `"cyber"`) |
| `framc.lastFormat`  | last chosen parser format   |

Active report is **never** persisted to localStorage.

---

## 3. Analysis (Engine) State Model

### 3.1 Rule invariants (post-parse)

For every `FirewallRule` produced by `parsers.parse()`:

```
1. position == insertion order in the source (0-based); monotonic.
2. rule_id == f"R{position+1:03d}".
3. action ∈ {ALLOW, DENY, DROP, REJECT}; missing action ⇒ DENY-by-default*.
4. protocol ∈ {tcp, udp, icmp, icmp6, any}; lowercase.
5. src_ip/dst_ip are canonical strings:
     "ANY"            for any/all/*/0.0.0.0/0
     "<ip>/<mask>"    for CIDR
     "<a>-<b>"        for raw ranges
     "<ip>"           for single hosts
6. src_port/dst_port are canonical strings:
     "ANY" | "8080" | "443,8443" | "1024:65535" | "*:80" (host:port forms normalized to port)
7. enabled==True unless a vendor explicit-disable token was seen.
8. raw preserves the original line for provenance.
```

Dataclass integrity is enforced at the end of every parse by
`normalize_rule()` (idempotent). No rule may reference an invalid rendering of
itself (e.g. `src_ip="0.0.0.0/33"` cannot exist — it is downgraded to a
`Finding` and set to `ANY`).

### 3.2 Finding invariants

```
1. category ∈ {shadowing, shadowed, override, duplicate, permissive, ordering,
   norelog, default-deny, cidr, mismatch, nat, informational}.
2. severity ∈ {CRITICAL, HIGH, MEDIUM, LOW, INFO}.
3. rule_ids non-empty (INFO findings may reference the chain/every rule).
4. deterministic order: detector order, then rule position, then title.
```

### 3.3 Posture computation

Posture is derived, never stored: recompute lazily per render/export.
Formula and weights are centralised in `scoring.py` (see architecture §8) so
changing a weight changes the whole audit consistently.

---

## 4. Concurrency & Race Policy

- Flask dev server threads: `MemoryStore` guarded by a simple `threading.Lock`
  around read/write of `last_report` (export vs. new analyze).
- Frontend: single async `analyze()` call; a second request is rejected while
  `analyzing===true` (UI-level guard).

---

## 5. Error States Matrix

| Condition                          | Backend                                | Frontend                             |
|------------------------------------|----------------------------------------|--------------------------------------|
| Empty content                      | `400 ok:false "content is empty"`      | toast, keep state                    |
| Unknown format                     | `400 ok:false "unknown format"`        | toast, default to iptables           |
| Content over 2 MB                  | `413 ok:false`                         | toast, do not POST                   |
| Parse produces 0 rules             | `200` with `warnings=["no rules found"]`, rules:[] | empty-state panel   |
| Analysis crash (unexpected)        | `500 ok:false {error}` (logged)        | toast `Analysis failed (see logs)`   |
| Export with no prior report        | `404 ok:false`                         | toast `Run an analysis first`        |

Parse *warnings* (recoverable per-line problems) are non-fatal and returned in
`report.meta.warnings`; they surface as INFO findings and a yellow strip.

---

## 6. Stateless / CI Contract

`backend/cli.py audit` respects the same invariants:

- Exit code `0` = success (even with findings), `1` = parse failure
  (zero rules + fatal warnings), `2` = usage error.
- `--json` emits the identical envelop shape as the API so automation can reuse
  one schema.
- Determinism guarantee allows diffing audits across config versions
  (`audit v1 > a.json; audit v2 > b.json; diff a.json b.json`).

---

## 7. State evolution (roadmap hooks)

Future states, anticipated but not yet implemented (kept out to preserve
simplicity):

- `state.sessions[]` → multi-config comparison (v1 vs v2 posture diff).
- `MemoryStore.snapshots` → keep N recent reports for trend chart.
- `state.rulesView.selected` → rule drill-down drawer.
- Optional local SQLite when >10k-rule configs are supported.