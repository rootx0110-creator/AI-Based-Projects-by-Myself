# Memory

Session notes, decisions, and rationale recorded while building the SOC dashboard.

## Decision Log

### 2026-09-17 — v1.2.0: HTML reports + more data sources
- **Report export**: `#btn-report` in the top bar assembles a self-contained dark-theme
  HTML report via `renderer/report.js` (`window.buildHTMLReport(d)`) using a snapshot
  from `collectReportData()` (KPI cards, SIEM severity mix + feed, auth summary + failed-login
  bars, login table, EVTX table, app-log table, netflow protocol mix + top talkers, DNS top
  names, EDR table, vuln table, topology asset inventory, footer disclaimer).
  Saved through native dialog: preload `saveReportHtml` → IPC `save-report-html` → main
  `dialog.showSaveDialog` + `fs.promises.writeFile`. User gets a toast confirmation with the
  saved path, or an error toast. Report carries v1.2.0/banner/tick/UTC timestamp.
- **New simulated sources** (streams 1,2,4/threats blended, all 1 Hz):
  - NETFLOW (`HIST_FLOW`, `traffic`, `talkerBytes`): protocol mix, session + byte counters,
    top-5 talkers by volume, actions allow/monitor/detect.
  - DNS (`HIST_DNS`, `dnsAgg`): A/AAAA/MX/TXT queries, NXDOMAIN rate badge, top domains.
  - EDR (`HIST_EDR`): MITRE ATT&CK technique IDs (T1059.001, T1041…), severity, verdicts.
  - Vulnerability scanner (`HIST_VULN`): CVE x CVSS x port x status.
  - Threat intel (`INTEL`): attacker country + category generated from external-sourced flows.
- New `TRAFFIC` and `EDR` tabs; `#sources-strip` rail (9 pills) with live per-source counters.
- Gotcha: report assembly keys must match `collectReportData()` output exactly
  (e.g. `evtxCounters`, not `evtCounters`) — caught two key-name mismatches during live probing.
- Gotcha: renderer stays sandboxed (no fs); all file I/O goes through the main process IPC.

### 2026-09-17 — v1.1.0: log stream expansion
- Added three new real-time panels behind a tabbed rail (THREATS / EVTX / APP LOGS / LOGINS):
  - **EVTX**: simulated Microsoft-Windows-* events with real Event IDs
    (Security 4624/4625/4688/1102…, System 7036/7045…, PowerShell 4104/4103). ID 1102
    ("audit log cleared") resets the on-screen feed. Chips filter ALL/SECURITY/SYSTEM/PSH.
  - **APP LOGS**: Apache/Nginx/MySQL/BIND/Firewall lines with INFO/WARN/ERROR badges and
    WEB/DB/DNS/FW filters.
  - **LOGINS**: RDP/SSH/Kerberos/NTLM/WinRM/SMB attempts with SUCCESS/FAILURE/LOCKED-OUT,
    user, source IP, destination host; per-tick failed-login bar chart; success/fail/lockout
    badge counters in the header.
- Moved to a tabbed `#tab-stage` panel (individual `#tab-*` containers) so content is
  confined while the 3D stage stays dominant.
- KPI strip widened to 8 cards: added Failed Logins (sparkline) + Auth Success Rate (bar).
- Inspector now also shows per-node login-event counts and can display a clicked log entry
  detail (EVTX entries are click-to-inspect).

### 2026-09-17 — Packaging choice: Electron over PyInstaller
- **Context**: Need a Windows EXE with a rich, live 3D WebGL UI.
- **Decision**: Electron + `electron-builder`.
- **Why**:
  - Three.js WebGL scenes render natively in Chromium; no extra runtime.
  - Node 24 + npm 11 present on the build machine; no Python packaging toolchain
    (PyInstaller absent).
  - `electron-builder` produces a self-contained portable EXE from `dist/`.
- **Alternative**: Python `pywebview` was viable but adds a Python runtime dependency.

### Three.js: bundled local copy
- CDN is convenient but the EXE must work offline.
- `renderer/vendor/three.min.js` is committed/bundled into the app resources.

### Renderer security
- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
- Expose only a minimal `socApp` API via `contextBridge` (app name + versions).
- Renderer never touches Node/fs.

### Data model is simulated
- Purpose-built deterministic simulator keeps the demo "real-time" without external
  dependencies (no network capture, no SIEM). Architecture allows swapping the
  simulator for a live connector later (see `architecture.md`).

## Style & UX Notes

- Deep-space palette (`#0a0e1a` base) for a SOC wall feel; cyan accent for "live"
  signals; amber for warnings; red for critical.
- Glassmorphism panels (frosted translucent) over a subtle animated gradient.
- 3D scene: dark sphere/particle halo backdrop, emissive nodes, animated packet
  pulses along edges so "live traffic" is immediately legible.
- Panels: top bar (title/clock/status) → KPI strip → main 3D stage → side rail
  (threat feed + node inspector).

## Known Gotchas Encountered

- Node 24 / Electron: prefer current stable Electron version.
- **Win EXE build without admin**: `electron-builder`'s `winCodeSign` package contains macOS
  `darwin/` symlinks; extracting it with 7za fails (`Cannot create symbolic link ... A required
  privilege is not held`) unless the shell is elevated or Developer Mode is on.
  - Workaround applied locally in `node_modules/`:
    1. `app-builder.exe` is a shim (C#, compiled with `csc` from .NET Framework 4) that serves a
       pre-extracted `winCodeSign-local` dir (extracted without the `darwin/` tree) for
       `download-artifact --name winCodeSign`, and otherwise forwards raw bytes to
       `app-builder.real.exe`.
    2. `7zip-bin/win/<arch>/7za.exe` is a shim that strips `-snld` and adds `-xr!darwin` so any
       archive extraction skips the un-creatable symlinks; real binary at `7za.real.exe`.
  - The shims forward raw stdout/stderr byte-for-byte — path outputs must NOT gain a trailing
    newline (that earlier caused `ENOENT` on `elevate.exe`).
  - These shims live in `node_modules/`; a fresh `npm install` removes them (rebuild steps must
    re-apply). Portable EXE output: `dist/SOC-3D-Dashboard-1.0.0.exe`.

## TODO / Next Steps (stretch)

- Live data ingestion interface (pcap/Zeek/Suricata JSON).
- Force-directed node drift; expand/collapse subnets.
- Alerts → suspend or color compromised hosts in the 3D graph.
- Tray icon, autostart, dark/light theme toggle.