================================================================================
 VAULTGUARD  v1.0.0
 Password Strength Auditor & Wordlist-based Hash Cracker
 For educational / personal security testing. Crack ONLY hashes you own.
================================================================================

WHAT IT DOES
------------
1.  PASSWORD STRENGTH AUDITOR
    Paste any password and get a live 0-100 strength score with a circular
    gauge, entropy, character-class breakdown, a checklist of weaknesses and
    plain-language recommendations. It also estimates how long brute-force and
    dictionary attacks would take.

2.  WORDLIST-BASED HASH CRACKER  (your own hashes)
    Paste a hash of a password YOU own and let VaultGuard try to recover the
    plaintext using a wordlist. Supported hash types:
        MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512
    If you scan passwords through "Generate hash", it shows you the hash for a
    given algorithm so you can test the tool on yourself.

    Attack modes:
      * Straight attack    - try every word in the wordlist as-is.
      * Mangling rules     - also tries case variants, reversed words,
                             leet-speak (a->4, e->3, ...), number/year
                             suffixes (1, 12, 123, !, @, #, 2020...2026),
                             and symbol prefixes (recommended ON).

    A bundled default wordlist is created automatically on first run
    (default_wordlist.txt next to VaultGuard.exe). For serious testing load
    your own large wordlist via Browse...

3.  HTML REPORTS
    Both pages have a "Download HTML Report" button. The report is a
    self-contained, dark-themed HTML file with the audit results, the full
    cracking session, and time estimates - perfect for keeping records or
    printing.

--------------------------------------------------------------------------------
HOW TO USE
--------------------------------------------------------------------------------

A) STRENGTH AUDITOR
   1. Open the "Strength Auditor" tab (it is the default).
   2. Type a password in the field. The gauge, checklist, metrics and
      recommendations update as you type.
   3. Use "Show" to reveal the password, "Clear" to reset.
   4. Click "Download HTML Report" to save the analysis as an .html file.

B) HASH CRACKER
   1. Switch to the "Hash Cracker" tab.
   2. Paste YOUR hash into the hash box. The algorithm is auto-detected from
      its length and shown in green; you can override it with the dropdown.
      (To make a test hash yourself: choose algorithm MD5 above, tick the
      "Generate" note - simply run Python:  import hashlib;
      print(hashlib.sha256(b'password').hexdigest()))
   3. Choose a wordlist: "Use bundled" picks the default one, "Browse..."
      lets you select your own .txt (one word per line).
   4. Tune options: Mangling rules (recommended ON) and Threads (more = faster).
   5. Press "Start Attack". The progress bar and stats show live progress.
   6. Press "Stop" any time to halt. If the password is recovered it appears in
      the green "Identity recovered" panel along with the time/guess-rate.
   7. Click "Download HTML Report" to save the session as an .html file.

TIP: If your hash is not found, try:
      - a bigger/realistic wordlist (rockyou.txt style, no spaces per line)
      - mangling rules ON
      - the correct hash algorithm
      - your password just not being dictionary-recoverable (that is a GOOD
        sign for its strength - check the auditor!)

--------------------------------------------------------------------------------
BUILDING THE EXE FROM SOURCE (optional)
--------------------------------------------------------------------------------
Requires Python 3.12+ and the packages in requirements.txt.

    build.bat        (double-click)  -or-   powershell -ExecutionPolicy Bypass -File build.ps1

Output: dist\VaultGuard.exe  (single file, no install needed)

Running from source instead:  python main.py

--------------------------------------------------------------------------------
SECURITY & ETHICS
--------------------------------------------------------------------------------
* This tool is ONLY for auditing your own passwords. Cracking hashes without
  the owner's permission is usually a crime - don't do it.
* The app does not collect, upload or store anything. Hashes stay in memory;
  the HTML report you save is the only output and you control its path.
* Generic "fast" hashes (MD5/SHA) crack quickly. Hashes of strong, long,
  random passwords will simply not be found - use the auditor to confirm they
  are strong.

================================================================================
(c) VaultGuard Security Lab - for education and personal testing only.
================================================================================