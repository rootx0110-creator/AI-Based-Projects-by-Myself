# arpscan — State

Mutable status of the project. **Update this file whenever you change
behavior or verify something.** Durable knowledge: [memory.md](memory.md);
design: [architecture.md](architecture.md).

## Component status

| Component | Status | Notes |
| --------- | ------ | ----- |
| `network.py` target expansion | ✅ implemented, tested | CIDR, ranges (`a-b`, `a.b.c.d-e`), singles, dedupe, 65 536 cap |
| `arp_parse.py` parsers | ✅ implemented, tested | windows / linux-ip / posix-arp families; broadcast/multicast filtering |
| `localnet.py` `--auto` detection | ✅ implemented, tested | ipconfig, `ip -o -4 addr show`, ifconfig |
| `vendor.py` OUI lookup | ✅ implemented, tested | sample DB (~70 OUIs) + `--vendor-db` file loader |
| `output.py` formatters | ✅ implemented, tested | table / json / csv |
| `scanner.py` orchestrator | ✅ implemented, tested | dedupe, IP sort, vendor enrich, backend selection |
| `backends/scapy_backend.py` | ✅ implemented, tested-live | batched `srp()`, `retry=` kwarg, lazy import |
| `backends/system_backend.py` | ✅ implemented, tested-live | ping sweep (64 workers) + OS ARP table |
| `cli.py` | ✅ implemented, tested | auto→system fallback on `BackendError` |
| Docs (README/architecture/memory/state) | ✅ written | |
| `pyproject.toml` packaging | ✅ written | console script `arpscan`, extras `[scapy]`, `[dev]` |
| Exe build (GUI: `arpscan.spec`, `entry_gui.py`; CLI: `arpscan_cli.spec`, `entry.py`; `build_exe.bat`) | ✅ implemented, verified | `dist/arpscan.exe` (20 MB GUI), `dist/arpscan-cli.exe` (17 MB console), scapy bundled |
| GUI (`arpscan/gui.py`) | ✅ implemented, smoke-tested | Tkinter window: targets, backend, timeout/retries, results table, CSV/JSON export; background-thread scans |

**Test suite: 45 tests, all passing** (`python -m unittest discover -s tests`).

## Last verified behavior

Verified live on 2026-09-10 (this machine: Windows, Python 3.14.7, scapy
2.7.0, Npcap available):

- `python -m arpscan --version` → `arpscan 0.1.0`
- `python -m arpscan --auto -v -t 1`
  - auto-detected `192.168.56.0/24` and `192.168.0.0/24` (VirtualBox +
    real NIC)
  - backend: **scapy** (auto prefers it when importable and runnable)
  - found: `192.168.0.1` (`f0:b4:d2:3f:cb:be`), `192.168.0.101`
    (`dc:f5:05:fc:0a:71`); completed in ~2 s for 508 target IPs
- `python -m arpscan -b scapy -t 1 192.168.0.1` → gateway found, ~1 s
- `python -m arpscan -b system -t 1 -f json 192.168.0.1 192.168.0.101`
  → found only `192.168.0.1` (system backend is less complete; the other host
  did not answer ping or had expired from the ARP cache — expected)
- Vendor column was empty for both live hosts (`f0:b4:d2`, `dc:f5:05` are
  not in the sample OUI DB) — expected with the bundled sample.

Exe build (PyInstaller 6.22.2, Python 3.14):

- `python -m PyInstaller arpscan.spec --noconfirm --clean` →
  `dist/arpscan.exe` (20 MB, onefile, **windowed GUI app**).
- `python -m PyInstaller arpscan_cli.spec --noconfirm` →
  `dist/arpscan-cli.exe` (17 MB, console).
- GUI exe launch test: started in background, still alive after 8 s (~37 MB
  RAM), killed cleanly — window opens and stays open.
- `dist/arpscan-cli.exe -b system -t 1 -f json 192.168.0.1` → gateway found.
- Earlier console build (`dist/arpscan.exe` v1) was rejected by the user:
  double-clicking a console app with no args flashes a usage error and the
  window closes instantly. **The GUI build fixes this.**

GUI logic (headless smoke test, not part of the unit suite):

- Scan runs on a background thread; results arrive via a queue polled by
  `after()` and populate the Treeview; status bar shows backend + count.
- Two bugs found and fixed during bring-up: (1) reading a Tk `StringVar`
  from the worker thread raises `RuntimeError: main thread is not in main
  loop` — all Tk vars are read in `start_scan` and passed as plain values;
  (2) passing the targets string directly to `Scanner.scan` iterated it
  character-by-character (`Expected 4 octets in '1'`) — wrap in a list.

## Known limitations / open issues

1. **Sample vendor DB** only (~70 OUIs). Full coverage requires a user-supplied
   IEEE OUI file via `--vendor-db`.
2. **System backend misses ICMP-blocked / cache-expired hosts** by design.
3. **IPv6 / Neighbor Discovery** not supported (ARP is IPv4-only).
4. **`--auto` scans every detected network**, including virtual adapters
   (VirtualBox/VMware). No NIC filtering option yet.
5. No timeout protection if the OS `ping` binary hangs (subprocess timeout is
   `ping_timeout + 5`, which should suffice).
6. scapy sends one broadcast ARP request per IP (254 frames for a /24);
   `arp-scan`-style optimization (rate limiting, retry scheduling) is not
   implemented.

## Roadmap (next steps, unprioritized)

- [ ] `--interface` / `--nic` flag to restrict `--auto` to one adapter
- [ ] Full IEEE OUI database download helper (e.g. `arpscan --fetch-oui`)
- [ ] IPv6 ND probe as a new backend
- [ ] MAC-change / duplicate-MAC detection in output
- [ ] Rate limiting + retry scheduling for the scapy backend on big subnets
- [ ] Docker/CI test matrix (Linux + macOS) for the system backend parsers
- [ ] `pip install` packaging test (`pip install -e .` + console script)

## Changelog

- **2026-09-10** — Rebuilt the exe as a **GUI app** (`arpscan/gui.py`, Tkinter):
  double-clicking `dist/arpscan.exe` now opens a window with scan controls
  and a results table instead of a console that flashed and closed. Added
  `entry_gui.py`, reworked `arpscan.spec` (windowed), added
  `arpscan_cli.spec` (console variant), updated `build_exe.bat`. Both exes
  built and launch-verified.
- **2026-09-10** — Added standalone Windows exe build:
  `arpscan.spec` (onefile, bundles scapy via `collect_all`), `entry.py`
  (PyInstaller-safe entry), `build_exe.bat`. Built and verified
  `dist/arpscan.exe` (17 MB) with both backends and `--auto`.
- **2026-09-10** — Initial implementation:
  - Full package (`arpscan/`), 45 unit tests, live verification on Windows.
  - Fixed during bring-up: `re.MULTILINE` on ARP parsers (silent `{}`),
    scapy `retry=` kwarg (2.7 rename), batched `srp()` (per-IP waits made
    /24 scans ~254× slower), dotted/hex netmask → prefix conversion,
    auto-fallback widened to any scapy runtime failure.
  - Docs: README, architecture.md (ADRs D1–D10), memory.md (gotchas 1–14),
    state.md.