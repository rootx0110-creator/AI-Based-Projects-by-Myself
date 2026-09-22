# Memory - Wazuh/OSSEC Detection Rule Pack Studio

This file captures design decisions, constants and gotchas that must be respected
throughout the life of the project. Review before making changes.

## Idioms & conventions
- Rule IDs use the custom range **100000 - 100099** (local_rules.xml convention).
- Severity levels follow Wazuh: 0 = ignored, 3+ = alert, 6+ = moderate,
  12+ = high, 15 = GTR (no false-positive tolerance).
- Rule messages are lowercase, terse, and end without punctuation.
- `group` strings end with a comma per OSSEC convention.
- New rules must be added to ALL of: library, coverage matrix and at least one
  HTML report type.

## Key decisions (keep these)
1. **Embedded library**: no external data files bundled with the EXE. The 26
   seeds live in `app/rules_library.py`; runtime edits persist to
   `data/rulepack.json`.
2. **Zero-dependency reporting**: HTML reports use inline CSS only. No CDNs,
   no JS frameworks. Charts are `<div>`/`<table>` bars.
3. **Data directory**: `data/` is created next to the executable
   (`Path(sys.executable).parent`), falling back to cwd for development.
4. **Threading rule**: file I/O (reports / XML export) happens inline; it is
   fast and small. If exports grow, move to `threading`.
5. **MITRE mapping**: every rule carries exactly one ATT&CK technique id used
   in the coverage matrix.

## Validation invariants
- Duplicate rule ids in a pack = fatal; the pack refuses to save.
- Levels must be ints within [0, 16].
- Generated XML must re-parse with `xml.etree.ElementTree`.
- A rule without a `description` or `mitre` field is invalid.

## Gotchas
- Python 3.14 + tk 9.0: color strings are hex; alpha in customtkinter needs
  `0xAARRGGBB` or the `transparent` keyword, never an 8-digit CSS hex.
- PyInstaller onefile: `__file__` is not reliable for resources; always use
  embedded modules and `sys.executable` for the data dir.
- Windows path length: set `PYTHONUTF8=1` and keep export filenames short.

## Current sprint (see also todo.txt)
1. GUI views complete.
2. Report generator v1 stable.
3. EXE packaging verified.