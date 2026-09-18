# Reverse-Engineering CTF Challenge Solver Toolkit

## Architecture

A desktop application (`RE_Toolkit.exe`) for triaging and solving
reverse-engineering / crypto challenges from Capture-The-Flag (CTF)
competitions. It combines static file analysis, string/hex/entropy
inspection, classic cipher solving, and self-contained HTML report export
wrapped in a single-process Tkinter GUI.

```
+--------------------------------------------------------------------------------+
|                              RE Toolkit (the .exe)                             |
+--------------------------------------------------------------------------------+
| UI layer (customtkinter / tkinter)                                             |
|   SolverApp  : main window, sidebar navigation, toolbar, page stack            |
|   pages.py   : Home, FileInfo, Strings, Hex, Entropy, Frequency, Encodings,    |
|                XOR, Caesar, Vigenere, ReportPage                                |
|   widgets.py : ResultBox (tagged output box), Worker (thread bridge), Toolbar  |
+------------------------------------+-------------------------------------------+
| core engine (pure Python, no deps) | report layer                              |
|   fileinfo.py   metadata/hashes    | htmlreport.py                             |
|   signatures.py file magic DB      |   dark, responsive, self-contained HTML,  |
|   strings.py    ascii/utf-16       |   section builders + file & solver        |
|   hexdump.py    offset dump        |   report composers                        |
|   entropy.py    Shannon + blocks   |                                           |
|   frequency.py  N-grams, words,    |                                           |
|                 ASCII-text scoring |                                           |
|   encodings.py  hex/b64/b32/b58/   |                                           |
|                 b85/url/rot13/bin  |                                           |
|   ciphers.py    XOR single/multi,  |                                           |
|                 caesar, atbash,    |                                           |
|                 vigenere           |                                           |
+------------------------------------+-------------------------------------------+
```

## Module responsibilities

| Module                | Responsibility                                                        |
|-----------------------|------------------------------------------------------------------------|
| `toolkit/ui/app.py`   | `SolverApp` window: nav, file loading, page switching, report download |
| `toolkit/ui/pages.py` | One class per tool page; every page reads `app.current_bytes`          |
| `toolkit/ui/widgets.py`| `ResultBox`, `Worker` (UI-thread-safe async), `Toolbar`               |
| `toolkit/core/*`      | Deterministic, dependency-free analysis/solver functions               |
| `toolkit/report/`     | Purely string-based HTML builders; no templates, fully self-contained  |
| `run.py`              | Entry point; wraps `SolverApp().mainloop()`                            |

## Data flow

1. `SolverApp.open_file` reads the chosen file into `current_bytes` and
   stores `current_path`. Everything afterwards is **stateless**.
2. A page's "Run" action calls a core function inside `Worker`, which
   executes it on a background thread and marshals the result back to the
   main thread via `queue.Queue` + `after()` polling (Tkinter widgets are
   not thread-safe).
3. `ReportPage.generate` composes `build_file_report(...)` /
   `build_solver_report(...)` — the HTML is written to a user-chosen
   `.html` file through a native save dialog, then opened in the browser.

## Key algorithms

- **Strings**: greedy `[0x20,0x7F) ∪ {tab,lf,cr}` run extraction for
  ASCII; UTF-16LE runs where `hi==0x00`. Offsets are file offsets.
- **Entropy**: Shannon entropy `H = -Σ pᵢ log₂ pᵢ` per byte, per 256-byte
  block, plus overall verdicts (text/code < compressed < encrypted).
- **XOR single-byte**: all 256 keys, ranked with `english_gibberish_score`.
- **XOR multi-byte** (`ciphers.xor_multi_byte`): for each candidate key
  length, ciphertext is split into key-length columns; each column seeds
  candidate key bytes by **printability/letter ratio** (`ascii_text_score`)
  and by English frequency; three diverse seeds are refined by coordinate
  ascent against the *full-text* combined score. **Heuristic** — near-miss
  keys stay visible in the candidate list, and `xor_known_keys` plus the
  Vigenere known-key mode give exact results when a key is suspected.
- **Scoring** (`frequency.english_gibberish_score`): printable ratio +
  letter-frequency fit per character + interior-punctuation penalty +
  word-dictionary bonus (common words + CTF vocabulary) + fragment bonus.

## Design decisions

- **Zero third-party runtime deps** for the core engine; the only
  requirements are `customtkinter` (UI) and `pyinstaller` (build time).
- Analysis is bounded (samples capped at 4–16 KiB for solvers; hex dump
  rows capped; strings capped) so large binaries stay interactive.
- The report is generated as a single self-contained HTML string — no
  assets to ship, installed at click time, fully offline.
- Multi-byte XOR auto-breaking is explicitly labelled heuristic in the UI
  and reports; the exact tools (known-key XOR, known-key Vigenere) are the
  deterministic fallback.

## Build

See `readme.txt`. `python -m PyInstaller RE_Toolkit.spec` produces one
file, `dist/RE_Toolkit.exe`, Windows-GUI-subsystem (no console window).