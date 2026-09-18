# Architecture

**Log Anonymizer & Redactor** — a desktop application that desensitizes raw
log text before it is shared with third parties, vendors, or AI assistants.

## Purpose

Logs frequently contain names, IPs, e-mails, phone numbers, card numbers,
passwords, and API tokens. Sharing them "as is" leaks sensitive data. This app
replaces those values with safe placeholders while preserving the structure of
the log, and produces an HTML audit report.

## Design Principles

1. **100% local.** No network calls. No telemetry. Source text never leaves RAM.
2. **Deterministic.** Same input + same settings => same output (mask and hash).
3. **Modular.** Detection rules, masking strategies and the report renderer are
   isolated so new rules are simple to add.
4. **Single-file friendly.** The core is written without heavy ML / ORM
   dependencies so it packs into one `.exe` with PyInstaller.

## Component Map

```
┌────────────────────────────────────────────────────────────┐
│                       app.py  (entry)                       │
│         customtkinter desktop shell - 4 tabs + header      │
│  Tabs: Redact | Options | Report | About                    │
└───────────────┬──────────────────────────┬──────────────────┘
                │ builds                     │ invokes
                ▼                            ▼
   ┌──────────────────────────────┐   ┌──────────────────────────────┐
   │  core/redactor.py            │   │  core/html_report.py         │
   │  - ModeEntry registry        │   │  - build_html_report()       │
   │  - Redactor.redact()         │   │  - save_html_report()        │
   │  - strategies                │   │  - self-contained <style>    │
   │  - keep_prefix handling      │   │  - metrics + sample tables   │
   └──────────────────────────────┘   └──────────────────────────────┘
```

## Modules

### `app.py`

- `LogRedactorApp(ctk.CTk)` — the main window.
  - **Header** — title, tagline, dark/light theme toggle.
  - **Redact tab** — source log text box, output text box, `Anonymize`
    button, `Open File` / `Paste` / `Copy`, live progress + stats line.
  - **Options tab** — one toggle per detection module, radio group for the
    redaction strategy, privacy guarantees and tips.
  - **Report tab** — last-run summary with per-category counts and the
    download buttons (`Download HTML Report`, `Open in Browser`,
    `Save Sanitized Log (.txt)`).
  - **About tab** — feature list, detection catalog, tech stack.
- `LogRedactorApp._start_redact()` runs the engine in a **worker thread** and
  marshals the result back to the UI thread through `after()` so the window
  never freezes.
- `resource_path()` resolves asset paths both in source and frozen builds.

### `core/redactor.py`

Pipeline for one pass:

```
text
  └─ for each enabled ModeEntry (fixed-order dict):
        └─ regex .sub(callback) over the whole buffer
             ├─ keep_prefix modes re-emit literal prefix, mask the value
             ├─ validator-equipped modes (phone) reject numeric lookalikes
             └─ accumulate counts + up to 12 sample values per category
  └─ RedactionResult { text, counts, samples, elapsed_ms }
```

Pattern catalog (see `ModeEntry`):

| key       | label                | note                       |
|-----------|----------------------|----------------------------|
| ipv4      | IPv4 Addresses       | dotted quad                |
| ipv6      | IPv6 Addresses       | full + compressed + mapped |
| email     | Email Addresses      | user@domain.tld            |
| pan       | Credit/Debit Cards   | 4×4 with Luhn-style prefix |
| ssn       | Social Security #s   | ddd-dd-dddd                |
| uuid      | UUIDs                | 8-4-4-4-12                 |
| jwt       | JWT / bearer tokens  | eyJ…​.…​.…                   |
| cred_url  | URL credentials      | user:pass@ in URLs         |
| passwd    | Password literals    | key=value literal          |
| apikey    | API keys & secrets   | aws/stripe/oidc github…    |
| arn       | AWS ARNs             | arn:aws:iam::…             |
| latlon    | Geo coordinates      | lat= / lon= values         |
| phone     | Phone numbers        | validated to avoid dates   |
| mac       | MAC addresses        | aa:bb:cc:dd:ee:ff          |
| username  | Usernames / user ids | /users/…, user=…           |

**Ordering is significant** — more specific modules run first so broad
modules never split or double-mask a value (e.g. `pan` > `phone`, `arn` >
`phone`, `jwt` > `passwd`).

Strategies (`STRATEGY_MASK/FULL/HASH/TOKEN`):
- **mask** — keep leading characters, replace the rest with `***`.
- **full** — `{TAG-REDACTED}`.
- **hash** — `{TAG-<sha256[:10]>}` (stable across runs).
- **token** — `{TAG:UID0001}` sequential pseudonyms for analysis.

### `core/html_report.py`

`build_html_report(result, config, original) -> str` produces a single
self-contained HTML document (inline CSS, no external assets) containing:

- summary metrics (items redacted, chars removed, % reduction, time);
- per-category table with color-coded pills + truncated sample;
- configuration wording;
- truncated sanitized output;
- footer confirming the generation time and local-only processing.

`save_html_report(...)` writes it to disk.

## Data Flow (report download)

```
User clicks "Anonymize"
  └─ worker thread: Redactor().redact(text, enabled)        [core/redactor]
  └─ UI thread:     result -> stored on app.last_result
User clicks "Download HTML Report"
  └─ save_html_report(result, config, original, path)       [core/html_report]
  └─ option to open the file in the default browser
```

## Threading Model

- Tkinter must only be touched from the main thread.
- Heavy redaction of large logs happens in a daemon worker thread that never
  calls any Tk method.
- The worker pushes `("done"|"error", original, result|msg)` onto a
  `queue.Queue`; the main thread drains it every 50–100 ms via
  `after(_, _poll_results)` and performs all widget work there.

## Build & Packaging

`build_exe.py` drives PyInstaller:

| component        | purpose                               |
|------------------|---------------------------------------|
| `--onefile`      | single `dist/LogAnonymizer.exe`       |
| `--windowed`     | no console window                     |
| `--add-data core\...` | bundles the `core` package        |
| `assets/app.ico` | optional window/taskbar icon          |

The frozen app uses `sys._MEIPASS` for bundled assets (see `resource_path`).

## Extension Points

To add a new detection module:

1. add a pattern constant + `ModeEntry` inside `Redactor.MODES`;
2. (optional) give it `keep_prefix=True` and put the value in the final
   capture group, or attach a `validator` to filter lookalikes;
3. it automatically appears in the Options tab and the HTML report.

## Security Notes

- Samples kept for the report are truncated to 12 per category and only
  the first value is shown in the report table.
- No original values are ever written to disk by the app itself.
- The hash strategy uses SHA-256 truncated to 40 bits — a *risk* token, not a
  cryptographically strong pseudo-anonymization channel; do not rely on it for
  high-assurance anonymization.