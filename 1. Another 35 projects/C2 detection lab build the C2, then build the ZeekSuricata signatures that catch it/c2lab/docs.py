"""Embedded lab documentation.

architecture.md, state.md, memory.md and README/RUN_INSTRUCTIONS.md content
lives here so the packaged exe is fully self-contained and can re-export the
docs on demand. Running ``python -m c2lab.docs`` writes the markdown files into
``docs/`` at the repository root (used by the build script).
"""

from __future__ import annotations

from pathlib import Path

from . import __title__, __version__

ARCHITECTURE_MD = f"""# {__title__} — Architecture

> Document version 1.0 · Generated for the C2 Detection Lab project.

## 1. Purpose

The C2 Detection Lab is a closed, loopback-only environment that lets an
analyst:

1. **Build a C2** — stand up a lightweight HTTP command-and-control listener and
   an agent (beacon) that checks in to it, with fingerprints cribbed from
   well-known families (Cobalt Strike, Sliver, Metasploit, SocGholish-style).
2. **Build the detectors** — auto-generate Zeek *signatures* and Suricata *rules*
   that match the exact beacon the lab produces.
3. **Validate the detectors** — capture a live session and run the generated
   rules plus a behavioural beacon-cadence model over it, producing findings.
4. **Report** — export everything as a self-contained HTML report.

Everything runs on **127.0.0.1**. No real network is touched.

## 2. Component Overview

```text
  +--------------------------------------------------------------+
  |                       C2 Detection Lab (GUI)                 |
  |                                                              |
  |  Dashboard  |  Lab Control  |  Signatures  |  Reports  | Docs |
  +------+---------------+--------------+--------------+---------+
         |                    |                 |             |
         v                    v                 v             v
   +-----------+      +--------------+    +----------+  +---------+
   | Profiler  |      |  C2 Server   |    |  Rules   |  |  Docs   |
   | (presets) |----> |  (listener)  |    | renderer |  | (md)    |
   +-----------+      +--------------+    +----------+  +---------+
                              |  ^
                    beacons   |  |  events (queue)
                              v  |
                     +--------------+
                     |  Beacon Client (agent) |
                     +--------------+
                              |
                              v
                     +--------------+      +--------------+
                     |  Detector    |----> |  HTML Report |
                     | (analyzer)   |      |  generator   |
                     +--------------+      +--------------+
```

### 2.1 Module map

| Module                | Responsibility                                             |
|-----------------------|------------------------------------------------------------|
| `c2lab/presets.py`    | C2 profile definitions (UA, methods, URIs, interval, jitter) |
| `c2lab/server.py`     | Loopback HTTP listener, records `BeaconEvent`s               |
| `c2lab/client.py`     | Simulated agent emitting timed beacons                       |
| `c2lab/signatures.py` | Zeek + Suricata artifact generation                          |
| `c2lab/detect.py`     | Session analysis against generated rules                     |
| `c2lab/report.py`     | Self-contained HTML report rendering/export                  |
| `c2lab/app.py`        | Tkinter GUI (standard menu/toolbar/tabs/statusbar)           |
| `c2lab/config.py`     | App + session configuration                                  |
| `c2lab/docs.py`       | Embedded documentation (architecture/state/memory/run)       |

### 2.2 Data flow

1. User selects a **profile** (e.g. *Cobalt Strike Beacon*) and starts the lab.
2. `C2Server` binds `127.0.0.1:<port>` and `BeaconClient` begins emitting
   `GET`/`POST` beacon requests using the profile's User-Agent and URIs, with
   `interval ± jitter` scheduling.
3. Each request is recorded as a `BeaconEvent` (method, path, UA, timestamp,
   RTT, UA hash) and pushed on a thread-safe `queue.Queue`; `app.py` drains the
   queue on a Tk `after()` ticker (GUI threads never touch the widget tree
   directly — see `memory.md`).
4. On **Run Detection**, `analyze_session()` evaluates:
   - the generated **Suricata rules** (UA match + URI usage),
   - the **Zeek signature** equivalents (content-based),
   - a **behavioural model** (cadence CV, UA stability, URI concentration).
5. Findings + full session log + generated rule text feed the **HTML report**.

## 3. Threat model of the simulated "malware"

Each profile is a *lab-legal* stand-in for real HTTP beacons:

| Family               | Typical signature used by the lab                        |
|----------------------|----------------------------------------------------------|
| Cobalt Strike        | Ancient IE User-Agent + low-cardinality URIs, GET        |
| Sliver               | Modern Chrome UA, `/checkin`, mixed GET/POST             |
| Metasploit           | MSIE 6.0 UA, short irregular intervals                   |
| SocGholish-ish       | Firefox UA + JS-lure URIs, high jitter                   |
| Generic HTTP beacon  | Minimal UA + innocuous URIs, low-and-slow interval       |

Because profiles drive both the emitter *and* the rules, the lab is
**internally consistent**: a signature that says "this UA is Cobalt Strike"
truly matches the traffic the lab generates.

## 4. Detection defense-in-depth

Content signatures alone are brittle (off-the-shelf rules are trivially
modified by defenders/attackers alike). The lab therefore bundles three layers:

1. **Layer 1 — Suricata content rules** (instant, wire-speed, per-packet).
2. **Layer 2 — Zeek signatures + script** (protocol-log aware, session state).
3. **Layer 3 — behavioural model** (timing/jitter/US consistency) that mirrors
   what SOCs reason about in a SIEM.

## 5. Threading & lifecycle

```text
Main (Tk) thread          Listener thread [daemon]      BeaconAgent thread [daemon]
   |                            |                             |
   |-- start() ---------------> | binds :port                 |
   |                            | store_event -> Queue        |
   |-- DrainQueue via after()   | <-------- beacons ----------|
   |-- stop() -----------------> | shutdown + server_close     |
```

* `C2Server` is a `ThreadingHTTPServer`; each request is handled on its own
  thread and funneled through the single `BeaconEvent` queue.
* `BeaconClient` sleeps `interval * (1 ± jitter)` between beacons for a
  configured duration, then exits.
* All daemon threads join on app close.

## 6. Packaging (PyInstaller)

```text
main.py
  └── c2lab.app.main()     -> Tk root, Notebook UI
PyInstaller --onefile --windowed --icon assets/c2lab.ico main.py
```

`c2lab/docs.py` is the single source of truth for the markdown docs, so the
exe ships with no external text files; the **File ▸ Export ▸ Documentation**
menu writes them to disk on demand.

## 7. Boundaries & ethics

The lab is deliberately incapable of C2 beyond the loopback interface. It
exists to teach **detection engineering**: build the thing, build the rules
that catch it, measure the catch. Do not point it at real infrastructure.
"""

STATE_MD = f"""# {__title__} — Current State

> Written for lab operators and maintainers. Updated on first release (v{__version__}).

## 1. What is implemented

- [x] Loopback C2 listener (`c2lab/server.py`) — GET/POST, tasking blob response.
- [x] Beacon agent simulator (`c2lab/client.py`) — interval + jitter scheduling,
      RTT measurement, profile-driven fingerprints.
- [x] Five C2 fingerprint profiles (`c2lab/presets.py`).
- [x] Suricata `.rules` generator — UA + URI + method signatures with
      deterministic SIDs (`c2lab/signatures.py`).
- [x] Zeek `signatures` generator + `beacon_detect.zeek` skeleton script.
- [x] Detection analyzer (`c2lab/detect.py`) — signature replay + behavioural
      cadence model (CV, UA stability, URI concentration).
- [x] HTML report renderer (`c2lab/report.py`) — **full** and **summary**
      flavours, self-contained inline CSS, plus JSON event export.
- [x] Tkinter GUI (`c2lab/app.py`) — standard menu bar, toolbar, tabbed
      notebook, live beacon monitor, status bar, docs viewer.
- [x] Embedded documentation with **File ▸ Export ▸ Documentation**.
- [x] One-file `.exe` build script (`build_exe.ps1`) + generated icon.

## 2. Known limitations (lab honesty)

| Limitation                                    | Reason / mitigation                                  |
|-----------------------------------------------|------------------------------------------------------|
| HTTP only, no HTTPS/TLS decoder               | Keep the lab dependency-light; rules document where TLS would require JA3/JA4 tooling. |
| Suricata/Zeek rules are *content* based       | Behavioural layer compensates; rules are teaching artifacts, validate before prod. |
| RTT data approximate                          | Loopback timings are not representative of WAN RTT.   |
| Single listener instance at a time            | One lab at a time keeps state obvious.               |
| Python 3.14 + Tk 9 build                      | Verified locally; PyInstaller one-file.              |

## 3. Test notes

Smoke-tested flows:

- Start lab → beacons flow → live table populates → detection returns
  CRITICAL/HIGH findings → full + summary HTML saved and opened in browser.
- Signature export writes `.rules`, `.sig`, `.zeek` and the docs rebuild from
  `c2lab/docs.py` verbatim.

## 4. What is next (backlog)

- [ ] JA3/JA4 fingerprint presets for TLS beacons inside the generated rules.
- [ ] PCAP capture mode (write the beacon traffic to a pcap file for off-box
      Zeek/Suricata replay).
- [ ] Rule lint pass (suricata -T / zeek -s) surfaced in the UI.
- [ ] MITRE ATT&CK annotation per profile (T1071.001 Application Layer Protocol).
- [ ] Multi-host victim simulation (multiple beacon clients, distinct IPs).
- [ ] IOC export (domains/IPs/UA hashes) alongside the HTML report.

## 5. Status rubric

- **Detector quality** — deterministic and self-consistent inside the lab;
  representative, not production-grade.
- **Operational hygiene** — loopback only; documented; ethical-lab scope.
"""

MEMORY_MD = f"""# {__title__} — Operational Memory

Operational notes for anyone extending or operating the lab. This file records
the decisions, conventions and gotchas that would otherwise be re-learned the
hard way.

## 1. Conventions & ground rules

1. **Loopback only.** The listener binds to `127.0.0.1`; the UI offers no way
   to expose it. Keep it that way on purpose.
2. **Single source of truth for docs.** Text in `c2lab/docs.py` is canonical.
   `python -m c2lab.docs` regenerates `docs/*.md`. Never edit `docs/*.md`
   by hand and expect them to survive a rebuild.
3. **Profiles drive everything.** `presets.py` feeds the agent *and* the rule
   generator. If you change a UA in a profile, the generated signatures change
   with it — that consistency is the lab's core trick.
4. **Deterministic SIDs.** Suricata SIDs derive from CRC32(profile name), so
   rules for a profile keep stable IDs across runs and machines.
5. **UI threads.** Tkinter is not thread-safe. Workers (`C2Server`,
   `BeaconClient`) communicate via `queue.Queue`; `AppPod.poll_queue()` drains
   it from the Tk `after()` ticker. Never call widget methods from a thread.

## 2. Reliable Python that ships

- Python **3.14.7** + Tk **9.0** + PyInstaller **6.22** + Pillow + `requests`.
- The GUI, server, client and docs use only the standard library except
  `requests` (beacon agent) and `Pillow` (runtime icon drawing).
- Build with: `powershell -File build_exe.ps1`.
- Output exe: `dist\\C2DetectionLab.exe` (self-contained, `--onefile`).

## 3. Gotchas observed in this codebase

- `hashlib` / `zlib.crc32` (not the builtin `hash()`) for any repeatable
  fingerprint — `hash()` of strings is randomized per-process.
- `ThreadingHTTPServer` spawns one thread per connection; keep handlers short.
  The drain queue means the GUI never blocks on server I/O.
- On stop, call `httpd.shutdown()` **and** `server_close()`; shutdown alone
  leaks the bound port for the reuse-window.
- Zeek `signatures` files are *optional extras* in a modern Zeek deployment —
  analysts usually prefer scripts. The lab emits both so learners see the
  content-based and behaviour-based approaches side by side.
- Windows PowerShell does not support `&&`; `build_exe.ps1` uses `;` with
  `if ($?)` guards.

## 4. How detection thinking maps to this lab

| Indicator in lab             | Real-world analogue                          |
|------------------------------|----------------------------------------------|
| Stable single UA             | Implant-driven, not organic browser          |
| Low CV inter-beacon interval | Machine scheduler, not human activity        |
| Repeated tiny URI set        | Check-in loop, not content browsing          |
| Tasking response always 200  | C2 tasking fetch, no real resource           |

The lesson lab operators should walk away with: **signature + behaviour** beats
either alone; that is why the report always shows both the rule coverage and
the cadence model.

## 5. Deployment cheat-sheet for the generated rules

**Suricata**

```powershell
Copy-Item outputs\\suricata\\c2_beacons.rules C:\\ProgramData\\suricata\\rules\\
suricata -T -c suricata.yaml          # lint
suricata -S outputs\\suricata\\c2_beacons.rules -i <iface>   # live test
```

**Zeek (signatures + script)**

```text
sigs/ -> c2_beacons.sig  (enable with 'signatures c2_beacons;' in local.zeek)
scripts/ -> beacon_detect.zeek (a teaching skeleton - extend per architecture.md)
```

## 6. Routine maintenance

- `pip install -r requirements.txt` once per machine.
- Re-export docs after any change to `docs.py` strings.
- Rebuild exe after any change: `build_exe.ps1`.
- Keep reports in `outputs/`; they are intentionally not committed.
"""

RUN_INSTRUCTIONS_MD = f"""# {__title__} — Application Run Instructions

> v{__version__}

## 1. Prerequisites

- **Packaged exe:** Windows 10/11 ×64. No Python required.
- **Run from source:** Python 3.14, then:
  ```powershell
  pip install -r requirements.txt
  python main.py
  ```

## 2. Quick start (the 5-minute lab)

1. Launch **C2DetectionLab.exe** (or `python main.py`).
2. **Lab Control** tab → pick a **Profile** (start with *Cobalt Strike Beacon*).
3. Set **Port**, **Interval**, **Jitter**, **Duration** → press **Start Lab**.
   Watch beacons appear in the live table as the agent checks in.
4. Press **Stop Lab** (or let the duration elapse).
5. **Lab Control** tab → **Run Detection** → findings populate the Dashboard.
6. **Reports** tab → **Download HTML (Full)** or **(Summary)** → report opens in
   your default browser and is saved to `outputs/`.

## 3. Workflow that teaches detection

1. Generate a session (step 2 above).
2. Read the **Generated Signatures** tab — Suricata rules, Zeek signatures, and
   the Zeek script `beacon_detect.zeek`.
3. Run Detection and audit the **Findings**: each is tagged with the rule/SID
   that produced it, so you can map *evidence → rule* like a real IR review.
4. Re-run with a different profile (e.g. *Generic HTTP Beacon*, low-and-slow)
   and compare verdicts. Note how a leaner fingerprint produces fewer CRITICAL
   content matches and leans on the behavioural layer.
5. Export the rules (`File ▸ Export ▸ Signatures…`) and try the deployment
   cheat-sheet in `memory.md`.

## 4. User interface reference

| Region      | What it does                                                        |
|-------------|----------------------------------------------------------------------|
| Menu bar    | File (New/Export/Exit), Report, Rules, Help (docs + About)           |
| Toolbar     | Start, Stop, Clear, Run Detection, Generate Report, Open in Browser  |
| Dashboard   | Stat cards: beacons, findings, alerts, verdict                        |
| Lab Control | Profile/config controls + live beacon table                          |
| Signatures  | Generated Suricata / Zeek / Zeek-script text per profile             |
| Reports     | HTML preview + download (Full/Summary), JSON log export              |
| Docs        | architecture.md, state.md, memory.md, run instructions               |
| Status bar  | Server state, beacon counter, last artifact written                  |

## 5. Report download options (HTML)

- **Reports ▸ Download HTML (Full)** — complete report: summary, metrics,
  timing model, all findings, full session log, full rule text, URI usage.
- **Reports ▸ Download HTML (Summary)** — executive summary, findings and rule
  overview — ideal for sharing.
- **Reports ▸ Open in Browser** — render a preview instantly without saving.
- **Reports ▸ Export JSON log** — raw beacon events for analysis elsewhere.

Files are written under `outputs/` by default (next to the exe when packaged).

## 6. File ▸ Export options

| Action                        | Writes                                     |
|-------------------------------|--------------------------------------------|
| Report ▸ HTML (Full)          | `outputs/reports/C2DetectLab_<ts>_full.html` |
| Report ▸ HTML (Summary)       | `outputs/reports/C2DetectLab_<ts>_summary.html` |
| Report ▸ JSON log             | `outputs/reports/C2DetectLab_<ts>.json`      |
| Rules ▸ Signatures…           | folder of `.rules`, `.sig`, `.zeek` files    |
| Help ▸ Export Documentation   | `docs/architecture.md`, `state.md`, `memory.md`, `README.md` |

## 7. Troubleshooting

| Symptom                              | Fix                                              |
|--------------------------------------|---------------------------------------------------|
| "port in use"                        | Pick another port in Lab Control, or quit the app using it. |
| No beacons appear                    | Confirm **Start Lab** began the *server list* in the status bar, then the *beacon agent*. |
| Report looks empty                   | A detection must be run *after* a session with ≥1 event. |
| Rule export folder empty             | Run a session + detection first so rules reflect the active profile. |
| exe blocked by antivirus             | `--onefile` pyinstaller builds are sometimes flagged; add an allow rule (lab tool). |
| Tk/legacy font rendering             | Restart app; the UI uses the platform-default theme (`vista` on Windows). |
"""

DOCS = {
    "architecture.md": ARCHITECTURE_MD,
    "state.md": STATE_MD,
    "memory.md": MEMORY_MD,
    "RUN_INSTRUCTIONS.md": RUN_INSTRUCTIONS_MD,
    "README.md": (
        f"# {__title__}\n\n"
        "Build a C2, then build the Zeek / Suricata signatures that catch it —\n"
        "all inside a loopback-only desktop lab that ships as a single .exe and\n"
        "exports HTML reports.\n\n"
        "## Files\n\n- `docs/architecture.md` — system architecture\n"
        "- `docs/state.md` — current state, limitations, backlog\n"
        "- `docs/memory.md` — operational memory / conventions / gotchas\n"
        "- `docs/RUN_INSTRUCTIONS.md` — how to run the app and the lab exercise\n\n"
        "## Run\n\n- **exe:** `dist\\C2DetectionLab.exe` (no Python needed)\n"
        "- **source:** `pip install -r requirements.txt; python main.py`\n\n"
        "## Rebuild\n\n```powershell\npowershell -File build_exe.ps1\n```\n"
    ),
}


def export_docs(target_dir: Path) -> list[Path]:
    """Write all documentation markdown files to *target_dir* / docs."""
    target = Path(target_dir) / "docs"
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in DOCS.items():
        path = target / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    for p in export_docs(root):
        print(f"wrote {p}")