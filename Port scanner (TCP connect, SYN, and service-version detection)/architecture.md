# Architecture — PortScanPro

Colorful TCP port scanner with **TCP Connect**, **SYN half-open** and **service/version** detection, packaged as a single Windows EXE.

```
┌────────────────────────────────────────────────────────────┐
│                    PortScanPro.exe                          │
│  (PyInstaller onefile; python + deps frozen inside)         │
└────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
┌───────────────┐  ┌──────────────┐  ┌────────────────┐
│ CLI /         │  │ Scan engines │  │ Persistence    │
│ interactive   │  │              │  │                │
│ menu          │  │ • connect    │  │ • state.json   │
│ (argparse)    │  │ • syn(scapy) │  │   (sessions)   │
│               │  │ • version    │  │ • memory.json  │
│ colorful ANSI │  │   detect     │  │   (knowledge)  │
└───────────────┘  └──────────────┘  └────────────────┘
```

## Modules

| File | Responsibility |
|---|---|
| `port_scanner.py` | Entry point. Arg parsing, interactive menu, orchestration, colorful rendering, persistence. |
| `build_exe.py` | PyInstaller wrapper → `dist/PortScanPro.exe`. |
| `requirements.txt` | Build/runtime deps (pyinstaller; optional scapy). |

## Scan engines (in `port_scanner.py`)

### 1. TCP Connect (`tcp_connect_scan`)
- Plain `socket.connect()` with per-probe timeout.
- Thread pool (`ThreadPoolExecutor`, default 200 workers), randomized port order to dodge rate-limiters.
- Classifies **open** (connected), **closed** (`ConnectionRefusedError`), **filtered** (timeout / other OSError).
- No privileges required — the default mode.

### 2. SYN half-open (`syn_scan`)
- Builds raw `IP/TCP(flags=S)` packets via **scapy** and fires them with `sr()`.
- `SYN+ACK` → open (followed by a polite `RST` teardown); `RST` → closed; ICMP type-3 codes 1/2/3/9/10/13 → filtered; silence → filtered.
- Requires **Administrator** on Windows + **Npcap** driver. Gracefully degrades with a colored hint when scapy/privileges are missing.
- `--scan both` runs connect + SYN and prints an agreement/diff comparison table.

### 3. Service/version detection (`version_detect` → `detect_service`)
- Per open port: connect → passive banner read → optional typed probes (`HTTP HEAD`, `HELP`, Redis `PING`, newline…).
- TLS detection: port in the TLS set, or first response byte `0x16/0x15`.
- Product/version extraction via ordered regex signature table (`PRODUCT_SIGNATURES`): OpenSSH, vsftpd, Apache, nginx, IIS, MySQL, Redis, …
- If nothing matches, falls back to the well-known port-name table (`SERVICE_NAMES`).

## Target handling
- `expand_targets()` accepts single IP/hostname, CIDR (`192.168.1.0/24`), and dash ranges (`10.0.0.1-5`).
- `parse_ports()` accepts `22,80,443`, ranges `1-1024`, `1-65535`, or the built-in `top100` list.
- Unresolvable hosts are skipped with an error and a non-zero exit code.

## Persistence design
- `state.json` — ring buffer of the last 20 sessions (`ts`, target, per-engine results, services, port list). Overwritten each scan; capped size.
- `memory.json` — long-lived knowledge base keyed by host: every port ever seen open, service/product/version, `times_seen` counter, first/last seen. On new scans, previously-known facts are shown **before** scanning ("memory hint").
- Both files are written to the **current working directory** (override with `PSP_STATE_FILE` / `PSP_MEMORY_FILE`), disabled with `--no-state`.

## Colorful terminal
- `C` palette + `paint()` helper; auto-disabled when piped (`--quiet`/NO_COLOR respected, `FORCE_COLOR` forces).
- On legacy Windows consoles `_enable_ansi_windows()` enables `ENABLE_VIRTUAL_TERMINAL_PROCESSING` + UTF-8 codepage via ctypes.
- Banner, progress line, status tags (`OPEN`/`closed`/`FILTERED`), comparison table and memory hints are all color-coded.

## Build & packaging
- `python build_exe.py` → PyInstaller onefile → `dist/PortScanPro.exe` (python + colorama frozen; scapy optional via `--with-scapy`).
- Onefile build keeps the EXE self-contained; `--onedir` trades size for faster startup.

## Security posture
- Intended for **authorized** testing only; banner shown at completion reminds the user.
- No telemetry, no network calls beyond the scans themselves; all data stays in local JSON files.
