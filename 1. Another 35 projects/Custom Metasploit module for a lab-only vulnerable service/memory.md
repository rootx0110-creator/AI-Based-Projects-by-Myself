# memory.md — learned context & session notes

Plain-text scratchpad for anything future sessions should remember about this
project.

## Session 2026-09-19 (v2.0 — "smarter, more advanced")

- **Upgrade shipped.** Backend now a multi-vulnerability catalog
  (`VULN_TEMPLATES`: cmd-injection Exploit, path-traversal + config-leak
  auxiliary/scanner), auto-detection (`detect_all`), a stdlib TCP port scan,
  a JSON report twin, an activity timeline, a context-aware smart advisor and
  persistent profile (`%LOCALAPPDATA%\MSFLabStudio\profile.json`).
- Lab service extended: `/file` (traversal + flag) and `/backup` (unauth
  config dump with `db_password`) alongside `/exec`.
- New probes verified live: all three checks detect against a real lab
  process; `detect_all` reports `["cmd-injection","path-traversal",
  "config-leak"]`.
- Source selftest now 10 PASS (template switch → scanner module, JSON
  write+parse, offline detect_all, offline port scan).

## Session 2026-09-19 (v1.0 original build)

- **Goal reached.** First working cut: GUI + generator + probe + HTML report all
  verified end-to-end locally, then frozen into a single `.exe`.
- Verified behaviours:
  - `LabServiceProbe.probe()` → detects banner `VulnLab-Service v1.0` → check
    verdict `Vulnerable`.
  - `MetasploitModuleGenerator.generate()` → 76-line Ruby module, `end` balanced
    (11), embeds current RHOSTS/RPORT into the description/check helpers.
  - GUI smoke test OK; all four sections mount and switch.
  - HTML report ~8 KB self-contained, includes module source + check verdict.

## Gotchas (learned the hard way)

1. **tkinter is NOT thread-safe.** v1.0 posted worker results via
   `self.root.after(0, ...)` from the worker thread → intermittent
   `RuntimeError: main thread is not in main loop`, so in the frozen exe the
   Live Test buttons *appeared* to do nothing. Fixed with a `queue.Queue` +
   main-thread poller; workers only `put()`.
2. **Ruby `%q{}` vs Python `%` formatting.** The Ruby literal `Description =>
   %q{...}` must be written `%%q{%s}` in the Python template string, otherwise
   Python raises `ValueError: unsupported format character 'q'`.
3. **Ruby single-quote strings do not interpolate.** `print_status('... #{uri}
   ...')` prints the literal `#{uri}`; must use double quotes.
4. **PyInstaller + tkinter:** no hidden imports needed on Windows with
   `--windowed`; ttk `clam` theme used for the combobox is available by default.
5. **vuln_service stderr logging** is intentional noise — not an error, do not
   "fix" it purely because PowerShell shows it as a native-command error
   stream.
6. **Windowed exes swallow tracebacks.** All diagnostics now go to
   `%TEMP%\msf_lab_studio_error.log` so problems in the exe are never silent.
7. **THE blank-UI bug (v1.0.x).** Every section's `card(...)` frames were
   created but never `.pack()`ed into the section page, so the frozen exe
   rendered an empty mint content area and *every* button visibly "did
   nothing". Fixed by having `card()` pack itself. Lesson: always assert
   `winfo_ismapped()`/`winfo_width()` in GUI harnesses. Verified on the real
   exe via `PrintWindow` screen capture + a color-census ASCII map.
8. **Headless self-testing of the frozen exe.**
   `MSF_STUDIO_SELFTEST=1 dist\MSF-Lab-Module-Studio.exe` runs the full
   workflow inside the real binary and writes `%TEMP%\msf_studio_selftest.out`.
9. **Interacting with a frozen tkinter window from automation is painful** —
   tkinter exposes no UIA element tree and SendKeys focus can be stolen.
   `PrintWindow(hwnd,hdc,2)` + pixel/color-band analysis is the reliable way
   to verify rendering.
10. **V2 URL-encoding:** raw query strings with spaces (e.g.
    `/exec?cmd=echo VULNLAB...`) make Python's `http.server` return 400; the
    internal `_RawHttp` client must `urllib.parse.quote(..., safe="/?=&%")`.
11. **Template rendering:** Ruby modules are rendered with `@@TOKEN@@`
    placeholder replacement (not Python `%`/`.format()`) so `%q{}`,
    `#{...}` and `%d` survive untouched; template switching auto-adopts
    module class/name/URI/CVE.
12. **Combobox values are labels:** `.set()` must use the display label from
    `VULN_TEMPLATES[*].label`, not a bare template id (ttk readonly).
13. **PAYLOAD_CHOICES is 4-tuples** (name, payload, arch, platform) — unpack
    with 4 targets in every loop, or you get `ValueError`.

## Conventions to keep

- Single source of truth: `app.config` dict (see `state.md` snapshot).
- Backend must stay free of tkinter imports → testable headless via `python -c`.
- Palette: soft-mint background `#E7F5F3`, teal accents, dark-teal code area.
  Not black, not white.
- All network calls go through a daemon thread + queue.Queue + main-thread
  poller (`root.after(80, _poll)`); workers NEVER touch Tk widgets directly.
- Profile persistence is opt-in via "Remember settings"; never write to disk
  without the user's intent (save paths are always user-chosen dialogs).

## Open questions

- Should we let users edit the Ruby source in the GUI before saving? Currently
  it is read-only and regenerated from options.
- Add MSF-version targeting dropdown (e.g. "modern msf6 branch")?
- v2 lives without pytest because tkinter import would be required; a pure
  non-GUI test module for module_builder would still be nice.