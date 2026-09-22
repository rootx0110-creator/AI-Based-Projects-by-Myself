# C2 Detection Lab — Architecture

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
