===========================================================================
  SentinelForge
  AI-assisted log anomaly detector — unsupervised ML on SIEM data
  Version 1.0.0
===========================================================================

WHAT IT IS
  A self-contained web application (also packageable as a Windows EXE) that
  detects anomalous events in raw SIEM / firewall / OS log feeds.
  It is UNSUPERVISED: no labels, no signatures, no training set. Every event
  is compared to the rest of the feed by a voting ensemble of detectors and
  surfaced as triage-style incident clusters with per-event explanations.

QUICK START
  1) Install dependencies:
       pip install -r requirements.txt
     (needs Python 3.10+; developed on 3.14)
  2) Run:
       python app.py
  3) Open your browser at:
       http://127.0.0.1:8600
  4) Drag & drop a log file — OR click "Get sample data" and use the sample
     feed — then press "Run anomaly detection".
  5) Download the findings as a standalone HTML report (top-right button).
     The report opens offline; it has no external dependencies.

BUILD AS A WINDOWS EXE (optional)
  Run:
       build_exe.bat
  which calls PyInstaller (pip install pyinstaller if missing). The result
  lands in dist\SentinelForge.exe — double-click to start the local server,
  then open http://127.0.0.1:8600.

ACCEPTED LOG FORMATS
  CSV / TSV, JSON array, JSONL, Syslog (RFC3164), CEF (ArcSight-style), and
  raw text lines. Format is detected from content, not file extension.
  Typical fields auto-mapped (any order, case-insensitive):
    timestamp / time / ts | src_ip / srcip / source_ip | dst_ip / destip ...
    src_port / dst_port | user / username | event_id / signature / category
    severity / priority / level | protocol / service | message / msg / text
    bytes / bytes_in / bytes_out | duration

WHAT THE ENSEMBLE DOES
  - Isolation Forest       isolates observations with few cuts
  - Local Outlier Factor   measures local density
  - One-Class SVM          boundary around the normal bulk
  - Nano Autoencoder       pure-numpy MLP; reconstruction error
  - Burst component        catches coordinated floods (brute force, DNS
                           flash, port fan-out) that point detectors miss
  Scores blend the detectors, reward incident-cluster size, and are capped
  per identity so one storm cannot drown the triage queue. Every flagged
  event ships with feature-level "why" explanations.

RESULT SURFACES
  - Summary metric cards (events, flags, incidents, rate, features, models)
  - Incident clusters grouped by identity (source / account)
  - Flagged-events table with per-event anomaly score and explanations
  - Detector vote tally
  - Standalone HTML report download (self-contained, same navy/gold theme)

WHO SHOULD USE IT
  Security analysts validating unlabelled flows, SOC onboarding demos,
  threat-hunters doing fast triage, trainers teaching unsupervised learning
  on security data. It is single-user and in-memory by design.

PROJECT LAYOUT
  app.py                 Flask entry point / API
  loganomaly/            ML package (ingestion, features, models, scoring,
                         report, sample_data)
  templates/ static/     UI
  architecture.md        system design & rationale
  memory.md              working notes / decisions
  state.md               current status snapshot
  todo.txt               task list
  report downloads are generated on demand (nothing stored)

LICENSE / ETHICS
  Demo/education use. Performance depends on data quality; always confirm
  detections with your own analysts before acting. No telemetry, no data
  leaves the machine.

===========================================================================