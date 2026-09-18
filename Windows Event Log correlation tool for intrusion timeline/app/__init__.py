"""Windows Event Log Correlation Tool — application package.

Modules:
  models      - dataclasses: EventRecord, Alert, Rule, AnalysisResult
  parser      - wevtutil ingestion (live + .evtx) -> EventRecord
  rules       - MITRE ATT&CK detection rules
  correlator  - rule runner, kill-chain phases, incident chains
  report      - single-file HTML report generator
  gui         - tkinter-based dark UI
"""
__version__ = "1.0.0"
__title__ = "Windows Event Log Correlation Tool"