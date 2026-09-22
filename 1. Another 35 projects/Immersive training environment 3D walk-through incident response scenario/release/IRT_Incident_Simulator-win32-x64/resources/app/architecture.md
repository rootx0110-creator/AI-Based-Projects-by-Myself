# Architecture — Immersive Training Environment 3D Walkthrough (Incident Response Scenario)

## 1. Overview

A browser-based, immersive 3D training simulator that walks a trainee through a
realistic facility hit by an active incident (data-center fire). The trainee
must navigate the facility in first-person, investigate hazards, make time
pressured decisions, and complete a structured Incident Response runbook.
At the end, a branded HTML after-action report is generated and can be
downloaded.

The same document tree is loaded by an optional Electron shell so the app can
also be packaged as a desktop EXE.

```
Immersive training environment 3D walk-through incident response scenario/
├── index.html            # Single-page entry point
├── architecture.md       # This file — architecture & design decisions
├── memory.md             # Persistent trainee memory across sessions
├── state.md              # Live simulation state machine spec
├── todo.txt              # Backlog / task tracking
├── readme.txt            # End-user run instructions
├── assets/
│   └── three.min.js      # Vendored three.js (offline, no CDN required)
├── css/
│   └── style.css         # Eye-catching UI styling (HUD, menus, report)
└── js/
    ├── engine.js         # Three.js scene, loop, lighting, minimap overlay
    ├── player.js         # First-person controller, collision, pointer lock
    ├── world.js          # Building layout, rooms, furniture, hazard actors
    ├── scenario.js       # Incident timeline, objectives, scoring engine
    ├── audio.js          # WebAudio SFX (fire, alarm, footsteps, beeps)
    ├── report.js         # HTML after-action report generator + download
    └── main.js           # Bootstrapping, wiring, UI event bindings
```

## 2. Runtime topology

```
┌───────────────────────────────────────────────────────────────┐
│  Browser (Chrome / Edge / Firefox)  or  Electron desktop shell │
│                                                               │
│   main.js ── wires ──┐                                        │
│                        ▼                                      │
│   engine.js ───────► three.js ──► WebGL canvas (3D render)    │
│   player.js         pointer-lock mouse + WASD movement        │
│   world.js          static collision grid + dynamic actors    │
│   scenario.js       timeline/objectives/scoring (single tick) │
│   audio.js          WebAudio procedural SFX, no assets        │
│   report.js         builds data-driven HTML & downloads       │
│                        ▲                                      │
│   memory.js/state.js ◄┘  persisted to localStorage + JSON     │
└───────────────────────────────────────────────────────────────┘
```

All simulation logic runs client-side on a fixed 60 Hz requestAnimationFrame
loop. No server, no network dependency, no external asset CDN after the
initial vendored three.js (kept under `assets/`).

## 3. Module responsibilities

| Module        | Responsibility                                                          |
|---------------|-------------------------------------------------------------------------|
| `engine.js`   | Renderer, camera, scene graph, lights, shadows, ground/ceiling, loop    |
| `player.js`   | Movement, gravity, AABB collision against the world grid, look control  |
| `world.js`    | Floor-plan layout, static colliders, interactive hotspots, fire/smoke   |
| `scenario.js` | Runbook objectives, scoring rules, event timeline, end-of-exp scoring   |
| `audio.js`    | Alarm loop, fire crackle, pickups, decision beeps, footsteps            |
| `report.js`   | Builds a self-contained HTML report with metrics + timeline + badges    |
| `main.js`     | Composition root: binds UI, starts/ends runs, wires modules together    |

## 4. Key design decisions

1. **Web-first, EXE optional.** The core is index.html + assets only; an
   Electron shell (`shell/main.js` + `shell/package.json`) wraps the same
   files for desktop distribution. No server required even for the Electron
   build.
2. **Vendored three.js.** Downloaded once into `assets/three.min.js` so the
   training app runs fully offline (audit/compliance environments often have
   no internet).
3. **Fixed-step simulation.** All game logic advances on a single clock
   (delta-capped), keeping the scenario deterministic and reproducible.
4. **AABB collision.** Movement is validated against a pre-baked collision
   grid generated from the floor plan, so the trainee cannot walk through
   walls. No physics library dependency.
5. **Data-driven scoring.** Every objective, decision and hazard interaction
   produces a structured event record. The report module renders that record
   — scoring rules live in `scenario.js` only.
6. **State + memory separation.** `state.md` describes the transient run
   state machine; `memory.md` describes the persistent trainee ledger
   (personal best, attempts, skill profile) and its JSON schema.

## 5. Score model (summary)

| Pillar | Weight | Measures |
|--------|--------|----------|
| Safety  | 25%    | PPE donned, no injury, fire exit used |
| Speed   | 20%    | Activation time, per-objective time |
| Accuracy| 30%    | Correct decisions, ordered runbook |
| Coverage| 25%    | Alarms raised, E-stop, fuel isolated |

Penalties: injuries, missed steps, debris from wrong suppression, walking into
fire hazards. See `memory.md` for the persisted profile and `report.js` for
rendering rules.

## 6. Security & privacy

- Everything runs locally; **no telemetry, no network calls** from the app at
  runtime.
- Reports are generated in the browser and downloaded by the trainee; nothing
  is uploaded anywhere.
- `localStorage` only stores the trainee's own attempt history / profile.

## 7. Extension points

- Add rooms to the floor plan in `world.js` (the `ROOMS` table) — collision is
  auto-derived.
- Add objectives/decisions in `scenario.js` (data-driven lists).
- Swap environment art by editing `engine.js` materials — no new libraries.