# Memory Forensics Notes

Reference material collected while building and testing the analyzer.

## Volatility3 Quick Facts

- Volatility 3 takes an **architecture-agnostic** approach — most plugins no
  longer need a specific Windows profile passed by the analyst.
- Core entry point: `vol.py` (Python 3) — the GUI is a thin orchestrator.
- Primary symbol layer: `windows` (KDBG-driven) and `banners` for detection.

## Common Artifact Locations

| Artifact               | Where to look in a dump                              |
|------------------------|------------------------------------------------------|
| Parent PID / chains    | `pslist` vs `psscan` (unlinked processes)            |
| Hidden DLLs            | `dlllist` vs `ldrmodules` divergence                  |
| Injected code          | `malfind` VAD/PROTECT faults                          |
| Command lines          | `cmdline`, `envars`, `pstree`                         |
| Network evidence       | `netscan` (tcp/udp), `sockscan`, `connections`        |
| Registry persistence   | `printkey` autorun keys, `shellbags`                  |
| Timestamps             | `mftscan`/`mftfind`, `timeliner`                      |

## Indicators of Interest (IoC) checklist

- Unlinked/hidden processes (`psscan` evasions)
- Unsigned or suspicious loaded kernel modules (`modules`, `driverscan`)
- Executable memory marked RWX (`malfind`)
- Unusual network callbacks / reverse shells (`netscan`)
- Short-lived parent-child process towers (`pstree`)
- Disabled user-mode hooks (`apihooks`)

## Analyst Notes (this sandbox case)

- Use hashing (`sha256`) of the raw image on ingestion to prove chain of custody.
- Always correlate plugin findings with the registry hive dump before reporting.
- Keep the generated HTML report next to the raw evidence in the case folder.