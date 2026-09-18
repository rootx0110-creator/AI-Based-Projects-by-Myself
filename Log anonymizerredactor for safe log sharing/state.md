# State

This file captures the **behavioral contract** of the Log Anonymizer &
Redactor application so future maintainers can reason about what it does
without reading all of it, and so tests can assert against one source of truth.

## Runtime State

### Application-level (in-memory)

| Variable               | Owner            | Type                          | Meaning                                  |
|------------------------|------------------|-------------------------------|------------------------------------------|
| `enabled`              | `LogRedactorApp` | `dict[str, bool]`             | Which detection modules are toggled on   |
| `strategy`             | `LogRedactorApp` | `str`                         | Active redaction strategy key            |
| `last_result`          | `LogRedactorApp` | `RedactionResult \| None`     | Result of the most recent run (or None)  |
| `last_original`        | `LogRedactorApp` | `str`                         | Raw input of the most recent run         |
| `_busy`                | `LogRedactorApp` | `bool`                        | Thread run lock, prevents re-entry       |
| `mode_switches`        | `LogRedactorApp` | `dict[str, ctk.CTkSwitch]`    | UI toggles, mirrors `enabled`            |
| `_strategy_var`        | `LogRedactorApp` | `ctk.StringVar`               | Radio group value                        |
| `status_label`         | `LogRedactorApp` | `ctk.CTkLabel`                | Last status message                      |
| `stats_label`          | `LogRedactorApp` | `ctk.CTkLabel`                | "N items · X ms" legend                  |
| `progress`             | `LogRedactorApp` | `ctk.CTkProgressBar`          | 0 → 1 during a run                       |
| `counts` / `samples`   | `RedactionResult`| `dict[str, int/list[str]]`    | Per-mode tallies after a run             |
| `elapsed_ms`           | `RedactionResult`| `float`                       | Duration of the last `redact()` call     |

### Persisted state

The application is intentionally **stateless on disk**:

- no config is written between launches (theme and toggles reset to defaults);
- nothing is cached, logged, or uploaded;
- the only files the *user* creates are manual exports
  (HTML report, `.txt` of the sanitized log) via save dialogs.

## Startup Sequence

1. `main()` → logs version, constructs `LogRedactorApp`.
2. `__init__`:
   - set window title/size/minsize;
   - `_configure_theme()` → dark appearance, blue CTk palette;
   - `_build_header()` → title, tagline, theme toggle;
   - `_build_tabs()` → 4 tabs (Redact, Options, Report, About);
   - `_build_statusbar()` → status line at the bottom;
   - `after(80, _safe_load_icon)` → load `assets/app.ico` if present.

## Module State Contract

`Redactor` is deterministic and stateless between calls (all per-run counters
live inside `redact()`). Construction options:

| Argument     | Default   | Valid                              |
|--------------|-----------|------------------------------------|
| `strategy`   | `mask`    | `mask` `full` `hash` `token`       |
| `mask_keep`  | `3`       | any `int >= 0`                     |

`redact(text, enabled=None)`:

- `enabled=None` ⇒ every module runs;
- `enabled={key: bool}` ⇒ modules not mentioned still default to **True**;
  modules mapped to `False` are skipped. (UI always passes a complete dict.)

Precondition / postcondition:

```
redact() never raises for arbitrary strings.
output text length <= input length + small growth from prefix re-emission
  (mask/full always shrink or keep; token/hash grow slightly).
counts sum == number of distinct replacements made.
Appending to input text never lowers any single-mode count.
```

## Redaction Invariants

- **Order** is fixed by dict order in `Redactor.MODES` and must be preserved.
  Adding a new mode at the end is safe; injecting one into the middle requires
  re-checking partial-mask interactions (see architecture.md).
- **keep_prefix modes** re-emit the prefix literal and only replace the last
  capture group (the value). Never add trailing capture groups to those
  patterns.
- **validators** must be pure functions returning `bool`; returning `False`
  causes the match to be left untouched and not counted. They run before
  counting/sampling.
- **Samples** are limited to at most 12 per category and only the first sample
  enters the HTML table.
- The **same input** yields the **same output** for `mask`, `full`, and `hash`
  strategies across runs (thread-safety: `redact()` must not be called
  concurrently on one `Redactor` instance).

## UI State Transitions

| Action              | Before             | After                                       |
|---------------------|--------------------|---------------------------------------------|
| Toggle a switch     | `enabled[k]=bool`  | switches are non-persistent; affects next run |
| Radio change        | `strategy` updated | affects next run only                       |
| Click Anonymize     | `_busy=False`      | `_busy=True`, button disabled, progress 0.15|
| Worker completes    | —                  | `_redact_done` on UI thread, progress = 1   |
| `_redact_done` ok   | —                  | `last_result/result` set, output box filled |
| `_redact_done` fail | —                  | status "Error: …", modal error box          |
| Download report     | needs `last_result`| file saved; optional browser open           |

## Failure Modes

| Problem                      | Behavior                                          |
|------------------------------|---------------------------------------------------|
| Empty input                 | `_start_redact` shows "Nothing to do" info box    |
| File read error             | modal error box, status unchanged                 |
| Engine exception            | status "Error", error box; `_busy` reset          |
| `core/html_report` missing  | download blocked with "Missing module" message    |
| Clipboard unreadable        | info box, input unchanged                         |

## Report Contents Contract

`build_html_report` only ever embeds:

- counts, redaction strategy label, elapsed time, char reduction stats;
- **masked** previews only (`first≤3 chars…***`) — raw samples are collected
  in memory but are never written into the HTML;
- the sanitized output (truncated to 8000 chars in the `<pre>` block);
- settings that were in effect.

It must **never** contain raw untruncated values.