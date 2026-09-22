VPN TUNNEL BUILDER - WireGuard Automation Script
==================================================

An offline, desktop GUI application that automates the creation and
management of WireGuard VPN tunnels: server profiles, peer devices,
client `.conf` files, QR codes, and self-contained HTML reports.

Scope / intended use
--------------------
- Build server + peer configurations for WireGuard networks.
- Generate native WireGuard keypairs (Curve25519) entirely on-device.
- Produce per-device client configuration files you can import into the
  official WireGuard apps (mobile / desktop).
- Emit branded, self-contained HTML reports for sharing and record keeping.
- Import the exported server `.conf` into `wg-quick` (Linux) or the
  WireGuard Windows GUI to bring the tunnel up.

Legal / lab note
----------------
For authorized, lab, and training use only. You are responsible for the
machines you run WireGuard on and for keeping generated private keys safe.

Features
--------
- Modern dark UI with sidebar navigation (Dashboard, Tunnel Builder,
  Peers & Devices, Deploy, Reports & Logs, Settings).
- One-click key generation (X25519 via RFC 7748, matches `wg genkey`).
- Automatic subnet address assignment for peers.
- Per-peer client config preview with live QR code image and copy-to-clipboard.
- Bulk export of server `wg0.conf` + each client `*.conf`.
- HTML report generator (dashboard summary, topology data, full configs,
  embedded QR codes) with Save/Download dialog, self-contained file.
- JSON state persistence. WireGuard CLI detection (wg / wireguard tools)
  with graceful fallback instructions.

Quick start
-----------
1. Press "Generate keypair" on the Tunnel page or accept the auto-generated
   server key on first launch.
2. Set listen port, subnet/CIDR, endpoint host, DNS, MTU, server address.
3. Add peers under "Peers & Devices" - each gets keys + a client config + QR.
4. "Deploy" -> Export all -> pick a folder. You receive:
     wg0.conf                     (server)
     client-<name>.conf           (one per peer)
5. "Reports & Logs" -> Download HTML report for an offline shareable document.

Installing the tunnel
---------------------
On the server (e.g. Linux):
    sudo apt install wireguard
    sudo wg-quick up /path/to/wg0.conf

On the peer device:
    import client-<name>.conf into the official WireGuard app (iOS/Android/
    Windows/macOS) or paste the config after scanning its QR in the app.

This tool only fabricates and exports configuration - bringing interfaces up
still uses the real WireGuard daemon via wg-quick / the desktop apps.

Building the .exe
-----------------
    pip install -r requirements.txt
    .\build.ps1
The produced binary is placed in dist\ and named "VPN Tunnel Builder.exe".
Run it directly - it stores its state in the app's local data folder.

Project files
-------------
  main.py                      - entry point
  wgbuilder\                   - application package
    core\                      - engine (keys, configs, store, report)
    ui\                        - interface (theme, widgets, views)
  architecture.md              - system design document
  state.md                     - current runtime state & invariants
  memory.md                    - decisions log / lessons learned
  todo.txt                     - backlog
  readme.txt                   - this file
  build.ps1                    - PyInstaller build script