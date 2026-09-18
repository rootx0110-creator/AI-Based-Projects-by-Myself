# Memory — PortScanPro knowledge base

`memory.json` is PortScanPro's long-term memory: every scan makes the next scan smarter.

## What is remembered

Per host:

- `first_seen` / `last_seen` timestamps (UTC)
- Every port that has **ever** been observed open, with:
  - `service` — well-known name guess by port number (e.g. `22 → ssh`)
  - `product` / `version` — when banner/version detection succeeded (e.g. `OpenSSH 6.6.1p1`)
  - `times_seen` — in how many scans the port stayed open (reliability signal)
  - `last_seen` — last time this specific port was confirmed open

Globals:

- `total_scans` — how many host scans have ever run
- `total_hosts` — how many distinct hosts are tracked

## How memory is used

| Moment | Behavior |
|---|---|
| Scan starts on a known host | Prints a **memory hint**: up to 10 previously open ports with product/version and a `seen N×` badge — you instantly see what changed compared to the past. |
| Scan finishes | All newly confirmed facts are merged into memory (append/overwrite, never delete). |

## Design notes

- **Additive merge**: ports that close later are *not* deleted — they simply stop updating `last_seen`. This preserves history for trending ("port 8080 was open in August, gone in September").
- **Latest-wins for identity**: if a service banner changes (e.g. server upgraded Apache 2.4.29 → 2.4.62), memory keeps only the newest identification.
- **Self-healing**: unreadable/corrupt `memory.json` resets to an empty knowledge base instead of crashing.
- **No-op friendly**: `--no-state` skips both state and memory writes for ephemeral runs.

## Example workflow

```bash
# Monday: first scan
PortScanPro.exe scanme.nmap.org

# Tuesday: memory hint appears before scanning
#   [*] Memory: previously seen 2 open port(s) on this host
#       · 22     OpenSSH 6.6.1p1  (seen 1x)
#       · 80     http             (seen 1x)
PortScanPro.exe scanme.nmap.org -p 1-1024
```

## Manual editing

The file is plain JSON — safe to inspect, diff, or reset:

```bash
rm memory.json     # full amnesia
```
