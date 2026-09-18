# VaultGuard — Architecture

VaultGuard is a Windows desktop application that (1) **audits password strength**
and (2) performs **wordlist-based hash cracking against hashes the user owns**.
It is written in Python 3.14, uses `customtkinter` for the UI, and is packaged as
a single-file EXE with PyInstaller.

## 1. High-level overview

```
+------------------------------------------------------------------------------+
|                             VaultGuard.exe                                  |
|                      (PyInstaller one-file bundle)                          |
+------------------------------------------------------------------------------+
|   ui/       customtkinter GUI layer (event-driven, Tk main loop)            |
|   ├── app.py        App root, chrome, page orchestration, background tasks  |
|   └── widgets.py    Reusable eye-catching widgets (gauge, cards, rows)      |
+------------------------------------------------------------------------------+
|   core/     Domain / business logic (no Tk dependencies — testable)         |
|   ├── hashing.py        hash generation, validation, algorithm detection    |
|   ├── strength.py       strength scoring, entropy, patterns, estimates      |
|   ├── cracker.py        threaded wordlist + mangling attack engine          |
|   ├── default_wordlist.py  curated weak-password list + file provisioning   |
|   └── report.py         self-contained HTML report generator                |
+------------------------------------------------------------------------------+
|   main.py      entry point (inserts project root on sys.path, launches ui)  |
|   wordlists/   user-supplied wordlist files (bundled default provided)      |
+------------------------------------------------------------------------------+
```

## 2. Modules

### 2.1 `core/hashing.py`
Pure functions with no side effects.

| Function                    | Purpose                                              |
|-----------------------------|------------------------------------------------------|
| `hash_password(pwd, algo)`  | Hash a string with MD5/SHA-1/SHA-224/-256/-384/-512   |
| `detect_algorithm(hash)`    | Hex-length based algorithm detection                  |
| `is_valid_hash(hash, algo)` | Validate format/length                                |
| `normalize(hash)`           | Lowercase + trim                                      |

Algorithms table: `ALGORITHMS = {name: (hex_length, hashlib_name)}`.

### 2.2 `core/strength.py`
`audit_password(password) -> dict` produces a single, UI-ready result object:

* `score` / `score_float` (0–100), `rating`, `rating_color`
* `length`, `classes` (of 4), `unique_chars`, `entropy` (Shannon bits)
* `search_space_bits` (`log2(unique_chars ** length)`)
* `checks[]` — passable check list (length, variety, common-list, patterns…)
* `suggestions[]` — human-readable recommendations
* `time_estimates` — brute-force (GPU fast-hash: 10 B/s) and dictionary timings

Scoring model:
```
score = min(length/16,1)*55         # up to 55
      + max(classes-1,0)/3*20       # up to 20
      + min(entropy/8,1)*15         # up to 15
penalties: common word −35, sequential/keyboard −12, repeated runs −14,
           single-char −20, one-class-short −8
clamped to [0, 100].
```

### 2.3 `core/cracker.py`
`crack(target_hash, algorithm, wordlist_path, mangling, workers, stop_event,
progress_cb) -> CrackResult`

* Loads the wordlist into memory (`load_words`).
* For each word, `candidates_for(word, mangling)` expands into a deduplicated
  candidate set: plain word, case variants, reversed, leet-speak, numeric/year
  suffixes, and symbol prefixes.
* A shared slash-and-claim counter (`index` + lock) distributes words across
  `workers` threads. `hashlib` releases the GIL during digest computation, giving
  near-linear speed-up with threads.
* `progress_cb(CrackProgress)` is throttled to ~8 Hz from the coordinating loop.
* `stop_event` (a `threading.Event`) is checked between candidates for halt.
* Returns a `CrackResult` dataclass (found password, attempts, words done,
  elapsed, guesses/second, inline errors).

Important: this is a **fast-hash** (MD5/SHA family) cracker — exactly the
account/config hashes a security student would self-test. It is *not* a
slow-hash or GPU engine.

### 2.4 `core/default_wordlist.py`
* `CURATED_WORDS` — ~300 well-known weak passwords.
* `_numeric_lines()` — years (1900–2100) + zero-padded numerics.
* `ensure_default_wordlist(candidates)` — locates an existing
  `default_wordlist.txt` or writes one into the first writable directory
  (EXE folder → `~/.vaultguard`).
* `COMMON_WORDS` — frozen-set used by the auditor’s common-password check.

### 2.5 `core/report.py`
`build_html_report(audit, crack, title, version, timestamp) -> str` builds a
self-contained dark-themed HTML page (inline CSS, conic-gradient gauge,
checklists, result tables — zero external assets, prints cleanly).

`save_html_report(path, html)` writes the file as UTF-8.

### 2.6 `ui/widgets.py`
| Widget             | Purpose                                                |
|--------------------|--------------------------------------------------------|
| `Header`           | Tk-canvas gradient header with title/badge             |
| `StrengthGauge`    | Canvas arc gauge, 40 colour-interpolated segments      |
| `StatCard`         | Label + big value metric card                          |
| `CheckRow`         | ✓/!/✗ dot row for the checklist                        |
| `SectionTitle`     | Accent-bar section heading                             |
| `StatusDot`        | Footer status indicator                                |
| helpers            | `gradient_color()`, colour palette dict `C`            |

### 2.7 `ui/app.py`
Two pages are built once and toggled with `tkraise()`:

* **AuditorPage** – live score (debounced 220 ms), gauge, metric cards,
  checklist, recommendations, *Download HTML Report*.
* **CrackerPage** – hash text area with live auto-detect, algorithm picker,
  wordlist picker/browse/bundled, mangling toggle, thread count,
  Start/Stop controls, progress bar + live stats, result card,
  *Download HTML Report*.

Thread-safety rule (enforced): the crack runs in a background thread that never
touches Tk. It communicates through `queue.Queue`; the UI polls with `after()`.
Tk variables (`mangle_var`, `workers_var`, …) are read on the main thread and
passed into the thread explicitly.

## 3. Control flow — cracking session

```
User clicks Start (main thread)
   │  validate hash + wordlist + algorithm (auto-detect label)
   ▼
spawn daemon thread ──── crack() ────────────────────────────┐
   │  clears stop_event, disables Start, enables Stop, after(120ms, poll)
   ▼                                                          │
main loop polls queue every ~120 ms ◄── progress_cb puts CrackProgress (≤8 Hz)
   │  renders progress bar + stats                            │
   ▼                                                          │
"done" arrives ──► _render_done(): restore buttons, detect   │
   found / not-found / errors, store last_result for report  ┘
```

## 4. Report generation flow

```
Auditor last_audit  (audit result dict)   \
                                          ├──► build_html_report() ─► .html
Cracker last_result (CrackResult.__dict__)/
```
The user picks a target file with `filedialog.asksaveasfilename`. Default name:
`vaultguard_report_<timestamp>.html`.

## 5. Build & distribution

* `main.py` — source entry point. When frozen, `resource_dir()` returns the EXE
  directory so the default wordlist is generated next to the binary.
* `tools/make_icon.py` — Pillow programmatic icon (`app.ico`, 16–256 px).
* `build.ps1` / `build.bat` — icon + `PyInstaller --onefile --windowed
  --collect-all customtkinter --collect-all darkdetect --version-file ...`.
* Output: `dist/VaultGuard.exe`.

## 6. Security & ethics notes

* The application only ever tests hashes the user pastes in — it never collects,
  uploads, or stores real-world credentials.
* Hash inputs are kept in memory only; reports contain the hash and recovered
  plaintext by design (user chooses where that report is saved).
* The tool is explicitly framed as an educational/personal security utility;
  cracking third-party hashes without permission is illegal in most jurisdictions.