=================================================================
  LLM-POWERED PHISHING EMAIL CLASSIFIER
=================================================================

A sleek, dark-themed web application that analyzes emails and
classifies them as SAFE, SUSPICIOUS, or PHISHING using a hybrid
engine: deep rule-based feature analysis + optional integration
with an LLM (OpenAI API or any OpenAI-compatible endpoint such as
Ollama / LM Studio) for advanced reasoning.

FEATURES
--------
  * Paste an email (raw text or FORMAT/EML) and get an instant verdict
  * Hybrid scoring engine:
      - 25+ heuristic signals (URLs, suspicious keywords, spoofed
        sender tricks, brand impersonation, credential bait, ...)
      - Optional LLM deep-dive analysis that explains the verdict
  * Beautiful glassmorphism dark UI with animated live classification
  * Downloadable HTML security reports (self-contained, shareable)
  * PDF report templates reserved for future work
  * Simple single-file local FLASK server - no database required
  * Can be packaged into a standalone executable (see BUILD)

QUICK START (web app)
---------------------
  1) Install dependencies:
       pip install -r requirements.txt
  2) Run:
       python app.py
  3) Open http://127.0.0.1:5000 in your browser.

  (Optional) Add LLM superpowers: create a file named
  "config.ini" in this folder, or use LLM settings panel in UI,
  then restart. See LLM CONFIG below.

LLM CONFIG
----------
  Create config.ini:
       [llm]
       enabled = 1
       api_base = https://api.openai.com/v1
       api_key  = sk-your-key
       model    = gpt-4o-mini
       timeout  = 30

  For a local Ollama:
       [llm]
       enabled = 1
       api_base = http://127.0.0.1:11434/v1
       api_key  = ollama
       model    = llama3.1

  When an LLM is configured, every scan also runs an LLM deep-dive
  pass whose verdict merges with the heuristic score. The LLM result
  is cached per content-hash so repeats are free.

BUILD STANDALONE EXE
--------------------
  Windows:  .\build_exe.ps1
  or manually:
       pip install pyinstaller
       pyinstaller --noconfirm --clean --onefile --windowed ^
           --name "PhishGuard" ^
           --add-data "templates;templates" ^
           --add-data "static;static" ^
           app.py

  Output: dist\PhishGuard.exe  (double-click to launch, browser
  opens automatically at 127.0.0.1:5000).

PROJECT FILES
-------------
  app.py              Flask application entry point
  classifier/         Classification engine (heuristics + LLM)
  report/             HTML report generator
  templates/          UI templates
  static/             CSS / JS / assets
  requirements.txt    Python dependencies
  build_exe.ps1       One-command executable build (Windows)
  architecture.md     Design documentation
  memory.md           Project memory / session notes
  state.md            Current development state
  todo.txt            Task backlog
  config.ini          Optional LLM settings (not required)

SECURITY NOTE
-------------
  This tool is for educational and defensive security analysis of
  messages you are authorized to inspect. Never submit credentials,
  secrets, or highly sensitive business emails to third-party LLM
  endpoints unless you trust the endpoint and network path.