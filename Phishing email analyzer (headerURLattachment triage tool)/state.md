# Phishing Email Analyzer — State Document

> Living document describing application state, transitions, and lifecycle.

## Application States

```
┌─────────┐    launch     ┌──────────────┐    email selected    ┌──────────────┐
│  IDLE   │ ────────────► │  LOADING     │ ───────────────────► │  PARSING     │
└─────────┘               └──────────────┘                      └──────┬───────┘
     ▲                            ▲                                  │ parse ok
     │                            │                                  ▼
     │      window closed      ┌──────────────┐              ┌──────────────┐
     └──────────────────────── │   SHUTDOWN   │ ◄─────────── │  ANALYZING   │
                               └──────────────┘              └──────┬───────┘
                                                                  │ done
                                                                  ▼
                                                          ┌──────────────┐
                                                          │ REPORT READY │
                                                          └──────┬───────┘
                                                                 │ export
                                                                 ▼
                                                          ┌──────────────┐
                                                          │  EXPORTED    │
                                                          └──────────────┘
```

## State Descriptions

| State          | Conditions                                                          | Actions available                    | Exit conditions                      |
| -------------- | ------------------------------------------------------------------- | ------------------------------------ | ------------------------------------ |
| `IDLE`         | App started, no email loaded                                        | Load file, paste email, open history | File selected / text pasted          |
| `LOADING`      | File opened, size checked, MIME sniffed                             | Cancel                               | Read success → PARSING               |
| `PARSING`      | Message object constructed; headers/body parts extracted            | Cancel                               | Parser success → ANALYZING           |
| `ANALYZING`    | Analyzers running; progress shown on progress bar                   | Cancel                               | All analyzers complete → REPORT_READY |
| `REPORT_READY` | Score + verdict computed; tabs populated                            | Export HTML, rescan, new analysis    | Export / new email / app close       |
| `EXPORTED`     | HTML report written to disk                                        | Open file, location, continue        | Next action                          |
| `SHUTDOWN`     | User closes window; state saved to `data/app_state.json`            | —                                    | Process exit                         |

## Persisted State (`data/app_state.json`)

```json
{
  "theme": "dark",
  "history": [
    {
      "id": "6f1c…ab",
      "timestamp": "2026-09-15T13:04:22Z",
      "subject": "Invoice 44522",
      "sender": "admin@paypal-security.com",
      "score": 87,
      "verdict": "HIGH RISK",
      "url_count": 2,
      "attachment_count": 1
    }
  ],
  "max_history": 10
}
```

- History prunes to `max_history` entries.
- The last analysis is only persisted when an email is successfully analyzed.

## Session State (In-Memory)

| Field              | Type          | Description                          |
| ------------------ | ------------- | ------------------------------------ |
| `current_email`    | `<EmlMail>`   | Parsed email object                  |
| `parse_error`      | `str\|None`   | Last parse failure reason            |
| `headers`          | `dict`        | Normalized header map                |
| `url_results`      | `list[dict]`  | Per-URL analysis                     |
| `attachment_results` | `list[dict]` | Per-attachment analysis          |
| `raw_headers`      | `str`         | Original raw header block            |
| `score`            | `int`         | Final risk score (0–100)             |
| `verdict`          | `str`         | Category string                      |
| `evidence`         | `list[dict]`  | Weighted evidence list               |
| `elapsed_ms`       | `int`         | Total analysis time                  |

## Gauge/UI State

- Risk gauge uses a segmented arc; target state is a float 0.00–1.00 fed by
  the model. Recommend animating with easing (`t_mix = (1-cos(pi*t))/2`).
- Verdict badge color derived from verdict class (CSS classes below).

### Verdict → Color palette

| Verdict    | Color       | CSS class  |
| ---------- | ----------- | ---------- |
| SAFE       | `#2ecc71`   | `v-safe`   |
| LOW RISK   | `#f1c40f`   | `v-low`    |
| MODERATE   | `#e67e22`   | `v-mod`    |
| HIGH RISK  | `#e74c3c`   | `v-high`   |
| CRITICAL   | `#8e44ad`   | `v-crit`   |

## Failure Modes

| Failure                      | Effect                                   | Recovery                                   |
| ---------------------------- | ---------------------------------------- | ------------------------------------------ |
| Unreadable / malformed email | PARSING fails                            | Show error banner, return to IDLE          |
| `.msg` (Outlook) not parsed  | Message lacks MIME structures            | Prompt user to export as `.eml` first      |
| Attachment hash error        | Missing hash shown                       | Skip hash, keep metadata                   |
| Export to unwritable path    | EXPORTED fails                           | Error dialog, user picks another location  |
| Very large email (>20 MB)    | Slow parse                               | Warn before parsing                        |

## Threading & Long-Running Tasks

- Email parse + analysis runs on a worker thread to keep the UI responsive.
- A `queue.Queue` carries results back to the main thread.
- Cancellation only allowed between analysis phases (phases are atomic).