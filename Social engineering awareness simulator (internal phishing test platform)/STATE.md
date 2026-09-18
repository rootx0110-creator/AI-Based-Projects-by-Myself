# STATE.md — SeaSim Current State

Snapshot of the project's build/verification state. Update this file
whenever the app is rebuilt or new verification is run.

**Last updated:** 2026-09-17 (full-workflow pass + bugfix + rebuild)

---

## 1. Deliverable status

| Item | State | Location |
|---|---|---|
| Source package `seasim/` | ✅ complete (18 files, ~3,400 lines) | `seasim/` |
| Compiled bytecode check | ✅ clean (`python -m compileall`) | — |
| Engine smoke tests | ✅ 9/9 pass | see MEMORY.md §5 |
| GUI smoke tests | ✅ all views + end-to-end campaign pass | see MEMORY.md §5 |
| Icon asset | ✅ generated (5 frames, 2.9 KB) | `build/SeaSim.ico` |
| Windows executable | ✅ built, launches, stays alive | `dist/SeaSim.exe` (12.7 MB, PE32+ GUI) |
| → rebuilt 2026-09-17 | both builds current with all fixes | `dist/SeaSim/SeaSim.exe`, `dist/SeaSim.exe` |
| Docs | ✅ ARCHITECTURE.md / MEMORY.md / STATE.md / README.txt | project root |

## 2. Feature checklist (all implemented)

- [x] Dashboard with program metrics + getting-started
- [x] Participants: add/edit/import CSV/toggle/delete, active flags
- [x] Templates: 8 built-ins (incl. 2 AI-themed), preview, duplicate,
      custom editor, delete (built-ins protected)
- [x] Campaign wizard: 7 steps (name → template → recipients → mode →
      schedule → review → authorize)
- [x] Recipient guards: active-only, duplicates, syntax, 500 cap,
      >100 extra confirmation
- [x] Authorization workflow: policy text, tick-box policy
      acknowledgement (no typed phrase), operator sign-off, AI-content
      extra consent, immutable consent log
- [x] Launch engine: draft→active→completed, rate-limited delivery
      thread, cancellable, per-recipient events
- [x] Inbox simulation: open / click / report / dismiss per email
- [x] Just-in-time training window on click & report; `trained_at` set
- [x] Training log view (all delivered moments)
- [x] Campaign detail: metric strip + per-participant outcomes
- [x] Reports: text report, HTML report export, events CSV,
      department CSV, program JSON export/import
- [x] Settings: org/operator, JIT toggle, tracking toggle, reminder
      days, locked safe-mode panel, reset-all
- [x] Loopback SMTP stub (binds 127.0.0.1:8025 only, refuses non-local)
- [x] Autosave (debounced + atomic) and corrupt-file quarantine

## 3. Runtime state on a user machine

| Path | Contents |
|---|---|
| `%LOCALAPPDATA%\SeaSim\seasim_data.json` | all app state (single file) |
| `%LOCALAPPDATA%\SeaSim\seasim.log` | reserved for future file logging |
| override | set `SEASIM_DATA_DIR` before launch (portable/dev use) |

The exe itself writes nothing next to itself (Program Files friendly).

## 4. Build & rebuild

```bash
# from project root
python build/icon.py                # only if icon changed
python -m PyInstaller SeaSim.spec --noconfirm
# → dist/SeaSim.exe
```

Requirements on build host: Python 3.10+ with Tk, `pip install
pyinstaller`. Build host used: Python 3.14.7, Tk 9.0, PyInstaller 6.22.2.

## 5. Verification matrix (latest run)

One command re-runs everything (isolated throwaway data dir):

```bash
python tools/selftest.py
```

Latest result: **17 passed, 0 failed** —

| Check | Result |
|---|---|
| Launch blocked without consent / without policy ack | PASS ×2 |
| Consented launch completes + click/report scoring | PASS |
| Dismiss path | PASS |
| Stats + text report + program totals | PASS |
| Recipient guards (unknown/inactive) | PASS |
| External host refused | PASS |
| Rate cap 60/min | PASS |
| Ack phrase constant | PASS |
| JSON persistence roundtrip | PASS |
| All 9 views build | PASS |
| Campaign detail view | PASS |
| Live click → JIT `trained_at` via event pump | PASS |
| Training log view | PASS |
| Inbox refresh twice (no widget leak) | PASS |
| SMTP stub roundtrip (port-fallback aware) | PASS |
| Store reload from disk | PASS |
| `dist/SeaSim.exe` launch probe (alive after 6 s) | PASS |

## 6. Session log

- **2026-09-16 — initial build.** Full implementation in one session:
  engine, safety envelope, consent flow, templates, JIT, reports,
  mailer stub, 9 views + wizard, app shell, icon generator, spec,
  exe build. Fixed during the session: missing `ORG_DEFAULT` import;
  `tk.Label style=` misuse (removed all); JIT double-path consolidated
  into the Tk event pump; SMTP stub restart (`_stop.clear()`) and
  app-startup stub wiring; icon.py negative-float power crash.
- **2026-09-16 — testing pass.** Added `tools/selftest.py` (17 checks,
  one command, isolated data dir). Found and fixed:
  (1) `Engine.launch` skipped the `policy_ack` check — consent is now
  validated FIRST in `_validate_launch`, before template/schedule
  checks; (2) SMTP stub could deadlock on Python 3.14/Tk 9.0 — its
  logger called `self.after()` from a background thread; stub logs now
  flow through the app's thread-safe event queue; (3) stub now falls
  back to ports 8026–8035 when 8025 is taken and the mailer client
  follows `bound_port`. Exe rebuilt and launch-verified.
- **2026-09-17 — full-workflow pass (43 checks).** Added a throwaway
  end-to-end driver that walks EVERY menu/workflow through the real
  Tk views: dashboard, participants (add/edit/toggle/import CSV/
  delete), templates (new/preview/duplicate/edit built-in/delete),
  wizard 7 steps with the REAL 3-page consent dialog + launch +
  delivery, campaigns list/detail/guarded launch/cancel/delete,
  inbox open/click+JIT/report/dismiss, training log, reports
  (text/CSV/JSON), settings (save/log/import JSON), smtp stub,
  scheduled draft, clean close. **Found and fixed one real runtime
  crash:** Settings → "Reset all data" raised
  `NameError: builtin_templates` because `seasim/ui/views2.py` never
  imported it — added the import; reset now works and re-seeds the
  8 built-ins. Both exes rebuilt, launch probe PASS on each.
- **2026-09-17 — customization pass (44 checks).** (1) Consent step 2
  became tick-only: the read-and-type phrase entry was replaced by a
  policy acknowledgement checkbox (`seasim/consent.py`); `POLICY_TEXT`
  in `seasim/safety.py` updated to say the checkbox is the electronic
  signature. (2) Reports gained an HTML export — new
  `build_html_report()` in `seasim/reports.py` (self-contained styled
  page: metric tiles, campaign meta, department table, notes) plus an
  "HTML report..." save button in the Reports view. Workout extended
  to drive the tick-box consent and the HTML export: 44/44 PASS;
  selftest 17/17. Both exes rebuilt and launch-verified.

## 7. Open items

- None blocking release. Future roadmap lives in MEMORY.md §6
  (trend charts, scheduled-launch dashboard prompts, reminders,
  localization).
