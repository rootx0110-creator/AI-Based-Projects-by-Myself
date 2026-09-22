# C2 Detection Lab — Operational Memory

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
- Output exe: `dist\C2DetectionLab.exe` (self-contained, `--onefile`).

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
Copy-Item outputs\suricata\c2_beacons.rules C:\ProgramData\suricata\rules\
suricata -T -c suricata.yaml          # lint
suricata -S outputs\suricata\c2_beacons.rules -i <iface>   # live test
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
