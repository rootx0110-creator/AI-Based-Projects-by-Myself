IMMERSIVE TRAINING ENVIRONMENT - 3D WALKTHROUGH INCIDENT RESPONSE SCENARIO
==========================================================================
Version 1.0   |   Offline training simulator   |   Data-center fire scenario

WHAT THIS IS
------------
A fully offline, browser-based 3D training simulator. You spawn inside a
modern data-center facility where a UPS bay has just caught fire. Your job is
to walk through the facility, follow the incident-response runbook shown in
the HUD, make the right calls, and bring the incident under control. Every
action is scored; when you finish you can download a branded HTML
after-action report of your run.

HOW TO RUN
----------
OPTION A - Just open the file (easiest):
    Double-click index.html. Open it in Chrome / Edge / Firefox.
    (Chrome/Edge also support the optional
     --allow-file-access-from-files flag if anything fails to start.)

OPTION B - Local web server (recommended):
    Windows PowerShell, from the project folder:
        python -m http.server 8000
    then open http://localhost:8000/

OPTION C - Desktop EXE (if built):
    Run "IRT_Incident_Simulator.exe" in the release folder.

CONTROLS
--------
    WASD / ZQSD  - move
    Mouse        - look around (click the screen to lock the mouse,
                   press ESC to release it)
    E / click    - interact with highlighted hotspots
    F            - toggle flashlight
    R            - quick focus back to the objective hint
    M            - toggle minimap
    ESC          - release mouse / pause menu
    Tab          - marker / objective details

PLAY TIP
--------
    Complete objectives in order. The correct first move is to DON the PP
    hanging in the entry lobby. Then verify and raise the alarm before going
    near the fire. Choose the correct extinguisher (look at hazard labels),
    isolate fuel and cut electrical power to the bay, then extinguish the
    fire and evacuate. Watch your health pip and avoid smoke.

REPORT & MEMORY
---------------
    On completion (or abort) a summary screen appears with a DOWNLOAD REPORT
    button. The report is a self-contained HTML file saved to your Downloads
    folder, timestamped, containing scores, runbook checklist, timeline and
    skill radar. Your profile and personal bests are kept on your machine in
    the browser's local storage - nothing is uploaded anywhere.

TROUBLESHOOTING
---------------
    * Black screen / missing world  -> make sure assets/three.min.js exists
      next to index.html.
    * High-DPI laptop blurry        -> browsers handle it; if odd, resize the
      window once.
    * Can't interact              -> you must be close to a hotspot and the
      objective must be active.

FILES
-----
    index.html                    entry point
    css/style.css                 UI styling
    js/*.js                       engine, player, world, scenario, audio,
                                  report, main
    assets/three.min.js           vendored WebGL library (offline)
    architecture.md               design documentation
    memory.md, state.md           persistence + simulation state specs
    todo.txt                      backlog

LICENSE
-------
    Free for training use. three.js (MIT) is vendored as-is.