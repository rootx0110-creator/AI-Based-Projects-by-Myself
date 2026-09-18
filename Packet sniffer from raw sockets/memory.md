# memory.md — Knowledge & Memory Design

`memory.json` (in `runtime/`) is the sniffer's **long-term memory**: everything
the application learns during use and reuses across sessions.

## 1. What lives in memory

| Key | Type | Purpose |
|---|---|---|
| `version` | int | Schema version (bump on breaking changes) |
| `saved_at` | str | ISO timestamp of last write |
| `session_count` | int | Lifetime capture sessions started |
| `total_packets_seen` | int | Lifetime packet counter (never trimmed) |
| `total_bytes_seen` | int | Lifetime byte counter |
| `protocol_history` | obj | Cumulative per-protocol counters: `{TCP: n, UDP: n, ...}` |
| `top_talkers` | list | Top IPs by bytes, `{ip, packets, bytes}` (kept top 10) |
| `known_hosts` | dict | `ip → {"packets", "bytes", "first_seen", "last_seen", "names"[]}` |
| `port_labels` | dict | Learned `port → service name` from observed traffic |
| `recent_filters` | list | Last 15 display-filter expressions used (dedup) |
| `notes` | str | Free-form operator notes persisted across sessions |

## 2. Lifecycle rules

- **Load**: at startup, `memory.json` is read (corrupt file → start fresh, never crash).
- **Update**: in-memory dict is mutated by the UI layer as sessions run.
- **Save**: written atomically (temp file + `os.replace`) when: capture session
  ends, filter applied, or app closes.
- **Trim**: `known_hosts` and `top_talkers` are pruned to the top-10/50 by bytes
  on every save so the file stays small (< ~50 KB) even after weeks of use.
- **Privacy**: no packet payloads are ever stored in memory.json — only counters,
  IPs and ports.

## 3. Memory vs State

| | `memory.json` | `state.json` |
|---|---|---|
| Scope | Lifetime knowledge | Current/resumable session |
| Written | End of session / on demand | Continuously (every ~5 s and on stop) |
| Survives app restarts | ✅ | ✅ (resumed next launch) |
| Example | "host 10.0.0.5 sent 1.2 GB since install" | "last session captured 4 200 TCP pkts, filter was `tcp.port==443`" |

## 4. Example

```json
{
  "version": 1,
  "saved_at": "2026-09-11T10:24:03",
  "session_count": 7,
  "total_packets_seen": 184203,
  "total_bytes_seen": 77126510,
  "protocol_history": {"TCP": 120441, "UDP": 48210, "ICMP": 1180, "OTHER": 14372},
  "top_talkers": [{"ip": "10.0.0.5", "packets": 55211, "bytes": 40123311}],
  "known_hosts": {"10.0.0.5": {"packets": 55211, "bytes": 40123311,
                               "first_seen": "2026-09-01T09:00:11",
                               "last_seen": "2026-09-11T10:20:55",
                               "names": ["workstation-5"]}},
  "port_labels": {"443": "https", "53": "domain"},
  "recent_filters": ["tcp.port == 443", "udp.port == 53"],
  "notes": "Lab segment; 10.0.0.0/24 is trusted."
}
```
