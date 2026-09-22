WAZUH/OSSEC DETECTION RULE PACK STUDIO
=======================================

WHAT THIS IS
------------
A Windows desktop application for building, curating, validating and
exporting a custom Wazuh/OSSEC detection rule pack that covers ONE rehearsed
attack chain:

    Web Initial Access -> Execution -> Persistence -> Privilege Escalation
    -> Credential Access -> Discovery -> Lateral Movement
    -> Command & Control -> Exfiltration

It ships an embedded library of 26 detection rules mapped to the MITRE ATT&CK
stages, an interactive attack-chain view, a form-based rule builder with live
XML preview, pack validation, and offline HTML report export.

CONTENTS
--------
  app/                 Application source code
  architecture.md      System design document
  memory.md            Design decisions / invariants / gotchas
  state.md             State ledger (updated by the app)
  todo.txt             Work plan
  requirements.txt     Python dependencies for build/runtime
  run_gui.py           Development launcher (python run_gui.py)
  build_exe.ps1        One-click PowerShell EXE build script

FEATURES
--------
  * Dashboard   - KPI cards, severity distribution chart, stage coverage
  * Rule Library- search / filter / inspect / export rules
  * Attack Chain- 11-stage kill-chain with per-stage rule coverage
  * Rule Builder- structured rule creation + live local_rules.xml preview
  * Reports     - full pack, coverage matrix, severity and single-rule
                  reports exported as standalone .html files
  * Exports     - consolidated local_rules.xml for Wazuh/OSSEC manager

INSTALL & RUN (source)
----------------------
  pip install -r requirements.txt
  python run_gui.py

BUILD THE EXE
-------------
  powershell -ExecutionPolicy Bypass -File build_exe.ps1
  Result: dist/RulePackStudio.exe (single-file, no install needed).

USAGE NOTES
-----------
  * Runtime state is kept in data/rulepack.json next to the executable.
  * Reports and XML exports are written to data/exports/.
  * Deploy exports/local_rules.xml on a Wazuh manager under
    /var/ossec/etc/rules/ and restart wazuh-manager.

DISCLAIMER
----------
Provided for defensive detection engineering and lab use. The rule pack is
sample detection content, not a guarantee against any real-world campaign.