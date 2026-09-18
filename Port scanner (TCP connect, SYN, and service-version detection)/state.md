# State — PortScanPro runtime state

This document describes **what state the application produces and how it evolves**. The companion JSON files are the machine-readable mirror of this page.

## Files

| File | Purpose | Retention |
|---|---|---|
| `state.json` | History of recent scan sessions (append + trim) | last 20 sessions |
| `memory.json` | Aggregated long-term knowledge per host | grows; one entry per host |

Both files are created next to the working directory at scan time. Paths can be overridden with `PSP_STATE_FILE` / `PSP_MEMORY_FILE`; writing can be disabled entirely with `--no-state`.

## state.json — session history

Written after **every** host scan by `record_state()`:

```json
{
  "sessions": [
    {
      "ts": "2026-09-10T12:34:56Z",
      "target": "scanme.nmap.org",
      "tcp_connect": { "open": [22, 80], "closed": [21, 23], "filtered": [25], "total": 100 },
      "syn":         { "open": [22, 80], "closed": [21, 23], "filtered": [25], "total": 100 },
      "services": {
        "22":   { "port": 22, "service": "ssh", "product": "OpenSSH", "version": "6.6.1p1", "banner": "...", "tls": false },
        "80":   { "port": 80, "service": "http", "product": null, "version": null, "banner": null, "tls": false }
      },
      "ports_scanned": [21, 22, 23, 25, 80]
    }
  ]
}
```

Rules:
- Newest sessions are appended; when the list exceeds **20**, the oldest are dropped.
- With `--scan both`, both engine payloads are stored, enabling later diffing.
- Keys `syn`/`services` may be absent depending on flags (`-s connect --no-detect`).

## memory.json — knowledge base

Updated by `update_memory()` after each host scan:

```json
{
  "hosts": {
    "scanme.nmap.org": {
      "first_seen": "2026-09-10T12:34:56Z",
      "last_seen": "2026-09-10T13:00:00Z",
      "ports": {
        "22": {
          "service": "ssh",
          "product": "OpenSSH",
          "version": "6.6.1p1",
          "times_seen": 3,
          "last_seen": "2026-09-10T13:00:00Z"
        }
      }
    }
  },
  "total_scans": 7,
  "total_hosts": 1
}
```

Rules:
- `times_seen` increments each scan where the port was open again.
- `product`/`version` are overwritten whenever version detection succeeds (memory always reflects the **latest** identification).
- `total_scans` counts host-scan invocations; `total_hosts` equals the number of keys in `hosts`.

## Behavior at scan time

1. **Before scanning** a host, `print_memory_hint()` prints up to 10 previously-known open ports in magenta — instant recon from past runs.
2. **After scanning**, both files are saved and the paths are echoed in the summary line.
3. Corrupt/missing files are treated as empty (`_load_json` falls back to the default) — the app never crashes on bad state.

## Resetting state

```bash
rm state.json memory.json          # bash
del state.json memory.json         # cmd
```
