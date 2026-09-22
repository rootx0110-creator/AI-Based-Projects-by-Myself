===============================================================================
 STRIDEForge - Threat Modeling Automation Tool (STRIDE + DREAD)
 Generate STRIDE/DREAD threat models automatically from architecture diagrams.
===============================================================================

WHAT IT IS
----------
STRIDEForge is a self-contained web application (can also be built into a
single .exe) that lets you draw your system architecture as a diagram and
automatically produce a full threat model:

  * STRIDE  - Spoofing, Tampering, Repudiation, Information Disclosure,
              Denial of Service, Elevation of Privilege
  * DREAD   - Damage, Reproducibility, Exploitability, Affected Users,
              Discoverability  (each scored 1-10, max total 50)
  * Risk    - Low / Medium / High / Critical per threat
  * Report  - Downloadable standalone HTML report

FEATURES
--------
  * Visual Architecture Canvas
      - Drag-and-drop components (processes, data stores, external entities)
      - Draw data flows between elements
      - Draw trust boundaries / zones (internet, DMZ, internal, restricted)
      - Mark entry points, internet-facing elements, sensitive data (PII/PCI/PHI)
      - Toggle existing controls (authentication, encryption, logging,
        authorization, rate limiting) -> residual (post-control) risk
      - Upload your own diagram image as a tracing background
  * Enterprise rules engine
      - Component-level, data store-level, external-entity-level and
        data-flow-level threat templates
      - Type-aware rules for web apps, APIs, databases, caches, queues,
        identity providers, microservices and more
  * Interactive analysis view
      - Filter by STRIDE category, risk level, or free text
      - Live DREAD breakdown with editable-looking visual bars
      - Context notes explaining why scores were raised/lowered
  * One-click HTML report download (also viewable in-app)
  * Built-in sample architectures (E-commerce, Microservices, 3-Tier Legacy)
  * JSON import/export of your architecture model

REQUIREMENTS
------------
  * Python 3.9+  (tested on 3.14)
  * Flask  (pip install -r requirements.txt)

RUN AS WEB APP
--------------
  1) Install dependencies:
     pip install -r requirements.txt

  2) Start the app:
     python app.py
     or double-click run.bat

  3) Open your browser at:  http://127.0.0.1:1234

BUILD AS STANDALONE .EXE
------------------------
  1) Install build tools:
     pip install -r requirements.txt pyinstaller

  2) Run the build script:
     build_exe.bat
     (or: pyinstaller --onefile --name STRIDEForge ^
              --add-data "templates;templates" ^
              --add-data "static;static" app.py)

  3) The executable is created at:
     dist\STRIDEForge.exe
     Double-click it - it starts the local web server and opens your default
     browser automatically. Closing the console window stops the app.

QUICK START
-----------
  1. On the Dashboard click a sample card (e.g. "E-commerce Web App") - the
     diagram loads on the "Diagram" tab.
  2. Click "Analyze Risk" (top right).
  3. Review the generated STRIDE/DREAD analysis on the "Analysis" tab.
  4. Go to "Report" and click "Download HTML Report".
  5. To model your own system, use the canvas toolbar to drop components,
     connect data flows, draw trust boundaries and set properties on the
     right-hand panel, then analyze.

HOW SCORING WORKS
-----------------
  * Every element (process / data store / external entity / data flow) gets
    STRIDE threats generated from a rules engine keyed by element kind + type.
  * Each threat carries base DREAD scores (1-10 per factor).
  * Context modifiers adjust scores automatically:
      + Internet-facing   -> +exploitability, +discoverability, +affected users
      + PII/PCI/PHI       -> +damage
      + Crosses boundary  -> +damage, +affected users
      - Controls in place -> residual risk is LOWERED
        (authentication, strict authorization, encryption, audit logging,
         rate limiting)
  * DREAD total = Damage+Reproducibility+Exploitability+Affected+Discoverability.
  * Risk tiers: Low <18, Medium 18-29, High 30-39, Critical 40-50.

PROJECT FILES
-------------
  app.py              - Flask web server (entry point)
  threat_engine/      - rules.py (STRIDE/DREAD templates), analyzer.py,
                        report.py (HTML report generator)
  templates/          - index.html (UI)
  static/             - style.css, app.js
  samples/            - example architecture models (JSON)
  architecture.md     - technical design of the tool
  memory.md           - project memory / conventions / decisions
  state.md            - current state of the build
  todo.txt            - planned enhancements
===============================================================================