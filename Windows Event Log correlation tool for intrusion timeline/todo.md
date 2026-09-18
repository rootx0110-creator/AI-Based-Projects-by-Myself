# Todo — Windows Event Log Correlation Tool

Prioritized backlog (P0 = blocking, P1 = important, P2 = polish).

## P0 (must finish)
- [x] Build artifact: run `build.bat` and confirm `dist\IntrusionTimelineTool.exe`
- [x] Smoke-test GUI from the exe on a clean Windows session
- [ ] Verify report export path handling when directory contains no write perms
      -> fall back to user temp folder with a warning

## P1 (next features)
- [ ] Sysmon channel rules (ProcessCreate 1, NetworkConnect 3, DnsQuery 22)
      auto-detected when `Microsoft-Windows-Sysmon/Operational` exists
- [ ] Timeline graph tab (pure-tkcanvas horizontal time axis with phase bands)
- [ ] Whitelist editor (rule id -> comma-separated account/asset exclusions)
- [ ] Automatic `open report` action after export (checkbox in GUI)
- [ ] CSV export of alerts/events as secondary format

## P2 (polish)
- [ ] Localization strings (template file)
- [ ] Icon embedded in the exe
- [ ] High-DPI awareness manifest in .spec
- [ ] Multi-file merge: combine multiple .evtx before correlation
- [ ] Audit-subcategory preflight check (list suggested `auditpol /get /subcategory:*`)

## Housekeeping
- [ ] Add `AGENTS.md` describing validation commands
- [ ] Keep memory.md ADRs in sync with code changes