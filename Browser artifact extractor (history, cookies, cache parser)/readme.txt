================================================================================
                    BROWSER ARTIFACT EXTRACTOR v1.0
            History, Cookies & Cache Parser for Windows
================================================================================

OVERVIEW
--------
Browser Artifact Extractor is a powerful yet easy-to-use tool that extracts
browsing artifacts from locally installed web browsers on your Windows system.

It parses browser history, cookies, and cache data, presenting them in a
beautiful, easy-to-navigate web interface. You can search, filter, and export
results as HTML reports.

SUPPORTED BROWSERS
------------------
  - Google Chrome
  - Mozilla Firefox
  - Microsoft Edge
  - Brave Browser

FEATURES
--------
  * Auto-detect installed browsers
  * Extract browsing history (URLs, titles, visit counts, timestamps)
  * Extract cookies (domain, name, value, expiry, secure flag)
  * Parse cache metadata (URLs, file sizes, MIME types)
  * Beautiful, modern web-based user interface
  * Search and filter across all artifacts
  * Sort data by any column
  * Export results to HTML report
  * Export to JSON format
  * Export to CSV format
  * Real-time extraction progress
  * No installation required (portable)

REQUIREMENTS
------------
  - Windows 10 or Windows 11
  - Python 3.8+ (if running from source)
  - 256 MB available RAM
  - Browsers should be closed during extraction for best results

QUICK START
-----------
  Option 1: Run the executable
    1. Double-click BrowserArtifactExtractor.exe
    2. The application will open in your default web browser
    3. Click "Detect Browsers" to scan your system
    4. Select browsers and click "Extract"
    5. Browse results and export as needed

  Option 2: Run from source
    1. Install Python 3.8+ from python.org
    2. Install dependencies: pip install flask
    3. Run: python app.py
    4. Open http://localhost:5000 in your browser

BUILDING FROM SOURCE
--------------------
  1. Install Python 3.8+
  2. Install dependencies:
     pip install flask pyinstaller
  3. Build executable:
     pyinstaller --onefile --name BrowserArtifactExtractor app.py
  4. Find the .exe in the dist/ folder

USAGE TIPS
----------
  - Close your browsers before extraction for best results
  - Run as Administrator if you encounter permission errors
  - The tool only READS data - it never modifies browser files
  - All processing happens locally - no data leaves your computer

FILE STRUCTURE
--------------
  BrowserArtifactExtractor.exe   - Main application
  architecture.md                - System architecture documentation
  memory.md                      - Memory management documentation
  state.md                       - Application state documentation
  todo.txt                       - Development task list
  readme.txt                     - This file

SECURITY & PRIVACY
------------------
  - This tool only reads browser data, it never writes or modifies anything
  - All processing happens locally on your machine
  - No data is sent over the network
  - Temporary database copies are deleted after extraction
  - The web server only listens on localhost (127.0.0.1)

TROUBLESHOOTING
---------------
  Q: Browser not detected?
  A: Make sure the browser has been used at least once and has a profile.

  Q: Permission denied error?
  A: Try running as Administrator. Some browser files require elevated access.

  Q: Application won't start?
  A: Check that port 5000 is not in use by another application.

  Q: Extraction is slow?
  A: This is normal for large browser histories. Wait for the progress bar.

LICENSE
-------
  This software is provided as-is for educational and personal use.

SUPPORT
-------
  For issues or feedback, please refer to the project repository.
