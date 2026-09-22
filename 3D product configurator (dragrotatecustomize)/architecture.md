# ORBIT — 3D Product Configurator · Architecture

A single-file Windows `.exe` that runs a local 3D product configurator
(drag / rotate / zoom / customize) and exports an HTML configuration report.

```
┌────────────────────────────────────────────────────────────────────┐
│  3D-Product-Configurator.exe (≈26 MB)                              │
│                                                                    │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐ │
│  │ C# launcher (native)     │  │ appended payload (zip)         │ │
│  │ - self-extract on 1st run│  │  node/node.exe   (portable)    │ │
│  │ - checksum verify        │  │  src/launch.js   (server)      │ │
│  │ - spawn node + heartbeat │  │  src/app.html    (UI)          │ │
│  │ - exit on window close   │  │  src/assets/three.min.js       │ │
│  └──────────────────────────┘  └────────────────────────────────┘ │
│  last 32 bytes: "ORBIT1:<10-digit size>|<10-digit checksum>"       │
└────────────────────────────────────────────────────────────────────┘
                                   │ first run
                                   ▼
        %LOCALAPPDATA%\Orbit3D\app\  (extracted, stamped payload.stamp)
                                   │
                                   ▼
        node src/launch.js  ──►  http://127.0.0.1:8642  (loopback only)
                                   │
                                   ▼
        Chrome/Edge --app window (chromeless, isolated profile)
```

## Components

### 1. `launcher/Launcher.cs` → native stub (compiled with .NET `csc`)
- **Self-extraction** — finds the appended zip via the 32-byte trailer
  (`ORBIT1:size|checksum`), verifies a byte-sum checksum, unzips to
  `%LOCALAPPDATA%\Orbit3D\app` with PowerShell `Expand-Archive`.
  Skipped when `payload.stamp` matches the embedded stamp.
- **Lifecycle** — spawns `node\node.exe src\launch.js` with
  `ORBIT_HEARTBEAT=<tempfile>`; touches the heartbeat every ~400 ms.
  Watches for the app window (`FindWindow`) and exits when it closes;
  also kills node if it dies first. Killing the exe tears down node.
- **Self-test** — `3D-Product-Configurator.exe --selftest` verifies the
  embedded payload headlessly (used by the build).

### 2. `src/launch.js` → local app server (Node)
- Serves `src/` on `127.0.0.1:8642–8652` (first free port), loopback only.
- `GET /health` → JSON heartbeat for tests. `POST /beacon` → page-alive ping.
- Path-traversal guard on every file request.
- Opens Chrome/Edge in `--app` mode with an isolated profile in `%TEMP%`.
- Watchdogs: exits if the heartbeat goes stale (exe killed) or the page
  stops beaconing (window closed).

### 3. `src/app.html` → the configurator (three.js r128, bundled offline)
- **Product** — a catalog of four parametric reference products (lounge
  chair, floor lamp, coffee table, bookshelf) built from primitives, each
  grouped into selectable parts (chair: frame/legs/seat/backrest/armrests;
  lamp: base/stem/shade; table: top/legs/undershelf; shelf: frame/boards/back).
- **Multi-product** — product chips swap the model; each product has its own
  parts, options, finish presets, camera framing and stored configuration
  (localStorage keyed per product, with v1.0 flat-config migration).
- **Controls** — custom orbit implementation: left-drag rotate (with
  inertia), wheel zoom, right-drag/shift-drag pan, auto-rotate, fullscreen,
  reset view.
- **Customization** — 12 finishes per part (wood/painted/metallic PBR-ish
  material presets), per-product options (chair: cushion/armrests/metal legs,
  lamp: dimmer/warm bulb, table: drawer/glass top, shelf: extra shelf/glass
  doors), canvas-texture engraving on every product, per-product color
  presets + randomizer.
- **State** — config persisted to `localStorage`; restored on relaunch.
- **Exports** —
  - **HTML report download** (the requested "report in HTML format"):
    a styled, self-contained quotation document with finish tables,
    options, pricing, interaction stats and a report ID.
  - PNG snapshot of the canvas, JSON config copy to clipboard.
- **Pricing** — per-product base price ($149 / $89 / $199 / $129) + options;
  live-updating HUD.

## Build pipeline (`build.js`)

```
tools/fetch-node.js  →  dist/node/node.exe        (one-time download)
                        src/assets/three.min.js   (bundled, offline-capable)
        │
build.js
  1. assemble dist/payload/ (node + src files)
  2. PowerShell Compress-Archive → dist/payload.zip
  3. csc /optimize+ launcher/Launcher.cs → dist/stage.exe
  4. stitch: stage.exe + payload.zip + 32-byte trailer → final exe
  5. run `final.exe --selftest` (must print SELFTEST PASS)
```

`npm run build` reproduces the exe deterministically; no internet needed
after the one-time `node tools/fetch-node.js`.

## Why this shape

| Decision | Reason |
|---|---|
| C# launcher + appended payload | IExpress silently rejected valid SED files on this machine; csc is built into Windows and gives full control over extraction, checksums and lifecycle. |
| Local server + browser `--app` window | WebGL + file downloads (report/snapshot) work with zero GUI toolkit code; window looks native/chromeless. |
| Heartbeat + beacon watchdogs | No orphaned node.exe processes: closing the window, killing the exe, or navigating away all shut the stack down. |
| Loopback-only server | Nothing is exposed to the network. |
| Bundled three.js | App runs fully offline. |

## Ports & data
- Ports: TCP 127.0.0.1 `8642–8652` (first free).
- Writes: `%LOCALAPPDATA%\Orbit3D\app` (extracted app), `%TEMP%\orbit-hb-*`
  (heartbeat, deleted at exit), browser profile `%TEMP%\orbit-app-profile`.
- Config data lives in the browser profile's localStorage.
