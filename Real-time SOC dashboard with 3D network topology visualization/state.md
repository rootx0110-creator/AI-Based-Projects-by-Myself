# State

This document tracks the current, authoritative state of the application: what exists,
its version, build status, and the operational contract between processes.

## Version

| Field            | Value |
|------------------|-------|
| App name         | SOC 3D Dashboard |
| Version          | 1.2.0 |
| Engine           | Electron |
| Renderer         | HTML5 + Three.js r128 |
| Platform target  | Windows (win32) |
| Distribution     | `dist/` (portable EXE) |

## Runtime State (in-memory, per session)

State is intentionally volatile; each launch re-seeds the simulator so the demo is
always live. No persistence layer is required.

| Store          | Owner       | Contents                                     | Mutated by          |
|----------------|-------------|----------------------------------------------|---------------------|
| `sim`          | renderer    | metrics history, event counters, tick clock  | simulator tick      |
| `topo`         | renderer    | nodes, links, packet positions, severity mapping | simulator + user   |
| `alerts`       | renderer    | latest alert feed entries                    | simulator           |
| `scene`        | renderer    | Three.js scene, camera, meshes, labels       | 3D renderer         |
| `evtxBuf`      | renderer    | Windows Event Log stream (security/system/PowerShell) | simulator     |
| `appBuf`       | renderer    | application/service log stream (web/db/dns/fw) | simulator          |
| `loginBuf`      | renderer    | authentication attempt stream + windowed stats | simulator         |
| `flowBuf`       | renderer    | netflow sessions, protocol mix, top talkers    | simulator         |
| `dnsBuf`        | renderer    | DNS queries, NXDOMAIN rate, top domains        | simulator         |
| `edrBuf`        | renderer    | endpoint detections (MITRE), verdicts          | simulator         |
| `vulnBuf`       | renderer    | CVE/CVSS scanner findings                      | simulator         |
| `intelBuf`      | renderer    | attacker geo / category indicators             | simulator         |
| reportData      | renderer    | snapshot assembled for HTML export             | report builder     |
| windowBounds   | main        | window position/size                         | Electron            |

## Simulator Contract

- Tick interval: `1000 ms` (configurable in code).
- Metrics series kept to a rolling window of ~60 samples.
- Alert stream: entry shape `{ ts, host, type, severity, msg, detail }`.
- Severity levels: `info, low, medium, high, critical`.
- Network graph: generated with N nodes (default ~19) and M links; packets traverse
  links at constant speed; nodes marked `compromised` pulse red.
- EVTX stream (`HIST_EVTX`): Windows-style events — Security (4624/4625/4634/4672/4688/4697/4720/4722/4725/4732), System (7036/7045/1074/6005), PowerShell (4104/4103), plus audit-cleared 1102 (purging the EVTX view). Filterable ALL/SECURITY/SYSTEM/PSH.
- Application stream (`HIST_APP`): Apache/Nginx/MySQL/BIND/Firewall with INFO/WARN/ERROR levels. Filterable ALL/WEB/DB/DNS/FW.
- Login stream (`HIST_LOGIN`): authentication attempts (RDP/SSH/Kerberos/NTLM/WinRM/SMB), outcomes SUCCESS/FAILURE/LOCKED-OUT, windowed failed-login bar chart, header badge counters, `badlogon` + `authRate` KPIs.
- NetFlow stream (`HIST_FLOW` + `traffic`): protocol mix aggregation, byte/session counters, live top-talkers by volume.
- DNS stream (`HIST_DNS` + `dnsAgg`): query types A/AAAA/TXT/MX, NOERROR vs NXDOMAIN rate, top queried names.
- EDR stream (`HIST_EDR`): endpoint detections with MITRE ATT&CK technique IDs, verdicts (blocked/quarantined/cleaned/isolated).
- Vulnerability stream (`HIST_VULN`): scanner findings with CVE/CVSS/port/package and NEW/REOPENED/VERIFIED status.
- Threat intel (`INTEL`): attacker geolocation per indicator with category (SCAN/C2/BOTNET/EXFIL/BRUTE).
- Data-source rail: `#sources-strip` shows 9 live source pills (SIEM/EVTX/APPS/AUTH/NETFLOW/DNS/EDR/VULN/INTEL) with per-source counters.
- Report export: `#btn-report` builds a self-contained dark-theme HTML report (KPI cards, severity mix, login chart, EVTX/app/traffic/DNS/EDR/vuln/topology tables) and saves via a native dialog (IPC `save-report-html`).

## Inter-Process Contract

- Renderer reads `window.socApp.appName` and `window.socApp.versions` via the preload
  bridge (`contextBridge`).
- Main ↔ renderer does not use Node APIs; all visualization is self-contained.

## Known Current Limitations

- Simulated data only; does not attach to live network interfaces (planned: pcap / SIEM feed).
- Node position static after generation (planned: force-directed layout drift).
- Single window; no system tray (planned).

## Build Status

- [x] Project scaffolding + docs
- [x] Electron main/preload
- [x] Renderer UI + Three.js topology scene
- [x] Packaging to EXE (electron-builder)

## Log / Change History

| Date       | Change                                        |
|------------|-----------------------------------------------|
| 2026-09-17 | Initial scaffold, simulator, UI, packaging    |
| 2026-09-17 | v1.1.0 — EVTX, app logs, login-attempt panels, filters, nav tabs, new KPIs |
| 2026-09-17 | v1.2.0 — HTML report export, netflow/DNS/EDR/vuln/intel data sources, sources rail |