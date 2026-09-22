NL2Rule Translator
================================================================

Natural Language -> Sigma & YARA detection-rule translator.

Describe malicious behavior in plain English, get a production-shaped
Sigma rule, a matching YARA rule, and a MITRE ATT&CK mapping - plus a
styled, self-contained HTML report you can download and share.

--------------------------------------------------------------------------
RUN AS A WEB APP
--------------------------------------------------------------------------

    pip install -r requirements.txt
    python app.py

Then open  http://127.0.0.1:5001  in your browser.

The app listens on 127.0.0.1 only (localhost access).

--------------------------------------------------------------------------
RUN AS A STANDALONE EXE
--------------------------------------------------------------------------

    .\build_exe.ps1

Produces  dist\NL2Rule-Translator.exe  (fully self-contained).
Double-click it; your browser opens automatically at http://127.0.0.1:5001.
Close the console window to stop the server.

--------------------------------------------------------------------------
WHAT IT DOES
--------------------------------------------------------------------------

1. SCAN        - the description is normalized and split into clauses.
2. EXTRACT     - artifacts are pulled out as regex-backed entities:
                 IPs, domains, URLs, hashes (MD5/SHA1/SHA256), processes
                 (LOLBins + custom binary names), file paths, registry
                 keys, ports, usernames, mutexes, named pipes, task
                 names, event IDs, and inline strings.
3. DETECT      - a curated lexicon maps wording to detection concepts
                 (download-and-execute, credential dumping, persistence,
                 C2 beaconing, obfuscation, lateral movement, ...). Known
                 binaries such as mimikatz, certutil, schtasks further
                 colour the intent.
4. MAP         - concepts are scored into MITRE ATT&CK techniques.
5. GENERATE    - a Sigma YAML rule (logsource, selection, condition,
                 falsepositives, level, tags) and a YARA rule (meta,
                 strings, condition) are produced.
6. REPORT      - "DOWNLOoad REPORT" builds a self-contained HTML file.

--------------------------------------------------------------------------
SAMPLE INPUT
--------------------------------------------------------------------------

    Mimikatz runs on an endpoint and dumps credentials from the LSASS
    process memory using sekurlsa::logonpasswords, the attacker then
    attempts lateral movement to 192.168.10.45 port 445.

    -> Sigma + YARA rules with T1003 (credential dumping) tagging.

--------------------------------------------------------------------------
FILES
--------------------------------------------------------------------------

    app.py            Flask application + API routes
    exe_entry.py      PyInstaller entry point (picked up by EXE build)
    engine/           NLP + rule-generation pipeline
      lexicon.py      vocabulary, concepts, MITRE, LOLBin catalog
      entities.py     regex-based artifact extraction
      concepts.py     natural-language intent detection
      sigma.py        Sigma YAML generator
      yara.py         YARA rule generator
      report.py       self-contained HTML report renderer
      translator.py   end-to-end orchestration
    templates/        HTML pages (dark SOC theme)
    static/           CSS + JS for the UI
    examples/         ready-to-try scenario library
    tests/            smoke + app-level tests (python tests/test_app.py)

--------------------------------------------------------------------------
LEGAL NOTE
--------------------------------------------------------------------------

Built for legal, defensive, and lab/authorized use only. Generated rules
are heuristic drafts - validate them against your log pipeline before
production use.