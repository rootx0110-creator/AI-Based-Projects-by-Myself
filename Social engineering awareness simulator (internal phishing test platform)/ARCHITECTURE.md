# SeaSim — Architecture

**SeaSim** (Social Engineering Awareness Simulator) is a Windows desktop
application for authorized security teams to run *simulated* phishing
awareness campaigns against their own organization, measure
susceptibility, and deliver just-in-time training.

Non-negotiable design constraints (enforced in code, not just policy):

| Constraint | Enforcement |
|---|---|
| No real credential harvesting | No credential field exists in any model; templates link to an educational JIT window only |
| No external targeting / delivery | `safety.ensure_local_only()` + loopback-only SMTP stub; `assert_safe()` gates every launch |
| Full consent workflow | `ConsentDialog` (3 steps) + typed policy ack phrase; engine refuses launch without it |
| Bounded blast radius | 500-recipient cap, 60/min rate cap, safe-mode flag that cannot be disabled in the UI |

---

## 1. Layer map

```
┌────────────────────────────────────────────────────────────┐
│ run_seasim.py / seasim.__main__      entry points          │
├────────────────────────────────────────────────────────────┤
│ seasim.app  (App shell)                                    │
│  ├── main window, sidebar navigation, status bar           │
│  ├── consent launch flow (launch_with_consent)             │
│  ├── engine-event pump (threads → Tk via queue)            │
│  └── timers: autosave (2 s), housekeeping (10 min)         │
├──────────────────────┬─────────────────────────────────────┤
│ seasim.ui            │  views.py  views2.py                │
│  theme.py (tokens,   │  Dashboard, Campaigns, Campaign     │
│  ttk styles, cards)  │  Detail, Participants, Templates,   │
│  dialogs.py (modal   │  Inbox, Training, Reports, Settings │
│  dialogs, forms)     │  WizardView (7-step creation)       │
├──────────────────────┴─────────────────────────────────────┤
│ seasim.consent   3-step authorization dialog (modal)       │
├────────────────────────────────────────────────────────────┤
│ seasim.engine                                              │
│  models.py  dataclasses + JSON (de)serialization           │
│  store.py   thread-safe JSON store, atomic writes          │
│  engine.py  lifecycle, delivery thread, event bus, scoring │
├────────────────────────────────────────────────────────────┤
│ seasim.safety    invariants, policy text, RateGate         │
│ seasim.templates builtin awareness templates               │
│ seasim.reports   aggregates, CSV, text report              │
│ seasim.mailer    loopback SMTP stub + best-effort client   │
│ seasim.jit       just-in-time training window              │
├────────────────────────────────────────────────────────────┤
│ seasim.constants app identity, paths, caps                 │
└────────────────────────────────────────────────────────────┘
```

Dependency rule: arrows point **downward only**. `engine` knows nothing
about Tk; `ui` never touches the disk except through `store`.

## 2. Runtime data flow

```
WizardView ──create_campaign──▶ Engine ──▶ Store.campaigns
                                   │
                    launch_with_consent (App)
                                   │
                     ConsentDialog (3 steps, modal)
                        │ scope / policy-ack / sign-off
                                   ▼
                    Engine.launch ──▶ safety checks
                                   │ consent recorded to settings log
                                   ▼
                 delivery thread (rate-limited, cancellable)
                        │  per participant:
                        ├─ CampaignEvent(Sent) → store
                        ├─ SmtpMailer.send → loopback stub (best-effort)
                        └─ bus.emit("delivery")
                                   ▼
            App._pump (queue → Tk thread) → status bar
                                   │
     Inbox interactions: mark_opened / click / report / dismiss
                        │
                        ├─ status transition + timestamps
                        ├─ risk_score (template difficulty bump)
                        └─ bus.emit("training")
                                   ▼
              JITWindow (educational moment) + trained_at set
                                   ▼
        ReportsView / reports.py → stats, CSV, text report
```

Key decisions:

* **Single JIT path.** JIT windows are opened only from the Tk-side
  event pump (`App._pump`), never from engine threads or view code —
  this avoids duplicate windows and cross-thread Tk calls.
* **Best-effort SMTP.** Delivery never blocks on the stub; if the sink
  is down, the simulation continues (the event ledger is the truth).
* **Coarse data only.** Events store timestamps + status + a risk
  score. There is no field anywhere that could hold message content,
  keystrokes, or credentials.

## 3. Threading model

| Thread | Owner | Notes |
|---|---|---|
| Tk main | `App` | all UI; drains `_q` every 120 ms |
| delivery-N | `Engine._start_delivery` | daemon; cancellable via `threading.Event`; sleeps in slices |
| smtp-stub accept/handle | `LocalSmtpStub` | daemon; loopback bind check per connection; logs via `App._q` (never calls Tk) |
| store lock | `threading.RLock` | guards every dict mutation; atomic writes via `os.replace` |

UI mutations after engine events always happen on the Tk thread.

## 4. Persistence

One JSON document at `%LOCALAPPDATA%/SeaSim/seasim_data.json`
(override with `SEASIM_DATA_DIR`).

```
{
  "schema_version": 2,
  "created": "...", "updated_at": "...",
  "settings":   { org, operator, jit_training, consent_log[] },
  "participants": { prt_id: {...} },
  "templates":    { tpl_id: {...} },   # builtins re-seeded by name
  "campaigns":    { cmp_id: {...} },
  "events":       { evt_id: {...} }
}
```

* Writes are debounced (0.5 s) + atomic (`.tmp` + `os.replace`).
* Corrupt files are quarantined as `*.corrupt.bak`; app starts clean.
* Built-in templates are re-seeded by **name**, so operator edits to
  custom copies survive resets.
* Full-document export/import (`export_json` / `import_json`) is the
  backup path; import replaces state after an explicit confirm.

## 5. Safety envelope (`seasim/safety.py`)

* `POLICY_TEXT` — the 7-point authorized-use policy quoted verbatim in
  both the wizard and the consent dialog.
* `ACK_PHRASE` — typed acknowledgement (`"I HAVE READ AND AGREE"`).
* `assert_safe(store, campaign)` — raises `SafetyViolation` if safe
  mode is off, consent/policy ack missing, recipients invalid, or rate
  exceeds the cap. Called by the engine before any launch.
* `validate_recipients` — existence, active status, address syntax,
  duplicate detection, `MAX_RECIPIENTS` cap.
* `RateGate` / `check_rate` — pacing; ceiling is `constants.RATE_PER_MINUTE`.
* `ensure_local_only` — refuses any non-loopback host/port (used by
  both mailer client and stub server).

## 6. Scoring model

`Engine.risk_score = base(status) + difficulty bump`

| Status | Base | Difficulty bump (Low/Med/High) |
|---|---|---|
| Opened | 30 | +0 / +10 / +20 |
| Clicked | 70 | +0 / +10 / +20 |
| Reported / Dismissed | 0 | — |

`CampaignStats.resilience` = (reported + dismissed) / sent. The score
is a *coarse program metric*, not a per-person judgment; README and the
UI both state results are for training, not discipline.

## 7. Build pipeline

```
python build/icon.py                 # generates build/SeaSim.ico (pure stdlib)
python -m PyInstaller SeaSim.spec    # onefile windowed exe → dist/SeaSim.exe
```

* `SeaSim.spec` excludes heavy libs (numpy/pandas/PIL/…); final exe is
  ~12.7 MB because the only dependency is the Python/Tk stdlib.
* `run_seasim.py` is the frozen entry; it also inserts the exe dir on
  `sys.path` for onefile layouts.
* Dev run: `python -m seasim` (identical code path as the exe).

## 8. UI architecture notes

* `theme.py` owns every color/font constant; views never hard-code hex
  values (they import `seasim.ui.theme as T`).
* Views are rebuilt on navigation (no incremental diffing) — state is
  small enough that full rebuilds are simpler and bug-free.
* `Sidebar.highlight` reflects the active route; campaign detail is a
  transient route outside the sidebar map.
* Plain `tk.Label` is used everywhere with explicit `bg/fg/font`;
  ttk styles exist for Treeview/Buttons/Combobox only. (tk.Label has
  no `style=` option — a bug we hit and fixed; keep it that way.)
