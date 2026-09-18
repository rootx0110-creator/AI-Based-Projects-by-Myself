================================================================================
 WIRELESS NETWORK AUDITOR
 WPA/WPA2 Handshake Capture - Your Own Lab Access Point
 Version 1.0.0
================================================================================

WHAT IS THIS?
--------------------------------------------------------------------------------
A self-contained web application for capturing and analyzing the WPA/WPA2
4-way handshake emitted by an access point you control in a lab environment.
It scans for access points, targets a lab AP, captures handshake packets
(EAPOL frames), records the session, and produces a downloadable HTML audit
report.

UNDERSTAND THE SCOPE
--------------------------------------------------------------------------------
- Educational / authorized-lab use ONLY.
- The default ENGINE is SIMULATION. It generates realistic demo data so you
  can evaluate the full workflow on ANY machine (Windows, macOS, Linux)
  without a special adapter.
- Setting AUDITOR_ENGINE=live enables REAL monitoring via aircrack-ng
  (airodump-ng + aireplay-ng) on Linux with a monitor-mode adapter.
  Only use live mode against your own lab infrastructure.
- Deauthentication frames are disruptive. Never send them to networks you
  do not own or have explicit written authorization to test.

REQUIREMENTS
-------------------------------------------------------------------------------
Python 3.8+

Optional (only for LIVE mode):
  - scapy  (pip install scapy)
  - Windows: Npcap (https://npcap.com) - enables the Wi-Fi adapter for capture
  - Linux: aircrack-ng (airodump-ng, aireplay-ng) and/or libpcap
  - a wireless adapter (monitor mode needed for true passive capture of APs
    other than the one you are connected to)

In Simulation mode, no adapter or external programs are required.

INSTALLATION
--------------------------------------------------------------------------------
1) Create a virtual environment (recommended):

   Windows:
     python -m venv venv
     venv\Scripts\activate

   Linux / macOS:
     python3 -m venv venv
     source venv/bin/activate

2) Install dependencies:

     pip install -r requirements.txt

   (The only hard dependency is Flask. All other modules are stdlib.)

3) Start the application:

     python app.py

   Then open your browser at:

     http://127.0.0.1:5001

QUICK START (Simulation mode - the default)
--------------------------------------------------------------------------------
1. Dashboard loads.  Click "Scan Networks" in the sidebar, or the
   "Start Scan" button on the Scanner page.
2. A list of lab access points appears with SSID, BSSID, channel and
   signal strength.
3. Pick a target AP and click "Capture Handshake".
4. On the Capture page press "Start Capture". Watch the state machine
   progress: Idle -> Listening -> EAPOL detected -> Handshake complete.
5. Optionally press "Trigger Deauth Burst" to speed up handshake
   acquisition (simulated counters give near-immediate results).
6. When the handshake completes, a "Generate & Download Report" button
   appears. Click it to produce and download a self-contained .html audit
   report. The report is also archived under "Reports".

LIVE MODE (real capture on your own AP)
-------------------------------------------------------------------------------
Windows (recommended, no monitor mode needed):
  1. Install Npcap (https://npcap.com) - required for live capture.
  2. Have the machine's Wi-Fi connected to YOUR lab access point.
  3. Start the app with the live engine:
       AUDITOR_ENGINE=live python app.py
     (the app auto-detects the Wi-Fi adapter; you can also pick an interface
      from the Scanner page dropdown.)
  4. Scan now lists REAL access points in range (from the OS Wi-Fi scan).
  5. Pick your lab AP and start capture. The app passively sniffs the
     connected adapter for EAPOL (0x888e) frames. To capture a fresh
     4-way handshake, reconnect a client to the AP while capture runs.
  6. Raw frames are written to captures/<ssid>-XXXX.cap for external
     analysis (aircrack-ng, hcxpcapngtool / hashcat).

Linux (monitor mode, aircrack-ng):
  1. sudo airmon-ng start wlan0   (note adapter name, e.g. wlan0mon)
  2. AUDITOR_ENGINE=live AUDITOR_IFACE=wlan0mon python app.py
  3. Scanning invokes airodump-ng; capture tails its .cap for EAPOL; deauth
     invokes aireplay-ng --deauth against the selected BSSID.

Note: deauth frame injection is legal ONLY against your own lab AP. On
Windows managed mode injection is not available - the app explains the safe
alternative (reconnect a client instead).

CONFIGURATION (environment variables)
--------------------------------------------------------------------------------
AUDITOR_HOST     Bind address          (default: 127.0.0.1)
AUDITOR_PORT     Web port             (default: 5001)
AUDITOR_ENGINE   simulation | live    (default: simulation)
AUDITOR_IFACE    Wireless interface    (default: wlan0, live mode only)
AUDITOR_DB       SQLite database path  (default: database/settings.db)
AUDITOR_CAPTURE_DIR  Capture file dir  (default: captures)
AUDITOR_OUT_DIR      Report output dir (default: reports/out)

PROJECT LAYOUT
--------------------------------------------------------------------------------
app.py              Flask web server and REST API
config.py           Configuration from environment variables
capture/            Capture engine (scanner, handshake, deauth, analyzer)
database/           SQLite persistence layer
reports/            HTML report generator
templates/          UI pages (dashboard, scanner, capture, reports)
static/             CSS and JS
captures/           Live-mode .cap files
reports/out/        Generated .html reports
architecture.md     System architecture document
memory.md           Memory model document
state.md            State machine document

DOCUMENTATION
--------------------------------------------------------------------------------
See architecture.md, memory.md and state.md for system design.
This readme.txt covers setup and operation.

LEGAL / ETHICAL DISCLAIMER
--------------------------------------------------------------------------------
This software is provided for lawful educational and research purposes only.
Capturing handshakes or sending deauthentication frames to wireless networks
that you do not own, or for which you lack explicit authorization, is illegal
in most jurisdictions. You bear full responsibility for how this software is
used. The author(s) assume no liability for misuse.
================================================================================