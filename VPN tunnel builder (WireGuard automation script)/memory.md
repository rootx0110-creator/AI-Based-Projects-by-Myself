Memory
======

A persistent log of decisions, gotchas and lessons learned while building
the VPN Tunnel Builder. Append new entries at the top.

2026-09-18 - Packaged exe verified
----------------------------------
- dist\VPN Tunnel Builder.exe (~20 MB, PyInstaller 6.22.3, Python 3.14, onefile/
  windowed) launches, auto-bootstraps a server keypair on first run into
  %LOCALAPPDATA%\VPNTunnelBuilder\state.json, and the derived public key
  matches the stored one - pure-python X25519 works frozen.
- warn-*.txt only lists optional POSIX modules (pwd/grp/fcntl...) and
  optional numpy for PIL typing - all benign, nothing required is missing.

2026-09-18 - App() runs the Tk mainloop inside the constructor
--------------------------------------------------------------
- Breaking Tk design: mainloop() is called from App.__init__, so callers
  cannot schedule root.after(...) between construction and the loop.
- Added optional private param `_boot_test` (after-hook) so automated smoke
  tests and screenshot capture scripts work without changing the shipped path.
- Lesson: keep a dedicated boot-test hook for GUI CI.

2026-09-18 - tk.Label vs ttk.Label "style" option
-------------------------------------------------
- tk.Label has NO `style=` option (Tcl error "unknown option -style");
  that attribute exists only on ttk widgets. Mixed usage in a form caused a
  runtime crash caught by the boot smoke test. Grep for `tk.Label.*style=`.

2026-09-18 - RFC 7748 self-test vector trap
-------------------------------------------
- The Section 5.2 X25519 vector uses an ARBITRARY u-coordinate (e6db...),
  NOT the basepoint 9. Wiring that vector into `scalarbase` (u fixed to 9)
  fails by design. Fixed by adding `scalarmult(k, u)` + keeping two selftests:
  5.2 vector (scalarmult) and 6.1 ECDH vector (scalarbase). Cross-validated
  against `cryptography`'s X25519 over 10 random scalars.

2026-09-18 - WireGuard key format
---------------------------------
- `wg genkey` prints base64 of the RAW 32-byte secret (no header/version).
- `wg pubkey` is Curve25519 scalar-base-mult (basepoint = 9, as u-coordinate).
- The secret must be clamped the RFC 7748 way (bits 0-2 clear, bit 255 clear,
  bit 254 set) BEFORE scalar mult - the Go crypto library does this inside
  ScalarBaseMult, so from_private_bytes of the raw bytes matches wg.
- Lesson: implement X25519 in pure Python + RFC 7748 test vector self-check,
  so the exe has zero dependency on `cryptography` availability.

2026-09-18 - IP auto-assignment
-------------------------------
- "10.0.0.1/24" style relies on /24 the vast majority of cases, but the
  builder normalizes via ipaddress module to support any prefix and always
  computes first/last usable host + broadcast, avoiding bugs on odd prefixes.

2026-09-18 - QR codes in HTML reports
-------------------------------------
- qrcode + pillow produce PNG in memory; embedding as base64 data URI makes
  the report a SINGLE self-contained file that renders fully offline and can
  be emailed without a sibling assets folder.
- Lesson: never reference ./qr/*.png relative paths in generated docs.

2026-09-18 - PyInstaller onefile + tkinter
------------------------------------------
- Keep the entry module tiny (`main.py` imports `wgbuilder.app:run`) so
  --onefile does not double-bundle anything.
- No hidden imports were needed for tkinter/qrcode/PIL in this project;
  `--collect-data qrcode` guarantees fonts/branding files (none used here)
  and defends against future data-file additions.
- Lesson: verify the exe launches in a vanilla shell (no dev-venv) - state
  writing to %LOCALAPPDATA% must not silently fail.

2026-09-18 - Deleting the windowed-Console
------------------------------------------
- Use `--windowed` (a.k.a. -w) so a GUI exe does not flash a console.
- Report download uses tkinter filedialog, which requires a message loop;
  trigger generation from a button handler, not from __init__.

2026-09-18 - Deterministic exports
----------------------------------
- Sort peers by name before emitting server config and exports so re-runs
  produce byte-identical output (diff-able), which aids audits.