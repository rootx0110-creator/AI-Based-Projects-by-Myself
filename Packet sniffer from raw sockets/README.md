# Packet Sniffer — Raw Sockets 📡

A colorful, tabbed **desktop packet sniffer** that captures live traffic with
**raw sockets** (no third-party packet libraries), decodes IPv4/TCP/UDP/ICMP,
shows live statistics, and exports a **downloadable HTML report**.
Ships with `architecture.md`, `memory.md` and `state.md` design docs.

## ✨ Features

- Raw-socket capture: `AF_INET / SOCK_RAW / IPPROTO_IP` + `SIO_RCVALL`
  (promiscuous) on Windows; `AF_PACKET` on Linux.
- Decoders for **IPv4 → TCP / UDP / ICMP** with flags, ports, TTL, service names.
- Wireshark-like display filter: `tcp.port == 443 and ip.src == 10.0.0.5`.
- 5 color-accented tabs: 🎛 Capture · 📋 Packets · 🔍 Detail · 📊 Stats · 📄 Report.
- Per-protocol colored rows, click a row for full decode + **hex dump**.
- Live stats: protocol mix, top talkers, top conversations, packets/sec.
- **HTML report export** — self-contained file (inline CSS) you can download,
  share, print or save as PDF.
- Persistent `runtime/memory.json` (lifetime knowledge) and
  `runtime/state.json` (resumable session state).

## 📦 Project layout

```
packet-sniffer/
├── architecture.md      ← layered design + diagrams
├── memory.md            ← knowledge persistence design
├── state.md             ← state machine + state.json design
├── main.py              ← entrypoint
├── core/                ← sniffer · packets · filters · stats · report
├── gui/app.py           ← colorful tabbed UI (Tkinter)
└── runtime/             ← memory.json · state.json · reports (created at runtime)
```

## 🚀 Run

**Windows (admin required for raw sockets):**

1. Open *Terminal (Admin)* in the project folder.
2. `python main.py`
3. Pick your **active** interface (adapter names are shown, e.g.
   `192.168.1.20  —  Wi-Fi`) → **▶ Start** → packets appear in the Packets tab.

Notes:

- The built `.exe` **auto-elevates** (UAC prompt) on launch; the header shows
  an `admin ✓` / `⚠ not admin` badge either way.
- **Not sure which IP is your Wi-Fi?** Pick **`0.0.0.0 — ALL IPv4
  interfaces`** at the top of the Interface list: the app binds one raw
  socket per local IPv4 and captures on **every adapter at once**. Adapter
  names are taken straight from Windows (`ipconfig`), so each IP is labelled
  with its real adapter — the app never guesses what an IP range "means".
- **No packets on a quiet adapter?** On Start the app sends a marked UDP
  **self-test probe** to the bound address(es) that must show up within ~2 s,
  so you can tell "working but quiet" from "not capturing". A live hint also
  appears if a bound adapter sees no traffic for 5 s.
- Promiscuous mode (`SIO_RCVALL`) failures are reported loudly instead of
  being silently ignored, and a capture thread killed by firewall/AV
  (WinError 10013) flips the status pill to **● ERROR** with the reason in
  the Report tab's *Recent errors* view.

**Linux:** `sudo python3 main.py` (uses AF_PACKET; no admin banner).

## 🏗 Build the .exe

```bat
build_exe.bat
```

Produces `dist\PacketSniffer.exe`. The exe asks for administrator rights via
UAC on launch (required for raw sockets). It is one-folder (`--onedir`),
starts fast, and does not need Python installed.

> Changed the code? Re-run `build_exe.bat` — a previously built exe contains
> the old snapshot and will not pick up fixes until rebuilt.

## 🧪 Smoke test (no admin needed)

```bash
python tests/smoke_test.py
```

Parses synthetic Ethernet/IP/TCP/UDP/ICMP frames, runs the filter engine,
exercises the full GUI, and writes a sample HTML report to verify rendering.

## 📄 Report

The Report tab generates `sniffer_report_YYYYmmdd_HHMMSS.html` containing:

- KPI header (packets, bytes, pps, protocols, endpoints)
- Session summary + filter used
- Protocol distribution / top talkers / top conversations with gradient bars
- First 500 packets table with protocol badges
- Focus packet deep-dive with hex dump
- memory/state appendix

Everything is inline (no CDN), so the file works offline and can be emailed,
printed, or archived.

## ⚠️ Ethics & legality

Only capture networks you own or are authorized to monitor. Capturing other
people's traffic may be illegal in your jurisdiction.
