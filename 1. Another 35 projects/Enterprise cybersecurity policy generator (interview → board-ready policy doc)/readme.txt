==================================================================
 ENTERPRISE CYBERSECURITY POLICY GENERATOR
 Interview --> Board-Ready Policy Document
==================================================================

WHAT IT IS
------------------------------------------------------------
A tool that walks a company's stakeholders through a guided
"interview" of questions about the business, industry, risk
appetite and current security posture, then automatically drafts
a polished, board-ready enterprise cybersecurity policy document.

The output is a formal, multi-chapter policy document with:

  * Executive summary & board context
  * Governance, roles and accountability
  * Risk taxonomy and tiering
  * Policy chapters per security domain
  * Compliance & framework mapping (NIST CSF 2.0, ISO/IEC 27001,
    SOC 2, GDPR, PCI-DSS, NIS2, HIPAA, SOX...)
  * Third-party / supply-chain controls
  * Incident response & business continuity posture
  * KPIs / metrics to report to the board
  * Implementation roadmap (0-90-180-365 days)
  * Formal sign-off / approval block and document version control

No two generated documents look the same: the policy text,
tone, gap analysis and controls adapt to the answers given.

HOW TO RUN
------------------------------------------------------------
OPTION A - Browser (recommended for development):
  1. Double-click index.html  --or--
  2. python -m http.server 8000   then open http://localhost:8000

OPTION B - Windows EXE:
  Run:  .\build_exe.ps1
  This builds a standalone dist\CyberPolicyGenerator.exe using
  pywebview (native window wrapping the SAME index.html) +
  PyInstaller. Works on machines without Python/Node installed.

DOWNLOADS
------------------------------------------------------------
Inside the app use:
  * "Download HTML report" -> self-contained .html policy document
    (printable, opens in any browser)
  * "Print / Save as PDF"  -> print dialog of the report preview
    (choose "Save as PDF" as the destination)

FILES
------------------------------------------------------------
  index.html        The entire application (interview UI +
                    policy engine + report preview). No server,
                    no build step, runs offline.
  build_exe.ps1     Builds the standalone Windows EXE.
  run_app.py        pywebview wrapper used to produce the EXE
                    (and for a native desktop window). Not needed
                    for the browser version.
  architecture.md   Design, data-flow and extension notes.
  state.md          Feature / release state and known limitations.
  memory.md         Session memory: decisions and history tracking.
  todo.txt          Backlog and roadmap.
  readme.txt        This file.

DESIGN PRINCIPLES
------------------------------------------------------------
  * Zero dependencies in the browser build (vanilla JS).
  * Policy text is assembled from parameterised expert templates
    using the officer-like "risk --> control --> metric" pattern.
  * Material is clearly structured for a security-conscious but
    non-technical board audience (layered language levels).
  * Every generated policy is fully customizable before download.
==================================================================