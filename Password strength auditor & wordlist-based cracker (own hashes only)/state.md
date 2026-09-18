# VaultGuard — Project State

## Status: DONE

All phases complete. The one-file EXE is built and smoke-tested.

## Feature checklist
- [x] Password strength auditor (live scoring, entropy, patterns, guidances)
- [x] Wordlist-based cracker: straight + mangling attack (MD5/SHA-1/SHA-224/-256/-384/-512)
- [x] Auto-detect hash algorithm from hex length + manual override
- [x] Threaded guessing with live progress bar, guesses/sec, stop control
- [x] Curated + generated default wordlist, user wordlist browsing
- [x] Eye-catching customtkinter dark UI (gradient header, arc gauge, stat cards)
- [x] Self-contained HTML report download (audit + crack sections)
- [x] Application icon generation (`tools/make_icon.py`)
- [x] Build scripts (`build.bat`, `build.ps1`) + version resource
- [x] `readme.txt`, `architecture.md`, `memory.md`, `state.md`
- [x] PyInstaller build of `dist/VaultGuard.exe` (≈20 MB, one file)
- [x] Smoke-test the frozen EXE: launches, stays alive, correct window title,
      renders full custom UI (967-colour screenshot check), auto-creates
      `default_wordlist.txt` beside the EXE

## File inventory
```
architecture.md          — design doc
memory.md                — engineering knowledge / gotchas
state.md                 — this file
readme.txt               — end-user instructions
main.py                  — entry point
requirements.txt          — runtime + build deps
version_info.txt          — Windows version resource
app.ico                  — generated icon
build.bat / build.ps1    — one-click EXE build
tools/make_icon.py       — icon generator (Pillow)
core/__init__.py
core/hashing.py          — HASH OK, tested
core/strength.py         — AUDIT OK, tested
core/cracker.py          — CRACK OK, tested (threads/stop/progress)
core/default_wordlist.py — OK, tested (provisions default_wordlist.txt)
core/report.py           — OK, tested
ui/__init__.py
ui/widgets.py            — OK, tested (gauge/cards/rows/header)
ui/app.py                — OK, tested (both pages + save-report path)
default_wordlist.txt     — generated at first run in project dir (now present)
```

## Next actions
1. Optional: run `build.ps1` again to regenerate a fresh EXE after source edits.
2. Add `.gitignore` for `__pycache__`, `build/`, `dist/`, `*.spec`, `default_wordlist.txt`
   if the repo is ever initialised.

## Known limitations (accepted)
* Fast-hash only (MD5/SHA family) — no bcrypt/argon2/NTLM/LM, no GPU kernels.
* Markov/rule engines limited to built-in mangling set (no user-defined rules).
* HTML report is intentionally static (no JS charts) for portability.
* One EXE replaces any prior distributed copy; the default wordlist is written
  beside the EXE on first run (2nd fallback: `~/.vaultguard`).