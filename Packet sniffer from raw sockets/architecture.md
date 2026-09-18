# Architecture — Packet Sniffer from Raw Sockets

A Windows-first desktop application (`.exe`) that captures live network packets
using **raw sockets**, decodes them fully offline (no external packet libraries),
and presents them in a colorful, tabbed GUI with HTML report export.

---

## 1. High-Level View

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         PACKET SNIFFER (Raw Sockets)                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐   raw IP packets   ┌────────────────┐   Packet objects   │
│  │ RAW SOCKET   │ ─────────────────► │ CAPTURE ENGINE │ ────────────────┐  │
│  │ (AF_INET /   │   (bytes, thread)  │ (worker thread)│                 │  │
│  │  IPPROTO_IP) │                    └────────────────┘                 │  │
│  └──────────────┘                          ▲                              │  │
│         ▲                                  │ BPF-ish filter               │  │
│         │ SIO_RCVALL                       │                              │  │
│         │                                  │                              │
│  ┌──────┴───────────────────────────────────┴──────────────────────────┐   │
│  │                          NIC / OS NETWORK STACK                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────── queue.Queue ─────────────────────────────┐   │
│  │  bounded FIFO (maxsize=20000) — decouples capture from UI refresh   │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      PRESENTATION LAYER (Tkinter)                   │   │
│  │   ┌─────────┐ ┌─────────────┐ ┌────────────┐ ┌────────┐ ┌────────┐ │   │
│  │   │Capture  │ │ Packet List │ │   Detail   │ │ Stats  │ │ Report │ │   │
│  │   │ Controls│ │ (Treeview)  │ │ (protocols)│ │ (charts)│ │(HTML) │ │   │
│  │   └─────────┘ └─────────────┘ └────────────┘ └────────┘ └────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   SUPPORT:  filters  │  statistics  │  HTML report  │  memory/state  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layered Architecture

| Layer | Module(s) | Responsibility |
|---|---|---|
| **L4 — Presentation** | `gui/app.py` | Tabbed Tkinter UI, theming, event loop (`after()` polling) |
| **L3 — Application services** | `core/filters.py`, `core/stats.py`, `core/report.py` | Filtering, metrics aggregation, HTML report generation |
| **L2 — Domain / decode** | `core/packets.py` | Pure functions: decode Ethernet/IP/TCP/UDP/ICMP into `Packet` dataclass |
| **L1 — Capture / OS** | `core/sniffer.py` | Raw socket creation, promiscuous mode (`SIO_RCVALL`), capture thread |
| **L0 — OS** | Windows Winsock / Unix BPF | Delivers raw IP datagrams to the socket |

Everything in L1–L3 is UI-free and unit-testable; L4 only renders state.

---

## 3. Raw Socket Mechanics (Windows)

1. **Create socket**
   ```python
   s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
   ```
   `SOCK_RAW + IPPROTO_IP` receives whole IP datagrams, headers included.
2. **Bind to the chosen interface**
   ```python
   s.bind((host_ip, 0))          # host_ip = selected adapter's IPv4
   ```
3. **Enable promiscuous mode** — accepts *all* traffic seen by the NIC,
   not just packets addressed to this host:
   ```python
   s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
   ```
4. **Loop**: `data = s.recvfrom(65535)` → parse → push to queue.
5. **On stop**: `RCVALL_OFF`, `close()`.

### Windows vs Linux

| Concern | Windows | Linux |
|---|---|---|
| API | Winsock raw IP + `SIO_RCVALL` | `AF_PACKET` / `SOCK_RAW` |
| L2 header | None on raw IP (frame starts at **IP header**); Ethernet header available via `SOCK_RAW` + `IP_HDRINCL` or Npcap-based capture | Present (14-byte Ethernet header) |
| Privileges | Run as **Administrator** | `sudo` / `CAP_NET_RAW` |
| Output | `sniffer.exe` (right-click → *Run as administrator*) | `sudo python3 main.py` |

The decoder auto-detects whether an Ethernet header is present (checks the
IP version nibble) and handles both layouts.

---

## 4. Data Flow (sequence)

```
NIC           Sniffer(thread)        Queue          UI(main thread)      Disk
 │  recvfrom()   │                     │                  │                 │
 │ ────────────► │  parse bytes        │                  │                 │
 │               │  apply filter ──x──►│ (drop if no      │                 │
 │               │  Packet dataclass   │      match)      │                 │
 │               │ ───────────────────►│  batched pull    │                 │
 │               │                     │ ────────────────►│ Treeview insert │
 │               │                     │                  │ stats update    │
 │               │                     │                  │ ───────────────►│ memory.json / state.json
 │               │                     │                  │ "Save Report"   │
 │               │                     │                  │ ───────────────►│ sniffer_report.html
```

**Threading model** — exactly two threads:

- **Capture thread** (daemon): blocking `recvfrom`; never touches Tk.
- **Main/UI thread**: Tkinter event loop; drains the queue in batches every
  100 ms via `root.after(100, poll)` — Tk is not thread-safe, so all widget
  updates happen here.

Communication is only via `queue.Queue` + `threading.Event` (stop signal);
no shared mutable state.

---

## 5. Module Map

```
packet-sniffer/
├── architecture.md          ← this document
├── memory.md                ← knowledge/memory design
├── state.md                 ← persisted state design
├── README.md
├── requirements.txt         ← (empty: stdlib-only; pyinstaller for build)
├── build_exe.bat            ← builds dist\PacketSniffer.exe
├── main.py                  ← entrypoint (starts engine + UI)
├── core/
│   ├── sniffer.py           ← RawSocketSniffer (L1)
│   ├── packets.py           ← Packet dataclass + decoders (L2)
│   ├── filters.py           ← DisplayFilter, BPF-ish expression parser (L3)
│   ├── stats.py             ← ProtocolStats / timeline aggregation (L3)
│   └── report.py            ← self-contained HTML report writer (L3)
├── gui/
│   └── app.py               ← SnifferApp (L4): tabs, colors, tables, detail
└── runtime/                 ← created at runtime (gitignored artifacts)
    ├── memory.json          ← session knowledge
    ├── state.json           ← persisted app state
    └── sniffer_report.html  ← generated report
```

---

## 6. Core Data Structures

```python
@dataclass
class Packet:
    index: int                 # sequence number in capture
    timestamp: float           # epoch seconds
    src_ip, dst_ip: str
    protocol: str              # TCP / UDP / ICMP / OTHER
    src_port, dst_port: int
    length: int                # total bytes
    flags: str                 # TCP flags e.g. "SA"
    ttl: int
    info: str                  # human summary line
    raw: bytes                 # full frame (for hex dump)
```

- `Packet` is an immutable value object produced by L2.
- `stats.py` keeps counters keyed by `(protocol, conversation)` — O(1) updates.
- `filters.py` compiles expressions like
  `tcp.port == 443 and ip.src == 10.0.0.5` into a predicate once, then applies
  it per packet — no per-row re-parsing.

---

## 7. GUI Design (Tkinter)

- Five color-accented tabs: **🎛 Capture · 📋 Packets · 🔍 Detail · 📊 Stats · 📄 Report**.
- Palette: dark slate background, neon accent per tab (cyan / green / orange /
  violet / pink); zebra-striped rows in the packet table.
- Controls: Start / Stop / Pause, adapter picker, display-filter box, protocol
  quick-filter chips, live counters in the status bar.
- Table: `ttk.Treeview` with columns `#, time, src, dst, proto, len, info`,
  1000-row soft cap, click row → full decode in **Detail** tab + hex dump.
- Stats: animated bars (protocol distribution, top talkers, top conversations).
- Report: one click builds `sniffer_report.html` and opens a save dialog.

---

## 8. Persistence

- `memory.json` — durable *knowledge* (see `memory.md`).
- `state.json` — resumable *state* (see `state.md`).
- Written by the UI layer after mutations (end of session, filter change,
  manual save), never by the capture thread.

## 9. Error Handling & Limits

| Risk | Mitigation |
|---|---|
| No admin rights | Clear banner + graceful "demo (loopback) mode" hint |
| Packet flood | Bounded queue (20 000); oldest dropped, drop-counter shown |
| Malformed packet | Decoders wrapped in try/except → `OTHER` protocol row |
| High UI load | Batched queue drain, 1000-row table cap, O(1) stats |
| Socket error | Engine emits status event, UI shows red status pill |
