# arpscan

A cross-platform **ARP scanner / live-host discovery tool**. Given a network,
range, or IP, it discovers which hosts are alive on the local L2 segment and
reports their IP addresses and MAC addresses (plus an optional OUI vendor
lookup).

```
$ arpscan 192.168.1.0/24
IP             MAC address        Vendor
-------------  -----------------  ------
192.168.1.1    a4:2b:b0:93:1c:2d  Dell
192.168.1.101  b8:27:eb:aa:bb:cc  Raspberry Pi Foundation
```

## Features

- **Targets**: CIDR blocks (`192.168.1.0/24`), ranges (`192.168.1.10-50`),
  single IPs, comma/space separated, or `--auto` to detect your own network.
- **Two probe backends**:
  - `scapy` — raw ARP request/reply, the most complete probe (default when
    available).
  - `system` — ping sweep + read the OS ARP table. Zero third-party
    dependencies; works on machines where raw sockets are unavailable.
- **Output**: aligned table, JSON, or CSV (pipe-friendly for scripting).
- **Vendor lookup**: OUI-based MAC vendor identification (small built-in
  database, extensible via `--vendor-db`).

## Install

```bash
# core (works everywhere, uses the system backend)
pip install -e .

# with scapy for the raw-ARP backend
pip install -e ".[scapy]"
```

No install? Run in place: `python -m arpscan --help`.

### Privileges

| Backend | Linux / macOS | Windows |
| ------- | ------------- | ------- |
| `scapy` | `root` (or `CAP_NET_RAW`) | Administrator + [Npcap](https://npcap.com/) installed |
| `system` | none (uses `ping`/`ip`) | none (uses `ping`/`arp`) |

With `--backend auto` (the default), the tool tries scapy first and falls back
to the system backend if scapy is missing or fails.

## Usage

```bash
# Scan a /24
arpscan 192.168.1.0/24

# Scan a small range, JSON output
arpscan 192.168.1.10-192.168.1.50 -f json

# Scan your local network automatically
arpscan --auto

# Use the dependency-free system backend, CSV to a file
arpscan -b system 10.0.0.0/28 -f csv > hosts.csv

# Custom OUI database (lines: "PREFIX VENDOR", '#' comments)
arpscan 192.168.1.0/24 --vendor-db oui.txt

# Verbose (shows backend choice + auto-detected networks)
arpscan --auto -v
```

### Options

| Flag | Meaning |
| ---- | ------- |
| `TARGET ...` | networks/ranges/IPs to scan |
| `--auto` | auto-detect local network(s) and scan them |
| `-b, --backend` | `auto` (default), `scapy`, or `system` |
| `-t, --timeout` | seconds to wait for a reply (default `2.0`) |
| `-r, --retries` | extra probes per target (scapy backend, default `1`) |
| `-f, --format` | `table` (default), `json`, or `csv` |
| `--no-vendor` | skip OUI vendor lookup |
| `--vendor-db FILE` | custom OUI database |
| `-v, --verbose` | progress + backend choice on stderr |
| `--version` | print version |

## How it works

1. Targets are expanded to individual IPv4 addresses (`arpscan/network.py`).
2. The backend probes them:
   - **scapy**: sends one broadcast ARP request per IP in a single `srp()`
     call and waits `timeout` once for all replies.
   - **system**: pings all targets concurrently (warming the OS ARP cache),
     then parses the OS ARP table (`arp -a` / `ip neigh show`) and keeps
     entries that are in the target list.
3. Results are de-duplicated, sorted by IP, optionally enriched with vendor
   names, and rendered (`table` / `json` / `csv`).

See [architecture.md](architecture.md) for the full design.

## Limitations

- **L2 only**: ARP does not cross routers. You can only scan the subnet(s)
  you are directly connected to.
- **System backend** depends on the OS ARP cache (entries expire, ~2 min on
  Windows) and on hosts answering ICMP. Firewalled hosts may be missed.
- The built-in **vendor database is a sample** (~70 OUIs). Install the full
  IEEE OUI list and pass it with `--vendor-db` for complete coverage.

## Standalone executables (Windows)

Build with [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
build_exe.bat
```

Output in `dist/` (single files, no Python install needed):

| File | What it is |
| ---- | ---------- |
| **`arpscan.exe`** | **GUI app — double-click this one.** Opens a window where you enter targets (or tick "scan my network"), pick a backend, and view results in a table. Results can be saved as CSV/JSON. |
| `arpscan-cli.exe` | Console CLI for terminals/scripting (`arpscan-cli.exe 192.168.1.0/24 -f json`). |

Notes:

- The exes **bundle scapy**, so the raw-ARP backend works on machines with
  Npcap + admin rights; everywhere else `--backend auto` falls back to the
  system backend automatically.
- Build entries are `entry_gui.py` / `entry.py` (PyInstaller cannot run
  `arpscan/__main__.py` because of its relative import — see the `.spec`
  files).
- First launch is slower than later ones: onefile exes extract themselves to
  a temporary directory on every run.
- Windows SmartScreen may warn about the unsigned exe; choose
  "More info → Run anyway".

## Development

```bash
python -m unittest discover -s tests     # run tests
```

Project state and durable knowledge live in
[state.md](state.md) and [memory.md](memory.md).

## License

MIT

> **Warning:** only scan networks you own or are authorized to test. ARP
> scanning other people's networks may be illegal in your jurisdiction.