# SOAR-Lite — State

Definition of runtime state, its lifecycle, and durability semantics.

## 1. What is "state"?

Two tiers:

1. **Declarative (code/static, in repo):**
   - `playbooks/*.json`            - playbook definitions (hot reloaded)
   - `static/`, `templates/`       - presentation assets
   - settings defaults in `soar_lite/defaults.py`

2. **Runtime (data/ only, gitignored):**
   - `incidents.json`              - incident records + notes
   - `executions.json`             - run + step-level execution state
   - `iocs.json`                   - indicators of compromise seen
   - `settings.json`               - analyst-modifiable configuration
   - `report_cache/`               - generated HTML reports (rebuilt on change)
   - `.seed_marker`                - set after first-run seeding

## 2. Object model

```
Incident
  id, ref_no (e.g. INC-2026-0012), title, description, type, severity
  status, phase, analyst, source, channel, tags[]
  risk_score, playbook_id, created_at, updated_at, closed_at
  notes[] {ts, author, text}, ioc_ids[]

Execution
  id, incident_id, playbook_id, status
  created_at, started_at, finished_at
  steps[] RunStep
  current_step_id, summary

RunStep
  id, kind, action?, label, status(pending|running|completed|failed|skipped)
  input, output, error?, latency_ms, started_at, finished_at

IOC
  id, type(file|ip|domain|hash|email|url), value, source, first_seen,
  reputation_score, threat_verdict, occurrences

Settings
  risk_weights{severity, ti_hit, ransom_index, critical_asset, ...}
  integrations{name: {enabled, latency_ms, failure_rate}},
  instance{label, timezone}
```

## 3. Lifecycle

- **Seeding:** first launch creates a healthy demo dataset so every screen is
  populated (see `soar_lite/seed.py`). Triggered when `data/.seed_marker` is
  absent; re-run via Settings -> Reset data (calls `POST /api/admin/reset`).
- **Incident:** `open -> triage -> contained -> eradicated -> recovered -> closed`.
  Closing stamps `closed_at`. Reopening moves back to `recovered`.
- **Execution:** `queued -> running -> completed | failed | cancelled`. A
  running execution keeps the incident phase in `containment` until finished.
- **IOCs:** deduplicated by `type:value`; reputation refreshed by TI adapter
  during playbook runs.

## 4. Durability semantics

- Every mutation is persisted immediately (write-through).
- **Atomic writes:** temp file + `os.replace()` under a collection `RLock`.
- Process crash mid-run leaves an execution with status `running` and
  `was_interrupted=true`; on boot, `Store.recover()` marks those as `failed`
  with a synthetic note so the queue never looks permanently stuck.
- No WAL / no transactions - acceptable, each step write is small and atomic.

## 5. Concurrency model

- `Store` uses per-collection `RLock`s; engine workers hold locks only for the
  duration of a single step mutation, never during simulated sleep.
- API reads use the same locks -> snapshot-consistent reads.
- Reports snapshot incident+execution before rendering, so a report is a point
  in time even if the incident keeps changing.

## 6. Resetting state

```
DELETE /api/admin/reset   (or Settings page button)
```
Backs up `data/` to `data/backups/<timestamp>/` then re-seeds. History is
preserved in the backup folder for audit review.

## 7. State integrity checklist (used by tests)

- No execution references a missing incident or playbook.
- Every RunStep has a terminal status.
- `current_step_id` always points at a real step when status != completed.
- Risk score within 0-100.
- References in playbook `on:`/`next`/`goto` resolve to valid step ids.