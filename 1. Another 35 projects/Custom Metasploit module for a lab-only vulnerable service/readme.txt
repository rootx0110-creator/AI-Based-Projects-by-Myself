=====================================================================
 MSF LAB MODULE STUDIO
 Custom Metasploit module for a LAB-ONLY vulnerable service
=====================================================================

WHAT THIS IS
------------
A small desktop tool that builds a custom Metasploit Framework module
(Ruby) for a deliberately vulnerable, lab-only HTTP service, auto-detects
which lab vulnerabilities are live, port-scans the box, verifies the lab,
and lets you download a polished HTML security report (plus a JSON twin).

It comes with:
  app.py            -> the GUI (four-step workflow, Alt+1..4 to navigate)
  vuln_service.py   -> the LAB-ONLY vulnerable target service
  build_exe.ps1     -> one-command EXE build (PyInstaller)
  dist/...exe       -> the built standalone application (if built)

LAB VULNERABILITIES (each has a matching module template)
---------------------------------------------------------
  /exec     -> OS command injection        -> exploit module (RCE)
  /file     -> path traversal / file read  -> auxiliary/scanner
  /backup   -> unauth config disclosure    -> auxiliary/scanner

QUICK START
-----------
1. Start the lab service (keep it on your localhost/isolated sandbox):

       python vuln_service.py --host 127.0.0.1 --port 8080

2. Launch the studio:

       python app.py

   (or just run dist/MSF-Lab-Module-Studio.exe)

3. In the studio:
   - Section 1 "Setup": pick a vulnerability template, keep the defaults,
     click "Apply configuration" (optional: "Remember settings").
   - Section 3 "Live Test": click "Detect all lab vulns" -> it auto-checks
     all three endpoints and reports which are vulnerable; "TCP port scan"
     sweeps common ports; "Simulate Metasploit check" returns the `check`
     verdict; the Smart advisor recommends your next move.
   - Section 2 "Builder": click "Generate Ruby module"; copy, save as
     vulnlab_exec.rb, or just keep it for the report.
   - Section 4 "Report": click "Generate & download report (.html)" or
     "Download JSON (machine readable)".

INSTALLING THE GENERATED MODULE INTO METASPLOIT
-----------------------------------------------
   cp vulnlab_exec.rb ~/.msf4/modules/exploits/linux/http/
   (msfconsole) > reload_all
   use exploit/linux/http/vulnlab_exec
   set RHOSTS  127.0.0.1
   set RPORT    8080
   check
   # -> [*] The target appears to be vulnerable.

   Scanner modules (path-traversal / config-leak) go under
   auxiliary/scanner/http/ and are driven with `run`.

GENERATING THE EXE
------------------
   pip install -r requirements.txt
   powershell -ExecutionPolicy Bypass -File build_exe.ps1
   # output: dist\MSF-Lab-Module-Studio.exe  (single file, windowed)

SELF-TEST (inside the frozen exe)
---------------------------------
   set MSF_STUDIO_SELFTEST=1
   dist\MSF-Lab-Module-Studio.exe
   type %TEMP%\msf_studio_selftest.out     (expect 10 PASS lines)
   All exceptions land in %TEMP%\msf_lab_studio_error.log.

DOCUMENTATION
-------------
   architecture.md  - system design and file map
   memory.md        - session notes and gotchas
   state.md         - application state snapshot / defaults
   todo.txt         - worklog and roadmap

SAFETY
------
THIS PROJECT IS FOR AUTHORIZED PENETRATION-TESTING LABS AND CTF
ISLANDS ONLY. The bundled service is intentionally insecure and must
never be reachable from a real network. You may only point the
generated module at systems you own or have written permission to test.

Requirements
------------
Runtime: Python 3.10+ with tkinter (Windows/macOS/Linux), no extra libs.
Build  : optional PyInstaller.