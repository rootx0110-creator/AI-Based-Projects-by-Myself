# State — Current Status

Last updated: 2026-09-17

## Phase: MVP complete

### Bug fixes shipped 2026-09-17 (version 1.0.1)
- **Live-log loading fixed.** Two root causes:
  1. Time-window XPath emitted a malformed timestamp (`+00:00Z` suffix).
     Now emits clean UTC ISO (`2026-09-16T09:35:19.000Z`).
  2. Query used XML entities `&gt;=` / `&lt;=`; the local wevtutil rejects
     them. Now uses plain `>=`/`<=` (probed and confirmed on this host).
- **Threading hardened.** Worker threads no longer call tkinter `after()`
  directly; they post to a `queue.Queue` drained on the main thread
  (`_poll_msgq`). Prevents `"main thread is not in main loop"` crashes and
  leaves `_busy` reset even on parser/correlator exceptions.
- **Raw Events tab** now lists loaded events immediately (before Analyze),
  not only after correlation.

### Bug fixes shipped 2026-09-17 (version 1.0.2)
- **Console window flash removed.** `wevtutil` (a console app) spawned by the
  GUI created a flickering console window during loads. All subprocess calls
  now pass `CREATE_NO_WINDOW`.
- **Light, user-friendly theme.** App switched from a near-black palette to a
  light theme: white cards, light gray-blue page, friendly blue header,
  readable severity colors. Palette centralized in gui.py constants.

### Verified end-to-end (non-elevated channels)
- GUI live-load of System + Application (24 h) -> 315 events, shown in tab.
- GUI -> Analyze -> dashboard/timeline/alerts population + HTML export.
- Current build launches and stays up.

## Deliverables in dist\
- `IntrusionTimelineTool.exe` — previous build (v1.0.1), locked by two still
  running (elevated) instances at time of writing.
- `IntrusionTimelineTool_v2.exe` — CURRENT build (v1.0.2: light theme,
  no console flash). **RUN THIS ONE.** Once the old instances are closed,
  delete `IntrusionTimelineTool.exe` and rename v2 to the clean name.

### Done
- [x] Project scaffolding (architecture.md, memory.md, state.md, todo.md, readme.txt)
- [x] Parser module: live channels + `.evtx` files via wevtutil, XML -> EventRecord
      (namespace stripping, unnamed Data fallback, time filtering, progress callbacks)
- [x] Rule engine: 28 MITRE ATT&CK rules (excess / sequence / single kinds)
- [x] Correlator: windowed grouping, dedup, kill-chain phases, incident chains, scoring
- [x] HTML report generator: dark single-file report (KPIs, coverage, timeline,
      chains, alert tables, raw events)
- [x] GUI: light friendly theme, dashboard/timeline/alerts/events tabs, threading,
      progress, live-log picker dialog, report export
- [x] Packaging: build.bat + PyInstaller spec, one-file windowed exe
- [x] Built artifact verified: `dist\IntrusionTimelineTool.exe` (12 MB) launches
      and stays up; synthetic intrusion data triggers 11 rules / 3 incident chains;
      System-log live ingest parsed 400 events end-to-end

### In progress / pending
- [ ] Swap fixed build over `IntrusionTimelineTool.exe` (blocked while old
      elevated instances hold the file; close them then rename)
- [ ] Optional Sysmon-driven network rules (Event 3/22) when Sysmon is present
- [ ] Threat-intel enrichment (local heuristics only by design; no network calls)
- [ ] Optional English/German/etc. report locale strings (currently English)

## Metrics (round-trip sanity)
- Live ingest of `Security` default window: works on default Win machines.
- .evtx from copied logs: verified with small generated dumps.
- Correlation latency: < 10 s for ~20k events.

## Known limitations
- Some rules need the auditing subcategories to be enabled (see todo.md).
- wevtutil requires the caller to have read access; system-protected channels
  may return 0 events without elevation.