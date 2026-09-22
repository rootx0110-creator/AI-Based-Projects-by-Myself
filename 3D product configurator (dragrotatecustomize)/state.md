# ORBIT — Project State

**Last updated:** 2026-09-20 · **Version:** 1.1.0 · **Status: WORKING — shipped**

## What exists right now
| Artifact | State |
|---|---|
| `3D-Product-Configurator.exe` (project root, ≈26 MB) | ✅ built, selftest PASS, E2E PASS |
| `src/app.html` — 3D configurator UI (4-product catalog) | ✅ complete |
| `src/launch.js` — loopback server + lifecycle | ✅ complete |
| `src/assets/three.min.js` — vendored engine | ✅ r128, offline |
| `launcher/Launcher.cs` — native exe stub | ✅ compiles clean with csc |
| `build.js` — packaging pipeline | ✅ 6-step build, self-verifying |
| `tools/fetch-node.js` — one-time runtime download | ✅ already ran |
| `architecture.md` / `memory.md` / `readme.txt` / `todo.txt` | ✅ written |

## Verification results (latest)
- `--selftest` → **SELFTEST PASS** (stamp parsed, zip extracted, all 4 payload files verified)
- Headless E2E → **6/6 PASS**:
  1. exe starts, prints `Local server: http://127.0.0.1:8642`
  2. `/health` → 200 `{"ok":true,...,"version":"1.1.0"}`
  3. `/` → 200, 48,143 bytes, ORBIT markup present
  4. `/assets/three.min.js` → 200, 603,445 bytes
  5. `/beacon` → 204
  6. taskkill → port freed (clean teardown)
- Server smoke test (dev mode): same endpoints, plus path-traversal guard
  confirmed (plain `../` → 403 `Forbidden`).

## Known limitations (accepted for v1.0)
- First run takes a few seconds (unpack 26 MB zip → `%LOCALAPPDATA%\Orbit3D\app`).
- Heartbeat watchdog only engages when the exe launched node (dev runs via
  `node src/launch.js` skip it; beacon watchdog still active).
- Turn counter uses absolute theta sweep; restarting mid-turn doesn't
  decrement — cosmetic only.
- Engrave text is canvas-rendered (no depth/emboss) — flat overlay on backrest.
- No code-signing certificate: SmartScreen may warn on first run on other PCs
  (unsigned exe). Local use is unaffected.

## Environment snapshot
- Windows 10.0.19045, bash (Git Bash) shell, F: drive project path
  (contains spaces + parentheses).
- Node v24.20.0 (dev), portable Node v20.19.4 (bundled in exe).
- Chrome + Edge installed; csc.exe (.NET 4) present; IExpress present but
  unusable (see memory.md).

## Next session quick-start
```bash
npm run build          # rebuild exe (no network needed)
./3D-Product-Configurator.exe --selftest
node /c/orbit_test/e2e.js "$PWD/3D-Product-Configurator.exe"   # full E2E
./3D-Product-Configurator.exe   # launch for real
```
