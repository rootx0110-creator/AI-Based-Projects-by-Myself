# state.md — application state snapshot

Snapshot generated for the current build. The GUI holds its state in the
`config` dictionary (`app.config`) and persists a small user profile to
`%LOCALAPPDATA%\MSFLabStudio\profile.json` when "Remember settings" is on.

## Editor defaults

| Key               | Default value                                  |
|-------------------|------------------------------------------------|
| template_id       | cmd-injection                                  |
| template_label    | Command Injection (RCE via /exec)              |
| module_class      | exploit                                        |
| module_name       | exploit/linux/http/vulnlab_exec                |
| target_host       | 127.0.0.1                                      |
| target_port       | 8080                                           |
| target_uri        | /exec                                          |
| cli_name          | VulnLab Exec Command Injection (Lab Only)      |
| author            | MSF Lab Author                                 |
| reference         | CVE-2026-LAB-0001                              |
| payload_name      | linux/x64/meterpreter/reverse_tcp              |
| payload_arch      | x64                                            |
| badchars          | \x00                                           |
| default_rank      | ExcellentRanking                               |
| license           | MSF_LICENSE                                    |
| disclosure_date   | 2026-09-19                                     |

Templates shipped in `VULN_TEMPLATES` (module_builder.py):

| template_id    | module class        | module                     | endpoint  | CVE            |
|----------------|---------------------|----------------------------|-----------|----------------|
| cmd-injection  | exploit             | exploit/linux/http/vulnlab_exec | /exec | 2026-LAB-0001  |
| path-traversal | auxiliary/scanner   | auxiliary/scanner/http/vulnlab_traversal | /file | 2026-LAB-0002 |
| config-leak    | auxiliary/scanner   | auxiliary/scanner/http/vulnlab_backup    | /backup    | 2026-LAB-0003 |

## Live-test state

| Field             | Meaning                                              |
|-------------------|------------------------------------------------------|
| reachable         | TCP connect success to RHOSTS:RPORT                   |
| health_code       | HTTP status from `GET /health`                        |
| banner            | First header line of the probe response               |
| vulnlab           | `VulnLab-Service v1.0` marker found in body           |
| check.state       | Vulnerable / Safe / Unknown                           |
| check.detail      | Human-readable reason for the verdict                 |
| detect.summary    | Vulnerable / Lab identified, no vuln matched / ...    |
| detect.open_vulns | sublist of template ids that matched the live box      |
| last_scan         | list of open TCP ports from the common-port sweep      |

Per-template checks live on `LabServiceProbe`:
`check_cmd_injection`, `check_path_traversal`, `check_config_leak`, and
`detect_all()` runs all of them in one pass. Each returns `{detected,
detail, evidence, ts}`.

Default verdict when nothing was scanned: `Unknown` ("Not tested yet" badge).

## Report state

- `report_id`: random 8-hex-char id per generated report.
- `generated_at`: local timestamp of report build.
- HTML report contains: verdict banner, auto-detection table, module overview,
  activity timeline, port-scan results, Ruby source block, usage/safety sheet,
  footer. Inline CSS, no external assets.
- JSON twin via `LabHtmlReport.to_json()`: machine-readable mirror including
  module source; downloadable from the Report section.

## Persistence

- Profile: `%LOCALAPPDATA%\MSFLabStudio\profile.json` (host, port, uri,
  template, payload, rank, author, remember flag).
- Saved on Apply / Reset / window close when "Remember settings" is checked.

## Environment

- OS: Windows (build host).
- Python: 3.14.x, tkinter 9.0 present.
- PyInstaller: 6.22.3.
- Build output: `dist/MSF-Lab-Module-Studio.exe` (onefile, windowed).

## Diagnostics / self-test (in the exe)

- Errors: logged to `%TEMP%\msf_lab_studio_error.log` (sys.excepthook,
  tkinter callback exceptions, worker-thread failures, profile save/load).
- Self-test: run with env `MSF_STUDIO_SELFTEST=1`; the frozen exe exercises
  its own full workflow headlessly and writes results to
  `%TEMP%\msf_studio_selftest.out` (plus a `.done` marker file). Currently 10
  checks: section switch, module gen, HTML render/write, template switch to
  scanner, JSON write+parse, offline probe, offline detect_all, offline port
  scan, threaded probe.
- Keyboard: `Alt+1..4` switches sections without using the mouse.