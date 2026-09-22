=====================================================================
 GLM BEACON LAB
 Encrypted C2 channel demo (TLS-wrapped beacon)
 + traffic decryption for blue-team study
=====================================================================

WHAT IS THIS?
-------------
A self-contained, offline Windows application that simulates a
command-and-control (C2) beacon hiding inside a TLS 1.3 tunnel —
and then hands you, the blue-teamer, the keys to tear that traffic
apart.

It is a TRAINING SANDBOX: the "implant" is a simulation that executes
only canned demo commands (whoami, ipconfig, dir, tasklist) against
fake host data. Nothing touches your real operating system, and all
traffic stays on 127.0.0.1.

WHO IS IT FOR?
--------------
* Blue-teamers learning what beacon traffic looks like on the wire
* SOC analysts practising TLS-inbound triage and frame carving
* Instructors demonstrating C2 mechanics safely
* Red-teamers studying which shortcuts get their channels detected

FEATURES
--------
* TLS 1.3 tunnel with a self-signed "lab.local" certificate
* Custom "GLM1" packet framing: AES-CTR ("CBCS(TM)") + HMAC-SHA256
* Jittered beacon check-ins (sleep +/- jitter, configurable)
* Live SOC-style traffic console with colour-coded event feed
* Registered-beacon table, operator tasking bar
* DECRYPTION LAB: paste the campaign passphrase, watch frames
  decrypt one by one (plaintext + ciphertext hexdump + header)
* Wrong passphrase fails loudly (MAC-first workflow)
* One-click analyst report export (HTML), capture export (txt),
  recovered-plaintext evidence export (txt)

ETHICS / LEGAL
--------------
Educational software for defenders. Do NOT use any of these techniques
against systems you do not own or lack written authorization to test.

PROJECT LAYOUT
--------------
  app.py                  the console UI (Tkinter)
  engine/                 listener, beacon, protocol, crypto, decrypt, report
  ARCHITECTURE.md         how everything fits together
  MEMORY.md               design decisions + gotchas
  STATE.md                current build status
  todo.txt                backlog
  how_to_run.txt          run + build instructions
  GLM_Beacon_Lab.spec     PyInstaller build recipe
  dist/GLM_Beacon_Lab.exe the packaged application
  captures/               saved capture text files land here
  engine/certs/           auto-generated self-signed lab certificate

QUICK START
-----------
See how_to_run.txt (short version: run dist\GLM_Beacon_Lab.exe,
click "Start listener + beacon", then explore the tabs).
