# Architecture

Real-time SOC (Security Operations Center) dashboard with 3D network topology visualization.

## Overview

The application is a desktop executable built with Electron. It renders a live security
operations dashboard in a Chromium-based renderer process, featuring a real-time 3D network
topology visualization (WebGL via Three.js) alongside live SOC metrics, threat feeds, and
alerting panels.

## Tech Stack

| Layer        | Technology                              | Purpose                                        |
|--------------|-----------------------------------------|------------------------------------------------|
| Shell        | Electron (Node.js)                      | Native desktop EXE, process & window lifecycle |
| Main process | Node.js (Electron `main.js`)            | Window creation, IPC / telemetry sink           |
| Preload      | `preload.js` (contextBridge)            | Secure bridge between renderer and main        |
| Renderer     | HTML5 / CSS3 / Vanilla JS               | Dashboard UI and data binding                  |
| 3D engine    | Three.js (WebGL)                        | 3D network topology scene                      |
| Data         | Deterministic simulator in renderer     | Real-time metrics, traffic, threat stream      |

## Process Model

```
+---------------------------------------------------------------+
|  Main Process (Node.js)                                       |
|  - Creates BrowserWindow                                      |
|  - Owns app lifecycle                                          |
|  - Exposes secure API via contextBridge (preload)             |
+-------------------------------|-------------------------------+
                                | IPC (contextIsolation on)
+-------------------------------v-------------------------------+
|  Renderer Process (Chromium)                                  |
|  - HTML/CSS/JS UI                                             |
|  - Three.js 3D topology scene (WebGL)                         |
|  - SOC simulator: metrics, alerts, network packets            |
|  - Chart panels (Canvas 2D sparklines)                        |
+---------------------------------------------------------------+
```

## Components

### 1. Main Process (`main.js`)
- Creates the application `BrowserWindow` (frameless, dark theme, taskbar-icon).
- Loads the renderer bundle from `renderer/index.html`.
- Security: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.

### 2. Preload Bridge (`preload.js`)
- Exposes `appInfo` (versions) to the renderer through `contextBridge`.
- No Node.js APIs are leaked to the page beyond the curated surface.

### 3. Renderer (`renderer/`)
- `index.html` — semantic layout: header, KPI grid, 3D canvas, side panels.
- `styles.css` — deep-space dark theme, glassmorphism panels, glow accents.
- `app.js` — main controller: simulator, Three.js scene, UI bindings.
- `vendor/three.min.js` — Three.js r128 build (offline, bundled).

### 4. SOC Simulator (in `app.js`)
Deterministic + seeded-random data sources on a fixed tick (e.g. 1000 ms):

- **Monitors**: CPU, memory, disk, packet-rate, detection-load.
- **KPI counters**: events/sec, active threats, blocked attempts, response time.
- **Threat feed**: streaming alerts with severity (info/low/medium/high/critical).
- **Network topology**: nodes (hosts/gateways/services) connected by links;
  packets animate along links; node color/status reacts to threat activity.

## Data Flow

```
                    +-------------------------------+
   Clock tick  ---->|  SOC Simulator                |
                    |  - compute metrics            |
                    |  - emit alerts                |
                    |  - move packets on links      |
                    +--------+-------------+--------+
                             |             |
                      metrics/alerts    topo state
                             |             |
                    +--------v-------------v--------+
                    |  UI Renderers                  |
                    |  - KPI counters / sparklines   |
                    |  - alert feed                   |
                    |  - 3D scene (Three.js)          |
                    +--------------------------------+
```

## Security Notes
- `contextIsolation` + `sandbox` enabled; renderer cannot reach Node.
- No remote code is loaded at runtime.
- Three.js is bundled locally; the app works fully offline.

## Build & Distribution
- Dependencies installed via `npm install`.
- Windows EXE produced with `electron-builder` (portable/nsis target).
- Output written to `dist/`.