# HIDS Agent — State

## Current status

**Working, v1.1.0.** The agent runs a FIM + process-monitoring loop in the
background (each module on its own interval) and a `customtkinter` desktop UI
renders live state and alerts. Report download (HTML / JSON / TXT / CSV) is
included. Core-engine tests and a full UI smoke test pass. A release EXE is
produced by PyInstaller in `dist/HIDS_Agent.exe`.

### Implemented

- [x] Config persistence (`config.json`; settings apply live — engines share the
      same dict as the agent, so hash/interval/threshold changes need no restart)
- [x] FIM: streaming hashes (sha256/sha1/md5, configurable), skip oversize files
- [x] FIM: baseline build + differential scan → added / modified / removed
- [x] FIM: per-directory manifests in SQLite; add / remove watched dirs from GUI
- [x] FIM: multi-select directories run sequentially in one background job
- [x] Process snapshot via psutil (pid, name, user, cpu, mem, exe, started);
      snapshot throttled to every 4 s when the tab is visible
- [x] Auto-learned process whitelist (deferrable via setting); one-shot
      new-process alerts with cross-cycle dedup
- [x] Resource-hog alerts (CPU %, mem MB) with per-PID de-duplication, excluding
      System Idle Process / kernel-side noise
- [x] Alert log with severity (Info/Warning/Critical), source, ack, working
      filters (severity + source), clear, **CSV export**
- [x] Reports tab: full report + filtered event log, downloadable as
      HTML / JSON / TXT / CSV, with "open last download"
- [x] Dashboard cards + severity open-count chips + live progress + recent
      alerts + quick actions (incl. Pause/Resume)
- [x] Live clock + versioned sidebar in the status bar
- [x] Settings screen (toggles, intervals, thresholds, hash algo) → live reload
- [x] Dark themed desktop UI, single-file EXE, windowed, with icon
- [x] `--headless` agent mode for the same process monitor without a GUI
- [x] Docs: `architecture.md`, `state.md`, `memory.md`

## Verified by automated checks

- FIM build/scan diffing: added, modified, removed, unchanged classification — PASS
- Process snapshot + whitelist + new-process detection — PASS
- End-to-end agent loop raises alerts for file add / modify / remove — PASS
- Per-module intervals honored; manual-event busy-spin guard — PASS
- Settings mutate engines in place without restart (`hash_algorithm=md5` takes
  effect immediately) — PASS
- Report builders (HTML / JSON / TXT / CSV) return valid output — PASS
- Alert severity + source filters apply — PASS
- GUI constructs, all six views render, tick loop runs — PASS

## Known limitations

1. **Polling, not real-time** — FIM detects change only on the next scan cycle
   (default 300 s). No filesystem events/watchdog yet; latent for low intervals.
2. **Resource-hog CPU%** uses single-call `psutil.cpu_percent`, which is relative
   to clock time, not cores; a value can be misleading on multi-core hosts.
3. **Auto-whitelist means every running process is "known"** — new-process alerts
   only surface processes that appear between cycles. When auto-learn is off the
   whitelist is static until the user rebuilds it from the Processes screen.
4. **No privilege elevation** — the agent sees only the current user's processes
   and files it can read; system/other-user processes are omitted (`AccessDenied`).
5. **No log shipping / SIEM / notifications** (SMTP, webhook, Windows toast) yet —
   alerts live only in the local SQLite log (reports can be saved anywhere).
6. Baseline hashing of very large directories is O(size); the UI shows progress
   and stays responsive because hashing runs off the main thread.
7. GUI + agent share one process; a crash in the UI takes the agent with it.

## Roadmap (next)

- Real-time FIM via `ReadDirectoryChangesW` (or watchdog) to close the latency gap
- Correlation/mini-SIEM: alert deduplication, severity escalation, sign-offs
- Process chain / parent-pid detection (attack-tree style, living-off-the-land)
- Notifications: Windows toast + optional SMTP/webhook
- Optional "elevated helper" service for system-wide visibility
- Export/import of baselines; JSON/CSV alert export (done for CSV; schedule-based
  automatic reports), DB retention policy
- App auto-update channel (replace EXE safely) and signed build