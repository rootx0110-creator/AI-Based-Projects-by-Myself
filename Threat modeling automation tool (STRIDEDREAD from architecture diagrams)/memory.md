# STRIDEForge — Project Memory (session + ongoing context)

## Purpose
A local, install-free threat modeling automation tool: draw an architecture
diagram, get STRIDE threats + DREAD scores + risk tiers + downloadable HTML
report.

## Key decisions (why things are the way they are)

- **Stack: Flask + vanilla JS + SVG canvas.** No npm build step, no framework,
  tiny dependency footprint, easy to freeze into a single .exe with
  PyInstaller. Python 3.14 + Flask 3.1.3 + PyInstaller 6.22.3 available.
- **Zone-based trust boundaries.** Instead of complex shape-containment
  modeling, each element gets an effective zone (from containing boundary
  rectangle or its own `zone` attribute). Flow crossing zones = boundary
  crossing. Simple, predictable, user-friendly.
- **Residual-risk controls.** Elements carry Boolean flags (`authn`, `authz`,
  `encrypted`, `logged`, `rate_limited`) that lower DREAD scores, so users
  model mitigations already in place and see residual risk. All score deltas
  are surfaced as `context_notes` for auditability.
- **DREAD = 5 factors** (Damage, Reproducibility, Exploitability, Affected
  Users, Discoverability), each 1-10, total 5-50. Risk tiers: Low <18,
  Medium 18-29, High 30-39, Critical 40-50.
- **Two rule layers**: `(kind, type, stride)` specific templates plus
  `(kind, "any", stride)` generic ones; results merge, dedupe by title.
- **Report is fully self-contained HTML** (CSS inlined, infused, escaped) so
  it can be emailed/archived without assets.
- **Exe = run server + open browser on 127.0.0.1:1234.** localhost-only by
  design (security + simplicity).

## Conventions

- No external CDNs required at runtime (Google Fonts link present but the CSS
  font-stack falls back to system fonts offline).
- UI copy uses title-case labels; STRIDE letters always shown with their
  expansion (e.g. "Spoofing").
- Colors: S #f43f5e, T #f59e0b, R #eab308, I #a78bfa, D #38bdf8, E #34d399.
  Risk: Critical #ef4444, High #f97316, Medium #eab308, Low #22c55e.
- Element kind → icon mapping lives only in app.js render functions.
- JSON wire format documented in architecture.md — keep in sync.

## Gotchas / lessons

- PyInstaller: Flask must resolve templates/static via `sys._MEIPASS`;
  `flask --app` style paths break in frozen mode — app uses
  `resource_path()` at Flask construction time.
- Font-awesome not bundled → inline SVGs only.
- Keep analysis payloads JSON-serializable (no datetime/numpy).

## Current status
See state.md. Next big ideas queued in todo.txt.

## File map
- app.py — server + routes + resource path shim
- threat_engine/rules.py — STRIDE/DREAD templates
- threat_engine/analyzer.py — pipeline + scoring + summary
- threat_engine/report.py — HTML report
- templates/index.html — single-page UI shell
- static/js/app.js — canvas, tabs, analysis, report, samples
- static/css/style.css — glass dark theme
- samples/*.json — example models
- build_exe.bat / run.bat — dev convenience