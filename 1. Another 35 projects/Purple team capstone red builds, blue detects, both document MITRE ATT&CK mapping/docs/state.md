# State & limitations

## What is simulated (not real)

- Scheduled-task XML drops into `lab_target/tasks/` - real Task Scheduler is never touched.
- Run-key autostart is a `.reg` text file. PowerShell "runs" are log lines.
- The exfiltration channel is a loopback socket bound to an ephemeral port.
- No host, registry, service, firewall or remote host is modified.

## Known limitations

- Detection engine inspects the artifact index + files; it is a *simulator* of
  a SOC toolchain, not EDR/AV. No real runtime inspection.
- T1041 fidelity depends on entropy/base64 heuristics; a passive network sensor
  (Zeek/Suricata/NIDS) is recommended in a production lab.
- RULE-CHANGE (catch-all) intentionally detects broadly at low fidelity.
- Scores reset each exercise; archive `outputs/reports/*.html` for trend data.
