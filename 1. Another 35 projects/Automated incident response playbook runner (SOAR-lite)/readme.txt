================================================================================
 SOAR-Lite - Automated Incident Response Playbook Runner
================================================================================

A lightweight SOAR (Security Orchestration, Automation and Response) platform
that automates incident response by executing structured playbooks against a
set of simulated security integrations.

WEB APPLICATION
--------------------------------------------------------------------------------
The product ships as a self-contained Flask web application. The same code can
be packaged into a standalone Windows EXE (see "Packaging as an EXE").

REQUIREMENTS
--------------------------------------------------------------------------------
  * Python 3.10+        (tested on 3.14)
  * Flask 3.x
  * No database required - runtime state persists to local JSON files

INSTALL
--------------------------------------------------------------------------------
  pip install -r requirements.txt

RUN
--------------------------------------------------------------------------------
  python app.py

  Then open:  http://127.0.0.1:5000

  Default credentials are not required; the app runs in single-analyst mode.
  Demo data (5 sample incidents, executions, and 5 playbooks) is seeded on
  first launch.

QUICK TOUR
--------------------------------------------------------------------------------
  Dashboard       Live KPI cards, charts, active executions, recent incidents.
  Incidents       Triage queue - create, assign a playbook, track lifecycle.
  Incident detail Playbook execution timeline with per-step results and IOCs.
  Playbooks       Library of automation playbooks (view / edit JSON).
  Executions      Historical run log with step-by-step status.
  Settings        Integration health, risk scoring rule tuning, data reset.

  Every incident can export an executive HTML report (File > needs a button ->
  "Download HTML Report" on the incident page). Reports are standalone HTML
  files that can be emailed, printed, or archived.

PLAYBOOKS
--------------------------------------------------------------------------------
  Playbooks live in /playbooks as JSON with a structured step grammar:

    step kinds:
      title         - section heading
      task          - manual analyst instruction (still recorded)
      integration   - automated adapter call (SIEM, TI, sandbox, EDR, etc.)
      condition     - branch on a previous step result
      delay         - wait N seconds

  Example (phishing playbook, abbreviated):
    {
      "id": "pb_phishing",
      "name": "Phishing Investigation",
      "steps": [
        {"kind": "title", "text": "Triage"},
        {"kind": "integration", "action": "ti.url_reputation", "params": {"value": "{{ioc.url}}"}, "on": [{"result": "malicious", "next": "block_domain"}]}
      ]
    }

  Templates may reference incident context via {{incident.*}} and IOC values
  collected during triage.

AUTOMATION / SIMULATED INTEGRATIONS
--------------------------------------------------------------------------------
  The execution engine calls adapters that simulate real tools so the whole IR
  lifecycle can be demoed offline:

    SIEM search          -> query correlation event log
    Threat Intelligence  -> reputation lookup (scored)
    Sandbox              -> dynamic file analysis
    EDR                  -> endpoint isolation / quarantine
    Firewall             -> IP blacklist
    DNS sinkhole         -> domain sinkhole
    Email gateway        -> message trace / mail quarantine
    Ticketing            -> create / update ticket

  Each integration has a health status, configurable latency and a failure
  rate so you can also demo error handling and analyst override steps.

STATE & CONFIG
--------------------------------------------------------------------------------
  data/                 runtime store (incidents, executions, IOCs, settings);
                        gitignored, recreated on first run.
  playbooks/            playbook JSON definitions (safe to edit; hot reloaded).
  settings.json         (in data/) risk scores and integration toggles.

PROJECT FILES
--------------------------------------------------------------------------------
  readme.txt            this file
  architecture.md       system architecture and engine design
  memory.md             persistent memory / context for the IR team
  state.md              state model and persistence semantics
  todo.txt              development roadmap
  app.py                Flask entry point + REST API
  soar_lite/            core engine package
  static/               CSS / JS / icons
  templates/            HTML views (Jinja2)
  playbooks/            playbook definitions
  data/                 runtime state (generated)

PACKAGING AS AN EXE
--------------------------------------------------------------------------------
  Two supported routes:

    1. PyInstaller (single-file EXE, opens the browser automatically):
         pip install pyinstaller
         .\build_exe.ps1            (or `pyinstaller soar_lite_server.spec`)

    2. Embedded browser via the optional `webview` route (see build_exe.ps1
       comments) for a native-window feel.

  The EXE is fully self-contained: it runs its own server on 127.0.0.1 and
  serves the same UI.

SECURITY NOTES
--------------------------------------------------------------------------------
  * This is a SOC demo / trainer. Integrations are simulated - they do not
    touch real infrastructure.
  * Multi-user auth, LDAP/SSO, TLS and audit-grade logging are roadmap items
    (see todo.txt).

================================================================================
 (c) SOAR-Lite Project - build with <3 for blue teams everywhere.
================================================================================