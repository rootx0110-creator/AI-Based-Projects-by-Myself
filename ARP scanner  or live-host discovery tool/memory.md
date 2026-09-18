# arpscan — Memory

Durable knowledge about this project: how it works, conventions, and the
hard-won gotchas. This file is meant to survive between sessions so a future
agent can pick up where the last one left off. Mutable status lives in
[state.md](state.md); design rationale lives in [architecture.md](architecture.md).

## Identity

- **What**: `arpscan` — cross-platform ARP scanner / live-host discovery CLI.
- **Stack**: Python 3.9+ (developed on 3.14), **stdlib only** for the core;
  `scapy` is an *optional* extra (`pip install -e ".[scapy]"`) used by the
  scapy backend. Tests use stdlib `unittest`, not pytest (though pytest is
  listed as a dev extra).
- **Entry points**: `python -m arpscan`, console script `arpscan`
  (`arpscan.cli:main`).

## Quick commands

```bash
python -m arpscan --help                     # CLI help
python -m arpscan --auto                     # scan your own network
python -m arpscan 192.168.1.0/24 -f json     # machine-readable output
python -m unittest discover -s tests         # run all tests (no installs)
```

## Project layout

```
arpscan/
  cli.py            argparse + backend fallback policy
  scanner.py        orchestrator (expand → probe → dedupe/sort/enrich)
  models.py         Host dataclass
  network.py        target expansion (CIDR / range / single)
  localnet.py       --auto detection (ipconfig / ip addr / ifconfig)
  arp_parse.py      pure parsers for OS ARP-table text
  vendor.py         OUI lookup (sample DB + file loader)
  output.py         table / json / csv
  backends/
    base.py         ScannerBackend ABC + BackendError
    scapy_backend.py    raw ARP via scapy
    system_backend.py   ping sweep + OS ARP table
  gui.py            Tkinter front end (background-thread scans, exports)
entry.py / entry_gui.py   PyInstaller entry scripts (repo root)
arpscan.spec / arpscan_cli.spec   PyInstaller specs (GUI / console)
build_exe.bat      builds both exes into dist/
tests/              45 unit tests (unittest)
README.md  architecture.md  memory.md  state.md  pyproject.toml
```

## Conventions

- Python 3.9-compatible syntax (`from __future__ import annotations` at the
  top of type-annotated modules).
- The `Host` dataclass (`models.py`) is the only data model; `to_dict()` is
  the single serialization point.
- MAC addresses are **canonicalized at the parse layer** to lowercase
  `aa:bb:cc:dd:ee:ff` — never pass raw `aa-bb-...` or uppercase forms
  downstream.
- Backends are thin I/O wrappers: they return unsorted, un-deduped
  `List[Host]`. The scanner owns dedupe (first MAC wins per IP), IP-octet
  sorting, and vendor enrichment. **Do not** move that logic into a backend.
- All parsing is pure functions over strings (unit-testable without I/O).
  Subprocess/OS calls stay in `*_backend.py`, `localnet.detect_*`, and the
  CLI.
- Heavy deps are imported lazily (`scapy` inside `ScapyBackend.__init__`), so
  `import arpscan` works everywhere.
- Output goes to `sys.stdout.write`; diagnostics/logs to stderr. Never mix
  progress text into stdout when `-f json/csv` is used.
- Tests must not touch the network. Use `FakeBackend` in
  `tests/test_scanner.py` and `mock.patch` for CLI/subprocess seams.

## Gotchas (learned the hard way)

1. **scapy 2.7 renamed `retries` → `retry`.** Passing `retries=` raises
   `TypeError: SndRcvHandler.__init__() got an unexpected keyword argument`.
   Always use `retry=` (stable across scapy versions).
2. **Never `srp()` per-IP in a loop.** Each call waits the full `timeout`;
   scanning a /24 took ~254× longer than `timeout`. Batch all packets into
   one `srp(packets, ...)` call — one wait total.
3. **Line-anchored regexes need `re.MULTILINE`.** `arp_parse` patterns start
   with `^\s*`; without the MULTILINE flag, only a line at position 0 of the
   text ever matches, silently returning `{}`. This bit us in all three
   parsers at once.
4. **scapy on Windows** needs Administrator + Npcap. Without it, the failure
   happens at *scan time* (not import/construct time), so the CLI's auto
   fallback catches `BackendError` thrown from `scan()` — never assume
   construction success means scapy will work.
5. **scapy may hang or fail for other reasons too** — the scapy backend wraps
   *any* scan-time exception in `BackendError` so `--backend auto` degrades
   gracefully instead of crashing.
6. **Windows `arp -a` includes broadcast (`ff:ff:ff:ff:ff:ff`) and multicast
   (`01:00:5e:...`, `224.x.x.x`) entries.** `arp_parse._keep` filters them;
   add sample lines to `tests/test_arp_parse.py` when changing the filters.
7. **System backend only reports hosts present in the OS ARP cache.** Ping
   warms the cache, but entries expire (~2 min dynamic on Windows) and hosts
   that block ICMP but answer ARP are invisible to this backend. It is a
   fallback, not the most complete probe — that's why scapy is preferred in
   auto mode.
8. **`ping` timeout units differ**: Windows `-w` = milliseconds, Linux `-W` =
   seconds, macOS `-W` = milliseconds. `system_backend._PING_SPECS` encodes
   this; the subprocess `timeout=` must exceed the ping's own wait.
9. **Netmask → prefix**: Windows `ipconfig` gives dotted masks
   (`255.255.255.0`), macOS `ifconfig` gives hex (`0xffffff00`), Linux `ip`
   gives `/24` directly. `localnet` handles all three (`_mask_to_prefix`,
   `_hex_mask_to_prefix`). `int("255.255.255.0")` raises ValueError — a
   classic slip.
10. **`ip neigh show` beats `arp -a` on Linux** (`arp` is deprecated/absent on
    modern distros); `ip neigh` also marks failed entries without `lladdr`,
    which the `linux-ip` parser skips via the `lladdr` requirement.
11. **Python dict literals dedupe keys** — you cannot express duplicate-IP
    results for the scanner's first-wins dedupe test with a dict; the
    `FakeBackend` takes a *list* of `(ip, mac)` tuples.
12. **Test stdout pollution**: CLI tests that call `main()` must
    `mock.patch("sys.stdout")` or result text leaks into real stdout during
    the test run (puzzling "No live hosts found." after the unittest summary).
13. **Target expansion cap**: ranges are capped at 65 536 addresses
    (`network.py`); `10.0.0.1-10.1.255.254` (131 070 addrs) raises
    `ValueError` — that's intended, and the test asserts it.
14. **`--auto` may return multiple networks** (VirtualBox/VMware adapters
    show up: e.g. `192.168.56.0/24` + `192.168.0.0/24`). All are scanned;
    that's by design but can surprise first-time users.
15. **PyInstaller can't run `arpscan/__main__.py`** — its relative import
    (`from .cli import main`) fails when the file is executed as a top-level
    script. The spec uses a tiny `entry.py` at the repo root instead.
16. **Bundling scapy requires `collect_all("scapy")`** in the spec
    (hidden imports + data files); plain analysis misses them. Without it the
    exe silently falls back to the system backend.
17. **Onefile exe extracts to %TEMP% on every launch** — first run is slow;
    SmartScreen warns about the unsigned exe (that's expected, not a bug).
18. **A console exe is a bad double-click deliverable** — with no args it
    prints a usage error and the window closes instantly; users report "the
    exe doesn't run". That's why the primary build is the windowed GUI
    (`arpscan.spec`, `console=False`).
19. **Tk variables are main-thread only.** Reading `StringVar`/`BooleanVar`
    from a worker thread raises `RuntimeError: main thread is not in main
    loop`. Read all Tk vars in the UI thread and pass plain values to the
    scan thread (`arpscan/gui.py` `start_scan` → `_run_scan`).
20. **`Scanner.scan` takes a *sequence* of target strings**, not one string —
    iterating a bare `"192.168.1.1"` walks its characters
    (`Expected 4 octets in '1'`). Wrap single strings in a list.
21. **The GUI spec must NOT exclude `tkinter`** (`arpscan.spec` excludes only
    `matplotlib`; the CLI spec excludes both).

## Dependencies

| Package | Required? | Used for |
| ------- | --------- | -------- |
| (stdlib) | **yes** | everything except the scapy backend |
| `scapy>=2.5` | optional (`[scapy]` extra) | raw ARP probe |
| `pyinstaller` | build-only | `arpscan.spec` / `build_exe.bat` → `dist/arpscan.exe` |
| `pytest` | dev-only | listed in `[project.optional-dependencies] dev`; tests run under unittest |

Runtime subprocesses used by the system backend / `--auto`: `ping`, `arp`,
`ip`, `ipconfig`, `ifconfig` — all OS-provided.

## Related docs

- `architecture.md` — component design, ADRs (D1–D10), extension points.
- `state.md` — current status, last verified results, roadmap, changelog.