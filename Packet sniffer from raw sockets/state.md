# state.md — Persisted State Design

`state.json` (in `runtime/`) stores the **current state machine of the app** so a
session can be paused, closed, inspected, or resumed without losing context.

## 1. State machine

```
            START (admin OK)
   ┌──────┐          ┌───────────┐   pause/resume   ┌──────────┐
   │ IDLE │ ───────► │ CAPTURING │ ◄──────────────► │ PAUSED   │
   └──────┘          └───────────┘                  └──────────┘
      ▲                   │    socket error / stop
      │  stop / app exit  ▼
      └─────────────── STOPPED (summary shown, report available)
```

Transitions: `START → CAPTURING → (PAUSED ⇄) → STOPPED → (reset) → IDLE`.
`ERROR` overlays any state when the raw socket cannot be opened (no admin).

## 2. What is persisted

| Key | Type | Notes |
|---|---|---|
| `version` | int | Schema version |
| `saved_at` | str | ISO timestamp of last write |
| `phase` | enum | `idle / capturing / paused / stopped / error` |
| `session` | obj | `{id, started_at, ended_at, packets, bytes, drops}` |
| `last_interface` | str | Adapter IPv4 selected last time |
| `filter` | str | Active display filter text |
| `quick_filters` | list | Enabled protocol chips (`TCP`, `UDP`, ...) |
| `stats_snapshot` | obj | `{by_protocol:{}, by_endpoint:{}, by_conversation:{}}` |
| `last_report` | obj | `{path, generated_at, packets}` |
| `errors` | list | Last 10 runtime errors (for the Report tab) |

## 3. When it is written

- Every state transition (`start`, `pause`, `resume`, `stop`) — immediately.
- Heartbeat: every ~5 s while capturing (stats snapshot refresh).
- On app close.

Writes are **atomic** (write temp, `os.replace`) so a crash mid-write never
corrupts the file. `state.json` is also what the Report tab reads to include a
"session summary" section, and what the app restores at startup
(last interface + filter).

## 4. Example

```json
{
  "version": 1,
  "saved_at": "2026-09-11T10:24:31",
  "phase": "capturing",
  "session": {
    "id": "s-20260911-102403",
    "started_at": "2026-09-11T10:24:03",
    "ended_at": null,
    "packets": 1287,
    "bytes": 914552,
    "drops": 0
  },
  "last_interface": "192.168.1.20",
  "filter": "tcp.port == 443",
  "quick_filters": ["TCP", "UDP"],
  "stats_snapshot": {
    "by_protocol": {"TCP": 1011, "UDP": 210, "ICMP": 66},
    "by_endpoint": {"192.168.1.20": {"packets": 900, "bytes": 700000}},
    "by_conversation": {"192.168.1.20 ⇄ 142.250.4.100": {"packets": 800, "bytes": 640000}}
  },
  "last_report": {"path": "runtime/sniffer_report.html", "generated_at": "2026-09-11T10:24:30", "packets": 1287},
  "errors": []
}
```
