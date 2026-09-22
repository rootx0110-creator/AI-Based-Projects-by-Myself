# ORBIT — Project Memory

> Long-lived context for anyone (human or AI) resuming work on this project.
> Companion files: `architecture.md` (design), `state.md` (current status),
> `readme.txt` (user doc), `todo.txt` (open items).

## What this project is
A single-file Windows `.exe` (≈26 MB) containing a **3D product configurator**
with a **4-product reference catalog** (lounge chair, floor lamp, coffee table,
bookshelf), drag/rotate/zoom camera control, per-product/per-part customization
(12 finishes × product parts, per-product options), live pricing, and a
**downloadable HTML report** of the configuration.

## Key facts (don't re-learn these the hard way)
- **Build chain:** `tools/fetch-node.js` (one-time) → `npm run build`
  (`build.js`) → `3D-Product-Configurator.exe` in project root.
- **Packaging:** C# launcher compiled with .NET Framework `csc.exe`
  (`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`), payload zip
  appended after the exe bytes, 32-byte trailer `ORBIT1:<size>|<crc>`.
- **IExpress was abandoned.** It exits 1 or does nothing on every SED
  variant tried (LF/CRLF, %-vars vs direct, \ vs / paths, minimal 1-file
  payloads, space-free staging dirs). Root cause never identified; ~10
  variants failed. Do not revisit without a working reference SED.
- **The tool shell strips one level of backslashes even inside quoted
  heredocs.** Write temp scripts avoiding literal `\` (use
  `String.fromCharCode(92)`, `/` paths, or the write_file tool).
- **This machine:** Node v24.20.0 + npm 11.19.0, Python 3.14, Chrome at
  `C:\Program Files\Google\Chrome\Application\chrome.exe`, Edge present,
  no gcc. Project path contains spaces + parentheses (breaks some tools).
- **Port range:** 127.0.0.1:8642–8652 (first free wins). Loopback only.
- **three.js r128** is vendored at `src/assets/three.min.js` — the app is
  fully offline (WebGL, custom orbit controls, no external CDN at runtime).
- **Testing:**
  - `3D-Product-Configurator.exe --selftest` → `SELFTEST PASS` (headless
    payload verification).
  - `/c/orbit_test/e2e.js <exe>` → 6-check E2E (start exe headless with
    `ORBIT_DONT_OPEN=1`, poll `/health`, fetch app + three.js, `/beacon`,
    kill, confirm port freed). Last run: **E2E PASS**.
  - `node src/launch.js` with `ORBIT_DONT_OPEN=1` for server-only testing.

## Gotchas baked into the code
- `src/launch.js` `ROOT = __dirname` (it lives *inside* `src/`; pointing it
  at `src/src` was a real bug once).
- The page must ping `/beacon` every 1 s (`app.html` does this) or the
  server self-terminates after 6 s — don't remove that beacon.
- `ORBIT_HEARTBEAT` staleness is detected by *mtime not changing*; the
  launcher touches it every ~400 ms. Heartbeat file is per-run temp.
- Chrome launches with `--user-data-dir=%TEMP%\orbit-app-profile` so the
  app window has its own process tree (clean exit on window close).
- Config persistence uses the browser profile's localStorage — wiping
  `%TEMP%\orbit-app-profile` resets user customizations.
- Engrave plate per product (all rendered flat, canvas-texture): chair on
  backrest at z=-.335, y≈1.10 with rotation x=-.10 to match backrest tilt;
  lamp on stem y≈1.28; table on apron y≈.41; shelf on top rail y≈1.475.
- Config shape is `{product, products:{id:{finish:{...}, ...options}}}` in
  localStorage `orbit.cfg`; v1.0 flat `{finish, cushion, ...}` configs are
  migrated into the chair entry on load.

## Dead code / cleanups pending
- `tools/fetch-node.js` is required once but not wired into `build.js`
  (deliberate: build must not hit the network). Could auto-invoke later.
- `C:\orbit_test\` holds diagnostic debris (SED variants, e2e runner).
  The e2e runner is worth keeping; the SED experiments are not.
