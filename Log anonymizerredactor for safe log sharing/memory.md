# Memory

> Working notes for maintainers of the **Log Anonymizer & Redactor**.
> This file documents "how we got here", design decisions, traps, and
> refactoring pointers. It is not a user guide (see readme.txt).

## Project Genesis

- Goal: let people share logs with support / vendors / AI assistants without
  leaking PII — via a polished desktop `.exe`.
- Constraints discovered early:
  - Must run fully offline (data never leaves the machine).
  - Must ship as a single `.exe` without a huge dependency tree (so no
    spaCy/ML models; regex-only detection).
  - Must feel "beautiful" (tabs, toggles, theming) → customtkinter.

## Key Decisions & Why

### 1. Regex-only detection
Chosen over ML/NER. Cheap, deterministic, offline, and accurate enough for the
common log patterns (IPs, e-mails, tokens, cards). Trade-off: misses awkward
case formats; acceptable for v1.

### 2. Fixed-order mode processing
`Redactor.MODES` is a plain dict; iteration order is the pipeline order.
Ordering is **not cosmetic**: broad modes must run after specific ones so they
never split a value already masked by a specific mode.

Ordering rationale (must be preserved):
- `pan` before `phone` → phone would otherwise chop card numbers.
- `arn` before `phone` → ARN account ids (`123456789012`) would be
  miscounted as phone numbers.
- `jwt` before `passwd` → passwd's 80-char value cap previously truncated a
  120-char JWT, leaving the tail exposed (`...gRG***` bug).
- `latlon` before `phone` → phone was eating `122.4194` and causing
  double-masking (`lon=-12******`).

### 3. keep_prefix + validator mechanism
Two Python-3.14 realities forced design changes:
1. **Variable-width lookbehinds are rejected** by `re` in newer Pythons. Any
   pattern that wants to keep a literal prefix (`password=`, `lat=`,
   `/users/<id>`) now:
   - puts the *value* in the **last capture group**,
   - sets `keep_prefix=True` on the `ModeEntry`,
   - and the callback recomputes the prefix as
     `m.group(0)[: m.start(last) - m.start(0)]`.
   - ⚠️ Trap we hit: using `m.end(last)` instead of `m.start(last)` re-emits
     the whole value as "prefix" (`password=Hunt3r2!PasswordHun***`).
2. **Phone false positives** (dates `2026-09-15`, dotted quads, time strings)
   are filtered by a `validator` callable instead of clever regex. Values that
   fail validation are left untouched and not counted.
   - Phone validator minimum: 7–15 digits, not an ISO date, no `: , ;`,
     not a 4-part dotted numeric quad.

### 4. Customtkinter 6.0 breakages
- `CTkTabview` does **not** accept a `font` kwarg in ctk 6.x (removed).
- Radio groups need a shared `StringVar`; do **not** pass `variable=None`
  (that renders them selectable but ungrouped/duplicated).
- Status bar / theme toggle need to read `ctk.get_appearance_mode()`.

### 5. Threading
Redaction runs in a daemon worker thread. A worker touches **no Tkinter at all**
— it only pushes `(kind, original, payload)` onto a `queue.Queue`. The main
thread polls the queue through `self.after(..., self._poll_results)` and does
all widget updates there. This avoids the classic `RuntimeError: main thread
is not in main loop` (calling `.after()` from a worker) and keeps a single
thread owning Tk. Guarded by `app._busy` to prevent re-entry.

## Bug Log (regressions fixed)

| Bug | Symptom | Fix |
|-----|---------|-----|
| Prefix slice used `end` | `password=Hunt3r2!PasswordHun***` | use `m.start(last)-m.start(0)` |
| Phone too greedy | `2026-09-15`, `08:41` masked | candidate regex + validator |
| Phone range 6–16 | `4111 1111 1111 1111` left a trailing `1111` | widen to `{6,20}` |
| IPv6 regex | `2001:db8::ff00:42:8329` unmatched | OWASP-style compressed alternations |
| IPv6 false pos | `:9000` after ports | lookbehind `(?<![0-9a-fA-F:])` |
| passwd cap 80 | JWT tail exposed | run `jwt` first + raise cap to 256 |
| PAN before phone | card partially masked | reorder modes |
| ARN account id as phone | `123456789012` phone count | `arn` before `phone` |
| latlon before phone | `lon=-12******` double mask | reorder, keep prefix first |

## Remaining Gaps / Future Work

- **Hash strategy is not strong pseudo-anonymization** — SHA-256[:10] is a
  risk token (40 bits). If users need unlinkable/anonymized tokenization,
  replace with a salted HMAC + persistent mapping, or truly random tokens.
- **Locale-specific formats** (IBAN, Indian PAN, German phone lengths) are
  not covered yet; adding a mode is a one-entry change.
- **`.env` / structural files** (INI, JSON, YAML, XML) would benefit from
  key=value-aware parsing rather than pure regex; a `TextProcessor` mode
  could be added later.
- **No unit-test suite yet** — `tmp_debug.py` probes exist. A `tests/
  test_redactor.py` using pytest is the recommended next step.

## One-Line Legend
- `core.redactor.Redactor` — engine; add a `ModeEntry` to extend.
- `core.html_report.build_html_report` — HTML exporter; keep self-contained.
- `app.py` — UI plumbing; keep Tk touches on the main thread.
- `build_exe.py` — PyInstaller wrapper.
- Sample fixtures live in `sample/sample.log`.