BEACON DETECTION LAB
====================
Defensive, educational HTTP-beaconing detector with a local web dashboard
and one-click HTML report download.

WHAT THIS IS
------------
A blue-team teaching tool: feed it a web-server access log or a pcap, and it
finds sources that "check in" to the same destination at machine-regular
intervals - the traffic signature defenders look for when hunting C2 beaconing.
It analyzes evidence; it does NOT generate, emulate, or execute anything.

QUICK START
-----------
Requirements: Python 3.9+ (standard library only - no pip installs)

  1. Generate test data (synthetic, offline, no network activity):
        python make_sample_data.py

  2. Command line:
        python analyzer.py samples/access.log -o report.html
        python analyzer.py samples/capture.pcap --json findings.json
        python analyzer.py samples/access.log -t 70          # stricter threshold

  3. Web dashboard (real UI + report download):
        python dashboard.py
     Opens http://127.0.0.1:8000 in your browser.
     Upload samples/access.log or samples/capture.pcap, press Analyze,
     then "Download full HTML report".

WINDOWS EXECUTABLES (NO PYTHON NEEDED)
---------------------------------------
Pre-built in dist\ - just double-click or run from a terminal:

  dist\BeaconDetectionLab.exe
      Double-click: starts the local dashboard (127.0.0.1, first free port
      8000-8029), opens your browser automatically. Windowless app; errors
      are logged to %TEMP%\BeaconDetectionLab.log.

  dist\beacon-analyzer.exe  (command line)
      beacon-analyzer.exe samples\access.log -o report.html
      beacon-analyzer.exe samples\capture.pcap --json findings.json
      beacon-analyzer.exe samples\access.log -t 70

To rebuild the exes after code changes (needs Python + pip once):
      build.bat

WHAT YOU SHOULD SEE
-------------------
- access.log : 203.0.113.66 -> /wp-content/cache/refresh.php every ~60s
               scores ~100/100 (HIGH)
- capture.pcap : 10.0.0.50 -> 93.184.216.34 every ~30s scores ~100/100 (HIGH)
- all benign browsing hosts stay below the medium threshold

FILES
-----
  analyzer.py          core engine: parse, group, score, render report
  dashboard.py         local web UI (loopback only)
  launcher.py          windowed entry point used by BeaconDetectionLab.exe
  build.bat            rebuilds both executables with PyInstaller
  dist\                BeaconDetectionLab.exe + beacon-analyzer.exe
  make_sample_data.py  synthetic safe test-data generator
  detections/          educational Sigma + YARA rules
  architecture.md      design and data flow
  state.md             current project status
  memory.md            durable decisions and gotchas
  todo.txt             task list
  samples/             created by make_sample_data.py
  reports/             where CLI reports land if you use -o reports/report.html

SAFETY / SCOPE
--------------
This project is for learning defensive network analysis on data you are
authorized to analyze. It contains no implant, beacon, listener, or payload
functionality, and none will be added. The dashboard binds to 127.0.0.1;
it is not exposed to your network.
The executables are plain PyInstaller packages of this same code.
