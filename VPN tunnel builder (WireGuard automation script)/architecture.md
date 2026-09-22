# Architecture

## 1. Purpose

The **VPN Tunnel Builder** is a desktop GUI application that automates the
creation and management of WireGuard tunnel configurations:

- generate Curve25519 (X25519) keypairs that are byte-compatible with
  `wg genkey` / `wg pubkey`,
- assemble server and per-peer client `.conf` files,
- produce QR codes for import into the official WireGuard mobile apps,
- export all artifacts to a folder,
- emit self-contained HTML reports with full documentation of the tunnel.

It does **not** contain a WireGuard kernel module or userspace TUN driver; it
is a configuration factory / orchestrator. Bringing interfaces up is delegated
to `wg-quick` (Linux) or the official WireGuard clients, using the exported
files.

## 2. High-level flow

```
User (GUI)
   |
   v
+--------------------------------------------------------------+
|                      wgbuilder package                       |
|  ui/ (views, theme, widgets)  <--> core/ (engine, store)     |
+--------------------------------------------------------------+
   |                                   |
   | calls                             | calls
   v                                   v
core/keys.py   core/configs.py   core/report.py   core/store.py
   |                 |                |               |
   v                 v                v               v
x25519.scalar  subnet math       HTML generator    JSON persistence
(RFC 7748)     + .conf builder   (+ embedded QR)   (app data)
```

Every action is recorded into an in-memory event log that is included in the
generated HTML report, giving the report "state & history" transparency.

## 3. Module breakdown

### 3.1 core/x25519.py
Pure-Python Curve25519 scalar-base multiplication following RFC 7748
(byte-swapped reference implementation). Exposes:

- `scalarbase(k)` -> u-coordinate bytes (public key for a raw 32-byte scalar)
- `clamp(k)` -> WireGuard-style clamping (bit 255 clear, bit 254 set, bits 0-2 clear)
- validated against the RFC 7748 official test vector on import (self-test).

### 3.2 core/keys.py
- `wg_base64(32_bytes)` / `wg_decode(text)` - 32-byte <-> unpadded-standard
  44-char base64 as used by `wg`.
- `generate_keypair()` -> (private_b64, public_b64); public derived by
  `x25519.scalarbase(private_bytes)`.
- `derive_public(private_b64)` -> public_b64 (equivalent of `wg pubkey`).
- `is_valid_keybase(text)` sanity check on paste.

### 3.3 core/configs.py
- subnet math helpers: network/mask, host enumeration, next free address,
  broadcast, first/last usable host, `Address = a.b.c.d/n`.
- `build_server_config(server, peers)` -> INI-style text for the WireGuard
  server (`[Interface]` + one `[Peer]` per device).
- `build_client_config(server, peer)` -> text for a device with its own key,
  the server public key, Endpoint, DNS, AllowedIPs, MTU, PersistentKeepalive.
- `parse_config(text)` lightweight parser (round-trip check used in tests).

### 3.4 core/qr.py
Wrapper around the `qrcode` + `pillow` libraries:

- `qr_png_bytes(text)` -> PNG in memory (used in report embedding),
- `qr_image(text)` -> PIL Image (used by the GUI preview).
- Config text is embedded as-is, so the mobile app reads it natively.

### 3.5 core/store.py
- `State` dataclass: server settings, peers list, export history, settings.
- `Store.load()/save()` to a JSON file under `%LOCALAPPDATA%\VPNTunnelBuilder`
  (path overridable in Settings). Deterministic JSON, atomic writes via temp
  file + `os.replace`.

### 3.6 core/report.py
`ReportBuilder` produces a single-file, self-contained HTML document:

- embedded CSS (dark theme) and inline base64 QR PNGs (no external assets),
- sections: summary, server detail, peer inventory, full server config,
  per-peer client configs with QR, event log, export history,
- `build_report_lead()` factory used both by the Reports view and the
  Dashboard quick action; the file is written via a native Save As dialog
  (report download -> HTML).

### 3.7 ui/
- `theme.py` - central color tokens + `ttk.Style` configuration (dark palette,
  flat cards, accent color). Enforces a consistent "high level design".
- `widgets.py` - reusable controls: `Card`, `StatCard`, `Section` headers,
  `AccentButton`, `Note`, toast notifications, page container.
- `views/*` - one class per screen, all mounted into a single `App` window:
  - `dashboard.py`  - KPI cards + quick actions,
  - `builder.py`    - server parameters + keypair generation,
  - `peers.py`      - peer inventory, add/edit/delete, config + QR preview,
  - `deploy.py`     - export everything, foldered commit, wg CLI detection,
  - `reports.py`    - report configuration + download HTML,
  - `settings.py`   - defaults, paths, CLI path override.

## 4. Design decisions

| Decision | Rationale |
| --- | --- |
| Pure-Python X25519 | Zero runtime deps for key material; matches wg exactly; test-vector verified. |
| JSON state in LocalAppData | Survives app updates; %LOCALAPPDATA% writable by standard users; avoids admin-only paths. |
| Self-contained HTML report | Portable/shareable; works offline; only one file to e-mail or archive. |
| Base64-in-HTML QR | Makes the report valid everywhere with no broken relative links. |
| tkinter/ttk + custom theme | Ships with CPython, PyInstaller-friendly, rich enough for a polished dark UI. |
| CLI detection, not hard dependency | wg may be absent on Windows; the app degrades to instructions instead of failing. |

## 5. Security posture

- Private keys are only ever stored in the local JSON state file (user scope)
  and inside exported client confs on the user's chosen folder.
- Reports include private client configs (needed for onboarding) - the app
  prints a notice; treat report files like key material.
- No network calls are made by the application at all (air-gap friendly).

## 6. Build & packaging

- Source tree is PyInstaller-friendly: `main.py` imports `wgbuilder.app.main`.
- `build.ps1` runs:
  `pyinstaller --noconfirm --onefile --windowed --name "VPN Tunnel Builder"
   --collect-data qrcode main.py`
- Output: `dist\VPN Tunnel Builder.exe`.
- `pillow` and `qrcode` are bundled; tkinter ships with CPython.

## 7. Testing strategy

- `core/x25519.py` asserts against the RFC 7748 vector on import.
- Key equivalence checked against the RFC vector constant; config builder
  "round-trip" test parses generated configs back and compares fields.
- GUI is exercised manually per view; engine tests are script-based
  (`python -m wgbuilder.core.selfcheck`).

## 8. Repo layout

```
VPN tunnel builder (WireGuard automation script)/
  main.py
  wgbuilder/
    __init__.py  app.py
    core/  x25519.py keys.py configs.py qr.py store.py report.py selfcheck.py
    ui/    theme.py widgets.py views/{dashboard,builder,peers,deploy,reports,settings}.py
  architecture.md  state.md  memory.md  todo.txt  readme.txt  requirements.txt
  build.ps1
```