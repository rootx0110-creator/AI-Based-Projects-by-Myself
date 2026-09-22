# Memory — project notes and hard-won lessons

Working notes for the SubnetPlanner project. Append as you learn; this file
is the persistent "memory" for anyone (human or agent) continuing the work.

## Environment specifics (Windows)

- CPython 3.14 is installed at `C:\Python314`. `pyinstaller` is NOT on PATH;
  always invoke as `python -m PyInstaller ...`.
- Confirmed working combo on this machine:
  `Python 3.14.7` + `PyInstaller 6.22.3` + `Tk 9.0` + `Pillow 12.3.0`.
- `pip install pyinstaller` puts the entry script under user site-packages
  (`...\Roaming\Python\Python314\site-packages\bin`), which is why the
  bare `pyinstaller` command fails.
- Building `--windowed` hides the console; add `--debug all` ONLY for
  troubleshooting (it prints to `stderr`).

## Build command that works (from project root)

```
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --icon assets/app.ico --name SubnetPlanner main.py
```

- `--onefile` → single `dist\SubnetPlanner.exe` (slow first launch while it
  unpacks into temp; subsequent launches are normal).
- No `--hidden-import` needed: the app only uses the stdlib at runtime.

## GUI / theming lessons

- ttk widgets ignore `fg`/`bg`; use `ttk.Style().configure(".", ...)` with
  `font`, `override=...`. Backgrounds bleed incorrectly unless you style
  every used element (Notebook tabs, Treeview, Scrollbar, Entry, Button).
- `Treeview` background only resets when `style.map(...)` includes a row
  that is both `selected` AND `!selected`; zebra rows come from `Fieldbackground`.
- Card look with plain ttk: a Panel frame in `#FFFFFF` + 1px grid border +
  generous padding. Don't fight ttk for rounded corners — flat/soft is fine.
- Scalable crisp font: `("Segoe UI", 10)`; monospace for IP text:
  `("Consolas", 11)`. Never render binary maps with proportional fonts.
- Windows High-DPI: Tk 8.6+/9 auto-scales on Windows; no manual scaling code
  was needed for Tk 9.0.4.

## Verifying the FROZEN exe on this machine (important gotcha)

- The window title uses a plain ASCII hyphen: the EnumWindows/find title is
  exactly `SubnetPlanner - Custom Subnet Calculator & VLSM Planner`.
- **PIL `ImageGrab` on a PyInstaller-frozen Tk 9.0.4 window returns BLACK**
  even when the same code outside the exe grabs fine. It is a screen
  compositing artifact, NOT the app. The app truly renders the correct
  theme — verify with `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)`:
  white cards ~70%, `#EAF0F6` background ~12%, `#0F172A` header ~8%.
- So: never judge the frozen UI by an ImageGrab screenshot; use PrintWindow.
- `main.py` supports `--debug` (stderr markers + tracebacks) for diagnosis —
  build a `--console` variant when that flag is needed. Keep PIL OUT of the
  production entry path: importing Pillow just for a self-screenshot added
  ~7 MB to the bundle, so `--debug` intentionally does not import it.

## Networking logic gotchas (core.py)

- The "usable host count" rule: `2^(32-prefix) - 2` for `/1`..`/30`;
  `/31` = 2 usable (RFC 3021 point-to-point), `/32` = 1 usable (loopback/single host).
- VLSM block size = `next power of two >= (required_hosts + 2)`; this
  guarantees `usable >= required`. Example: 25 hosts → block 32 → /27 → 30 usable.
- Always plan from the SORTED list (largest demand first) but PRESENT results
  sorted by network address; identical if planning rules are stable.
- Watch integer-only arithmetic — never float for IPs (`31 * 2**24` is int;
  `255.0` floats silently break bit logic).
- Mask ⇄ prefix: `prefix = 32 - (mask & -mask).bit_length()` doesn't hold in
  Python for 0; use `bin(mask).count("1")`.
- /32 and /31 bases: block can't expand below 1; guard before `next_power_of_two`.

## HTML report lessons

- Keep the report single-file: all CSS inline. Users double-click and print.
- Escape every user value (`html.escape`) — segment names are free text.
- `@media print` rules + `page-break-inside: avoid` on tables so VLSM tables
  print cleanly.
- Relative `%` widths + `min-width` for the big tables; never fixed px on the
  wide tables.

## Settings persistence

- Path: `~/.subnetplanner/settings.json` (user home, not project dir, so the
  bundled exe is truly portable).
- Wrap loads in try/except and fall back to defaults — settings file may be
  from a newer version.
- Geometry restore: `root.geometry(saved)` then re-`minsize`.

## Ideas for later (see todo.txt for tracking)

- CSV export, PDF via `--print-to-pdf` browser flag, dark mode toggle,
  IPv6 scope, "copy all as text", multiple-ring topology preview.