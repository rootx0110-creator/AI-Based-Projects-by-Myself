=====================================================================
 MOBILE DEVICE FORENSIC WORKFLOW (MFW)
 Android logical acquisition | Lab toolkit | HTML report download
=====================================================================

QUICK START
-----------
0. Want to inspect YOUR OWN phone? Read  how_to_check_your_mobile.txt
   - a plain step-by-step walkthrough (USB debugging, backup prompt,
   which method to pick, troubleshooting).
1. Run  MobileForensicWorkflow.exe  (dist/ folder after a build).
   - First run creates  data\  next to the exe and a sample case
     "DEMO-001" so every screen has data immediately.
2. Create your real case in  Case Manager  (case number + examiner
   are required). It becomes the ACTIVE case (chip in the header).
3. Go to  Extraction :
   - Connect the Android device by USB, enable USB debugging.
   - "Refresh Devices" -> pick the device -> "Read Device Info".
   - Choose a method:
       * ADB Backup (logical) - on the device, tap "Back up my data"
         when prompted (the tool waits up to ~4 minutes).
       * Package inventory    - installed apps (3rd-party + system).
       * Screenshot capture   - PNG of the current screen.
       * Demo dataset         - works with NO device attached.
   - "Start Extraction" and watch the live log.
4. Review parsed data in  Artifacts  (Calls / SMS / Contacts / Apps,
   search box, CSV export).
5. Go to  Reports , fill the report title/classification/summary and
   click  DOWNLOAD HTML REPORT . Default save location is the case's
   reports\ folder. The report is a single self-contained HTML file
   (opens in any browser, prints cleanly) including case info, device
   info, methodology, findings tables, SHA-256 evidence hashes and the
   chain of custody.
6.  Audit Log  records every action (global) plus a per-case trail in
   the case folder (audit.txt, chain_of_custody.csv).

DATA LOCATION
-------------
Everything is stored in  data\  next to the executable:

  data\cases_index.json        all case metadata
  data\audit.log               global audit trail
  data\cases\<CASE_NUMBER>\
      metadata.json  audit.txt  chain_of_custody.csv
      evidence\      extracted\  reports\  exports\

Delete data\ to reset the app to factory state.

ADB (ANDROID PLATFORM-TOOLS)
----------------------------
The app looks for adb.exe on PATH and in common SDK locations:
  C:\platform-tools\adb.exe
  %LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
If not found, the header shows "ADB: not found" and only the Demo
dataset method works. Install platform-tools and re-open the app.

BUILD FROM SOURCE
-----------------
  pip install PySide6 pyinstaller
  python -m PyInstaller --noconfirm --clean --onefile --windowed ^
              --name MobileForensicWorkflow main.py
  -> dist\MobileForensicWorkflow.exe

Headless check:  set QT_QPA_PLATFORM=offscreen && python smoke_test.py

TROUBLESHOOTING
---------------
- App starts but no window appears?  Check  data\startup_error.log  next
  to the exe — any startup crash is written there in plain text.
- "Backup file missing or empty" -> the backup was cancelled on the
  device or timed out; device screen must be unlocked. Evidence and
  logs are still kept.
- No devices listed -> check USB debugging authorization (accept the
  RSA prompt on the phone).
- Antivirus flags the exe (typical for PyInstaller onefile builds) ->
  add an exclusion for your lab folder.

SECURITY NOTE
-------------
This is a lab tool for lawful examinations. It performs LOGICAL,
user-level acquisitions only and never modifies the device. Keep the
generated reports and hash records with your case file.
