# VaultGuard — Memory

Persistent engineering knowledge and gotchas for this project. Update whenever a
non-obvious lesson is learned.

## Environment
* Python **3.14.7**, `pip` 26.2.1, Windows 11 (win32), PowerShell 5.1.
* Installed and used: `customtkinter 6.0.0`, `darkdetect 0.8.0`,
  `pyinstaller 6.22.2`, `pillow 12.3.0`.
* Shell: commands must use PowerShell semantics (no `&&`; use `;` / `if ($?)`).

## Key implementation decisions (why)
1. **Threading the cracker** — `hashlib.*` digest calls release the GIL, so
   plain Python threads give near-linear speed-ups on MD5/SHA-family hashing.
   Word distribution uses a shared counter + mutex (slice-locking keeps `index`
   accurate under GC/free-threading).
2. **UI  never  touched  from  background  threads** — the crack thread posts
   `CrackProgress`/`CrackResult` onto a `queue.Queue`; the Tk main loop polls
   with `self.after(120, ...)`. This guarantees thread safety and lets "Stop"
   be a plain `threading.Event`.
3. **Tk variables must be read on the main thread** — a previous bug surfaced
   `main thread is not in main loop` because `self.mangle_var.get()` (a Tcl
   call) was executed inside the crack thread. Values are captured in
   `_start()` and passed in as arguments.
4. **No external assets for reports** — the HTML report is self-contained
   (inline CSS, conic-gradient gauge) so it renders offline and prints cleanly.

## Gotchas / traps (read before editing)
* `customtkinter` widget names are prefixed: `CTkEntry` (not `Entry`),
  `CTkTextbox`, `CTkButton` — a bare `ctk.Entry` raises AttributeError.
* Tkinter does **not** accept 8-digit hex colours (`#7c5cff22`) in
  `create_rectangle` — always use 6-digit hex.
* Triple-quoted f-string concatenation: `f"""a""" + x + """b"""`.
  Writing `f"""a"" + x + """b"""` (two quotes) silently swallows the terminator
  into the string body and produces confusing "invalid decimal literal"
  SyntaxErrors much later in the file — that exact bug cost real debugging time
  in `core/report.py` (line 125).
* `audit_password("password")` correctly returns score 0 — verified in both the
  core and through the GUI. When a GUI page seems stale, remember the 220 ms
  debounce: `app.update()` alone may not fire it; sleep ≥ ~250 ms or let the
  mainloop run.
* `Set-Variable` is aliased as `SV` in PowerShell — don’t name helper functions
  `SV` (positional-arg binding errors).
* When packaging: use `--collect-all customtkinter --collect-all darkdetect`
  (they ship data/theme files PyInstaller’s analysis misses otherwise).
* Default wordlist provisioning is multi-dir: EXE folder first, then
  `~/.vaultguard`. The app never assumes the EXE folder is writable.

## Verified behaviours (regression reference)
* `strength.audit_password`: `P@ssw0rd123!` → 56 Fair; `password` → 0 Very Weak;
  `password123` → 4 Very Weak; empty → 0.
* Cracker finds `qwerty123` (SHA-256 via mangling of `qwerty`) within ~112
  attempts; a not-found dictionary finishes and reports attempts cleanly.
* GUI cracker (100% automated smoke test): `vaultguard` recovered with SHA-1,
  progress bar reaches 1.0, Start button re-enables; Stop mid-run returns a
  partial result (3011/20000 words in one recorded run).
* Report builder round-trip: `build_html_report` yields a printable, valid HTML
  doc (≈7 KB) containing audit + crack sections.