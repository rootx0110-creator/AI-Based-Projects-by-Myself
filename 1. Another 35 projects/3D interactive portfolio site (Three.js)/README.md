# Skill Atlas — 3D Interactive Portfolio (Three.js)

A high-quality 3D portfolio that maps **every project folder in the workspace**
into an orbiting galaxy — one glowing node per skill, grouped by discipline on
planetary rings, with Unreal Bloom post-processing, a particle core, and a
self-contained **HTML report download**.

## Run it

The app is pure client-side (WebGL) but loads its own code through ES-modules,
so it must be served over HTTP (not opened via `file://`).

**Easiest — double-click `run.bat`** (starts a local server and opens the browser).

Or manually:

```powershell
python -m http.server 8000
# open http://127.0.0.1:8000
```

Any static server works: `npx serve`, `python -m http.server`, VS Code Live
Server, etc.

## Features

- **50 skills / 9 disciplines** — one 3D node per project in the workspace,
  grouped on colour-coded orbital rings (Network, Detection & Monitoring,
  Offensive Security, Digital Forensics, Incident Response, Defensive Security,
  Tooling & Automation, Adversary Simulation, Data & Reporting).
- **Higher-quality 3D UI** — Three.js r160, ACES tone mapping, UnrealBloom
  post-processing, gradient sky dome, procedural starfield, animated central
  core, hover glow, and a camera fly-to on selection.
- **Explore** — drag to orbit, scroll to zoom, hover nodes for a preview,
  click to open a detail card with the skill's stack.
- **Filter & search** — category chips and a live search box (Ctrl/Cmd+F).
- **HTML report download** — one click generates a standalone, print-ready
  `skill-atlas-report-YYYY-MM-DD.html` covering every skill, its category,
  stack and full description. Each skill card also has its own single-skill
  HTML report download.

## Layout

```
index.html                  — app shell
css/style.css               — dark glass UI theme
js/
  data.js                   — skill inventory (id/name/dir/category/description/tech)
  scene.js                  — Three.js galaxy: rings, nodes, bloom, focus logic
  ui (main.js)              — chips, search, tooltip, modals, boot
  report.js                 — HTML report builders + download
vendor/three/               — local copy of Three.js + addons (works offline)
scripts/sync-skills.mjs     — verifies data.js matches the folders on disk
run.bat                     — one-click launcher
```

## Keeping the atlas in sync

When a project folder is added, edited or removed, run:

```powershell
node scripts/sync-skills.mjs
```

It compares the `dir` fields in `js/data.js` against the folders under
`F:\AI Training\Projects` (including `1. Another 35 projects`) and reports any
drift. Then update `data.js` (name, description, tech, category) for the new
skill.

## Packaging as a desktop exe (optional)

The site is a static Electron-ready bundle. To ship an executable:

```bash
npm init -y
npm i -D electron electron-builder
npx electron-builder --win portable
```

(point the Electron `main` at a tiny script that loads `index.html` over a
local static server, mirroring `run.bat`.)

All skills are lab/defensive/authorized-use tools.