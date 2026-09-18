# Usage Manual

## GUI walkthrough

Launch: `HardeningChecker.exe` (or `python run.py`).

### 1. Dashboard
The landing page. Empty until your first scan, then shows:

- **Score gauge** — arc gauge with the weighted score and letter grade
- **Stat cards** — Total, Passed, Failed, Errors, N/A + Skipped, Manual
- **Donut** — result-status mix with centered total
- **Category bars** — pass rate per category (green ≥80 %, yellow ≥50 %, red below)
- **Scan meta strip** — scan ID, host, OS, profile, timestamps

### 2. Run Scan
- **Benchmark profile** — `Level 1` (essential) or `Level 2` (includes L1 + stricter L2 rules)
- **Include informational checks** — documentation-only rules
- **Run manual-review placeholders** — no-op checks that surface as `MANUAL`
- Press **▶ Start scan**. Progress bar tracks the current rule ID. Typical
  duration 30–120 s (registry checks are instant; PowerShell probes take 1–3 s).

### 3. Findings
- Filter by **severity**, **status**, and **free-text search** (rule id, title, message, category)
- Click any row → detail pane shows description, rationale, how it's audited,
  result message, raw evidence, and (for failures) remediation guidance
- Keyboard: `F5` re-scan · `Ctrl+1..5` switch pages · `Ctrl+Q` quit

### 4. Reports
Requires a completed scan. All exports include the **full** result set:

| Button | Output |
|---|---|
| **Generate HTML report** | Self-contained dark-themed report with working filters and evidence sections; opens in your browser |
| **Generate PDF report** | Print-ready paginated document: cover metadata, score panel, severity table, category breakdown, per-finding blocks with remediation |
| **Export JSON** | Complete machine-readable scan (schema below) |
| **Export CSV** | Flat one-row-per-check table for spreadsheets/GRC import |

### 5. About
Safety model, data-handling notes, version.

## CLI reference

```
HardeningChecker.exe --cli <command> [options]
python run.py --cli <command> [options]
```

### `scan`

| Option | Description |
|---|---|
| `--profile l1\|l2` | Benchmark profile (default `l1`) |
| `--json PATH` | Write JSON results |
| `--html PATH` | Write HTML report |
| `--pdf PATH` | Write PDF report |
| `--no-manual` | Exclude manual-review rules |
| `--no-info` | Exclude informational rules |
| `--quiet` | Suppress the progress bar |

Exit codes: `0` compliant · `1` failures/errors · `2` tool error · `130` aborted.

Examples:

```bash
# nightly compliance gate (CI-friendly)
python run.py --cli scan --profile l2 --json out.json --quiet
echo exit code: $?     # 1 means drift detected

# full reporting bundle
python run.py --cli scan --html report.html --pdf report.pdf --json data.json
```

### `rules`

List the rule catalog for the current platform:

```bash
python run.py --cli rules
python run.py --cli rules --profile l1
```

## JSON schema (abridged)

```jsonc
{
  "scan_id": "6FA0F48B5213",
  "started_at": "2026-09-15T20:05:11Z",
  "finished_at": "2026-09-15T20:05:48Z",
  "profile": "level_1",
  "score": 32.9,
  "grade": "F",
  "platform": {
    "system": "Windows", "os_name": "Windows", "os_version": "11",
    "build": "10.0.26100", "arch": "AMD64", "hostname": "BABLU-PC",
    "is_admin": false, "domain_joined": false, "ip_addresses": ["192.168.1.20"]
  },
  "summary": { "total": 45, "passed": 11, "failed": 21, "errors": 0,
                "not_applicable": 4, "skipped": 9, "manual": 0 },
  "results": [
    {
      "rule_id": "HC-WIN-0101",
      "title": "UAC: Admin Approval Mode for built-in Administrator",
      "status": "pass",              // pass|fail|error|not_applicable|skipped|manual
      "severity": "critical",
      "profile": "level_1",
      "category": "User Account Control",
      "message": "Compliant.",
      "observed": 1, "expected": 1,
      "duration_ms": 0.9,
      "evidence": [ { "source": "registry",
                      "detail": "HKLM\\...\\FilterAdministratorToken",
                      "raw": "1", "truncated": false } ]
    }
  ]
}
```

## Scheduled compliance scans (Task Scheduler)

```bat
:: daily 06:00 JSON snapshot for drift tracking
schtasks /create /tn "HardeningScan" /sc daily /st 06:00 /rl HIGHEST ^
  /tr "\"C:\Tools\HardeningChecker.exe\" --cli scan --profile l2 --quiet --json \"C:\Logs\hc-%COMPUTERNAME%.json\""
```

Merge nightly JSONs in Power BI / Excel / your GRC platform to trend the score
over time. Exit code `1` on any drift makes alerting trivial.

## Interpreting results

- **SKIPPED** — needs elevation; re-run elevated to include
- **ERROR** — probe could not run; read the message (missing tool, access denied)
- **NOT_APPLICABLE** — target absent, which is compliant for that rule
- **MANUAL** — needs human verification; excluded from scoring

If a finding looks wrong for your environment (e.g. domain policy overrides a
local value), note that the tool audits the *effective local configuration* —
domain GPO results are what the registry/OS reports at scan time.
