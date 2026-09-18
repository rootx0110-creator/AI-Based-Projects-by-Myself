=====================================================================
   REVERSE-ENGINEERING CTF CHALLENGE SOLVER TOOLKIT
=====================================================================
   Build an .exe application for triaging and solving reverse-
   engineering / crypto challenges from CTF competitions.
=====================================================================

WHAT IS IT
----------
A Windows desktop tool that lets you load any challenge file and:

  * File Information      metadata, MD5/SHA-1/SHA-256/CRC32 hashes,
                          magic-byte identification, PE/ELF header parse
  * Strings               ASCII + UTF-16 string extraction with offsets
  * Hex Dump              offset-aware hex + ASCII dump
  * Entropy Analysis      Shannon entropy, per-block bands, verdicts
  * Letter Frequency      histogram to guide substitution analysis
  * Encoding Toolbox      Hex, Base64/32/58/85 (Ascii85), URL, ROT13,
                          Binary, plus auto-detection
  * XOR Solver            single-byte brute force, multi-byte breaking,
                          known-key tries
  * Caesar / Atbash       all 26 shifts ranked by English score
  * Vigenere              auto key-length break or decode with a key
  * HTML Report           one-click "Download HTML Report" for every
                          analysis (self-contained, dark themed)

The UI is dark-theme, keyboard friendly, and every result page can be
exported to a report that opens straight in your browser.

QUICK START
-----------
1. Run RE_Toolkit.exe (a single portable file, no install needed).
2. Click "Open File" (sidebar) and pick your challenge binary.
3. Tool pages read the loaded file automatically - just hit Run.
4. For plaintext payloads use the Encoding Toolbox and cipher pages;
   "Auto-detect" tries every decoder on pasted/loaded text.
5. "Download HTML Report" saves and opens a report of the full analysis.

A TYPICAL WORKFLOW FOR A CTF BINARY
-----------------------------------
1. File page -> identify the file (PE / ELF / PNG / ZIP / raw bytes).
2. Strings   -> look for flag{...}, URLs, interesting keywords.
3. Hex Dump  -> inspect magic bytes and offsets of interest.
4. Entropy   -> very high entropy usually = packed or encrypted payload.
5. Encodings -> decode the suspicious payload (base64/hex/url ...).
6. XOR       -> if garbage stays, brute single byte; then multi-byte;
                known keys as a quick check.
7. Caesar / Vigenere for shift-cipher-encoded text.
8. Report    -> save an HTML report to document your solve.

BUILDING FROM SOURCE
--------------------
Requirements:  Python 3.10+ (tested on 3.14), pip.

  pip install -r requirements.txt

Run from source:

  python run.py

Build the .exe (one file, no console window):

  build_exe.bat
  # or:  python -m PyInstaller RE_Toolkit.spec

The executable is written to  dist\RE_Toolkit.exe

PROJECT LAYOUT
--------------
  run.py                     entry point
  toolkit/
    core/          solver engine (analysis + crypto, no 3rd-party deps)
      fileinfo.py  signatures.py strings.py hexdump.py entropy.py
      frequency.py encodings.py ciphers.py
    report/
      htmlreport.py       self-contained HTML report builders
    ui/
      app.py              main window + navigation + report download
      pages.py            the tool pages
      widgets.py          ResultBox, Worker thread bridge, Toolbar
  architecture.md         design overview
  memory.md               solver heuristic notes / gotchas
  state.md                state model and file formats
  readme.txt              this file
  requirements.txt        build/runtime dependencies
  RE_Toolkit.spec         PyInstaller spec
  build_exe.bat           one-shot Windows build helper

NOTES & LIMITATIONS (read before trusting a solve)
--------------------------------------------------
* Single-byte XOR, Caesar, Atbash, known-key Vigenere and all encoding
  tools give exact results.
* Multi-byte XOR auto-breaking and the Vigenere auto-break are
  heuristics: they surface the most English-looking candidates. On short
  or punctuation-heavy plaintext a near-miss key can win. The candidate
  list stays readable, and the known-key modes are the deterministic
  fallback.
* This is a static-analysis triage kit, not a decompiler. For deep
  malware/obfuscation reverse engineering use Ghidra/IDA alongside it.
* Only for legal, authorised CTF challenges and your own software.

LICENSE / ETHICS
----------------
Use only on challenges you own or are explicitly allowed to analyse.
No telemetry, no network use, no persistence - fully offline.