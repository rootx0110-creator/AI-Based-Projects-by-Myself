# arpscan — Architecture

This document describes how the ARP scanner / live-host discovery tool is
structured and why. It is written for future maintainers (human or AI) to
understand the system quickly without re-reading every file.

## 1. Overview and goals

`arpscan` is a CLI tool that discovers live hosts on a local network segment
and reports IP + MAC (+ vendor). Design goals, in priority order:

1. **Work out of the box** on Windows, Linux, and macOS — including on
   machines without admin privileges or raw-packet access.
2. **Zero required third-party dependencies** for the core (stdlib only);
   scapy is an optional extra that improves probe completeness.
3. **Testable without a live network** — all parsing and orchestration logic
   is pure and unit-tested.
4. **Scripting-friendly** — JSON/CSV output for piping into other tools.

## 2. High-level layout

```
cli.py            argparse entry point; backend fallback policy
gui.py            Tkinter front end (double-click app; shares Scanner)
scanner.py        orchestrator: expand targets -> run backend -> normalize
models.py         Host dataclass (the only data model)
network.py        target-string expansion (CIDR / range / single)
localnet.py       --auto: detect local networks from ipconfig/ip/ifconfig
arp_parse.py      pure parsers for OS ARP-table text
vendor.py         OUI vendor lookup (built-in sample DB + file loader)
output.py         table / json / csv formatters
backends/
  base.py         ScannerBackend ABC + BackendError
  scapy_backend.py   raw ARP probe via scapy (optional dep)
  system_backend.py  ping sweep + OS ARP table (no deps)
entry.py / entry_gui.py   PyInstaller entry scripts (repo root)
arpscan.spec / arpscan_cli.spec   PyInstaller specs (GUI / console)
tests/            45 unit tests (unittest, no network access)
```

### Data flow

```
CLI args
   │  (--auto uses localnet.detect_local_networks)
   ▼
scanner.Scanner.scan(targets)
   │  network.expand_targets ──► list of IPv4 strings
   ▼
backend.scan(targets, timeout, retries)     ← the only I/O boundary
   │  (scapy: ARP request/reply;  system: ping + parse ARP table)
   ▼
List[Host]  →  de-dupe by IP  →  sort by IP  →  vendor enrich  →  render
```

## 3. Components

### `gui.py` (the double-click app)
- Tkinter window: target entry (or "scan my network" checkbox), backend
  dropdown, timeout/retries, vendor toggle, results Treeview, CSV/JSON
  export buttons, status bar.
- **Threading rule**: scans run on a background thread; results are marshaled
  to the UI thread via a `queue.Queue` polled by `after(100, ...)`. All Tk
  variables are read in the UI thread (`start_scan`) and passed to the
  worker as plain values — reading a Tk var from a thread raises
  `RuntimeError: main thread is not in main loop`.
- Shares the exact same `Scanner`/backend/formatter logic as the CLI; it is
  the PyInstaller windowed entry (`entry_gui.py` → `arpscan.spec`).

### `cli.py`
- Parses args; requires at least one `TARGET` or `--auto`.
- **Backend fallback policy** (important): with `--backend auto` it tries
  scapy first, and on `BackendError` at scan time retries with the system
  backend. An explicitly requested backend (`-b scapy`) fails loudly instead.
- Writes results with `sys.stdout.write` (never `print` into the output
  stream, so `-f json` stays clean on stdout; progress goes to stderr).

### `scanner.py`
The orchestrator owns everything testable without a network:
- target expansion via `network.expand_targets`,
- `_normalize`: de-duplicate by IP (first MAC seen wins) and sort by IP
  octets (so `192.168.1.10` sorts after `192.168.1.2`),
- `_enrich_vendors`: OUI lookup per host (skipped with `--no-vendor`).
- `select_backend(name)`: `auto` tries `ScapyBackend()` and falls back to
  `SystemBackend()` only if scapy is *unimportable*. Runtime permission
  failures are handled by the CLI (see above), because construction can't
  detect them.

### Backends (`backends/`)
A backend is a thin probe: it receives a list of IP strings and returns
`List[Host]` for the ones that answered. It must not sort, de-duplicate, or
enrich — that is the scanner's job.

- **`ScapyBackend`** — the complete probe. Sends one broadcast ARP request
  per target **in a single `srp()` call** so the wait is `timeout` once, not
  `timeout` per IP (a /24 would otherwise take ~254× longer). Uses scapy's
  `retry=` kwarg. Imports scapy lazily so the package imports without it;
  any failure at scan time is wrapped in `BackendError` so the auto path can
  fall back.
- **`SystemBackend`** — zero-dependency fallback. Pings all targets
  concurrently (`ThreadPoolExecutor`, 64 workers) to warm the OS ARP cache,
  then reads the ARP table (`arp -a` on Windows/macOS, `ip neigh show` on
  Linux) and keeps entries whose IP is in the target list. Only reports hosts
  that appear in the OS ARP table.

### Pure parsing modules (the unit-testable core)
- `network.py`: `expand_target(spec)` handles CIDR, `a-b` and `a.b.c.d-e`
  ranges, singles; caps ranges at 65 536 addresses to prevent footguns.
- `arp_parse.py`: line-anchored regex parsers for three OS output families
  (`windows`, `linux-ip`, `posix-arp`), canonical MAC normalization
  (`aa:bb:cc:dd:ee:ff`), and filtering of broadcast/zeros/multicast entries.
- `localnet.py`: parses `ipconfig` (Windows), `ip -o -4 addr show` (Linux),
  and `ifconfig` (macOS/Linux fallback) into `(ip, prefixlen)` pairs;
  converts dotted/hex netmasks to prefix lengths.
- `vendor.py`: `OUI_DB` sample (~70 well-known OUIs), `load_vendor_db(path)`
  for a full IEEE-style list, and `lookup_vendor(mac, db)`.
- `output.py`: three formatters keyed by name; table width computation is
  column-based with a `IP | MAC address | Vendor` header.

### `models.py`
`Host` is a frozen dataclass: `ip: str`, `mac: str` (canonical form),
`vendor: Optional[str]`. `to_dict()` is the single serialization point used
by both JSON and CSV.

## 4. Key design decisions

| # | Decision | Rationale |
| - | -------- | --------- |
| D1 | Backend abstraction (`ScannerBackend` ABC) | Lets users trade probe completeness vs. privileges; both strategies share orchestration. |
| D2 | scapy is an *optional* extra, not required | Keeps install and CI dependency-free; the system backend covers the common case. |
| D3 | System backend = ping sweep + OS ARP table | Requires no privileges anywhere; reuses the OS's own ARP resolution. |
| D4 | Pure functions for all parsing | All 45 tests run with no network and no mocks of I/O (except one `_run` patch). |
| D5 | Lazy scapy import | `import arpscan` must never fail on a machine without scapy. |
| D6 | Scanner owns dedupe/sort/enrich | Keeps backends thin and makes ordering/duplicate behavior deterministic and testable. |
| D7 | Batched `srp()` (one wait for all targets) | Sequential per-IP waits scale as O(hosts × timeout); batching makes /24 scans take `timeout` seconds. |
| D8 | `retry=` not `retries=` to scapy | scapy 2.7 renamed the kwarg; `retry` is stable across supported versions. |
| D9 | Range cap at 65 536 | Prevents a typo like `10.0.0.1-10.255.255.254` from scanning 16M addresses. |
| D10 | Output via `sys.stdout.write`, diagnostics via stderr | Keeps `-f json` machine-readable when piped. |
| D11 | GUI + CLI share one core (`Scanner`) | The windowed exe and the console exe are just two front ends over the same tested logic. |

## 5. Platform notes

- **ARP is link-local only**: the tool can only discover hosts on subnets the
  machine is directly connected to. Scanning a routed network silently finds
  nothing (or only the router).
- **Windows**: scapy needs Administrator + Npcap; without it, `srp` raises at
  runtime (wrapped in `BackendError`). `arp -a` lists broadcast and multicast
  entries (filtered by `arp_parse._keep`). `ping -w` timeout is in
  **milliseconds**.
- **Linux**: `ip neigh show` is preferred over `arp -a` (which is deprecated
  and may be absent); `ping -W` timeout is in **seconds**. Raw sockets need
  root or `CAP_NET_RAW`.
- **macOS**: `ip` may not exist, so `--auto` uses `ifconfig`; `arp -a`
  format matches the POSIX parser.
- MAC normalization (dash → colon, lowercase) is applied at the parse layer
  so every module downstream can rely on canonical form.

## 6. Testing strategy

`tests/` uses stdlib `unittest` (runnable with
`python -m unittest discover -s tests`, no installs, no network):

- parsers (`network`, `arp_parse`, `localnet`, `vendor`) — sample text in
  tests, including the broadcast/multicast entries that must be filtered;
- output formatters — round-trip via `json`/`csv` modules;
- `Scanner` — a `FakeBackend` double returns canned `(ip, mac)` pairs,
  covering expansion, dedupe (first-wins), IP sort, and vendor enrichment;
- CLI — mocked `select_backend`/`detect_local_networks`, `sys.stdout`
  captured with `mock.patch`; the auto→system fallback is tested with a
  backend that raises `BackendError`.

Real-network behavior is verified manually (see `state.md` for the latest
results), never in CI.

## 7. Extension points

- **New probe strategy**: subclass `ScannerBackend`, implement `scan`, register
  in `backends/__init__.py` and the `-b` choices in `cli.py`.
- **Full vendor coverage**: download the IEEE OUI list and pass
  `--vendor-db`; or grow `vendor.OUI_DB`/`load_vendor_db`.
- **New output format**: add a formatter to `output.FORMATTERS`.
- **New target syntax**: extend `network.expand_target` (keep the 65 536 cap).
- **IPv6**: out of scope today — ARP is IPv4-only; ND (Neighbor Discovery)
  would need a parallel `ScannerBackend` implementation.