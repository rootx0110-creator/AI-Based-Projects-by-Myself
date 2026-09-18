# Assessment Methodology

This document explains how the checker evaluates rules, how comparisons work,
and how the compliance score is computed.

## 1. Rule anatomy

Every rule is a `Rule` dataclass (`hardening_checker/core/models.py`):

| Field | Purpose |
|---|---|
| `rule_id` | Stable ID (`HC-WIN-0101`), unique across the catalog |
| `title` / `description` | Human-readable summary shown in UI/reports |
| `severity` | `critical` (10) · `high` (6) · `medium` (3) · `low` (1) · `info` (0) |
| `profile` | CIS-style `level_1` or `level_2` |
| `category` | Grouping for the dashboard bars and report breakdown |
| `check_spec` | Machine-readable probe definition (below) |
| `remediation` | Summary, ordered steps, and a suggested (never executed) script |
| `rationale` / `audit_hint` | "Why this matters" and "how it's audited" |
| `requires_admin` | Rules skipped (not failed) without elevation |
| `manual` | Documentation-only checks; produce `MANUAL` results |

## 2. Check kinds (all read-only)

| `check_spec.kind` | Probe | Observed value |
|---|---|---|
| `registry` | `winreg.OpenKey` + `QueryValueEx` (`KEY_READ`, WOW64_64) | The value's data, or `None` if absent |
| `registry_key` | `winreg.OpenKey` existence test | `bool` |
| `command` | Read-only command (e.g. `net accounts`) | stdout/stderr, optionally JSON-parsed |
| `powershell` | `powershell -NoProfile -NonInteractive -Command` | Text, or coerced via `as_bool` / `as_int` / `as_float` |
| `service` | `Get-Service` / `systemctl is-active` | State string, `None` if unknown service |
| `file_exists` | `os.path.exists` | `bool` |
| `file_content` | Read text file, apply regex | Matched text or whole file |
| `package` | Platform package probe | `True/False/None` |

## 3. Expected-value semantics

`expected_kind` defines the comparison against the observed value:

| Kind | Pass condition |
|---|---|
| `exact` | Normalized equality (string-trimmed; numeric-tolerant) |
| `equals_bool` | Truthiness match (`1/true/yes/enabled/on`) |
| `regex` | Case-insensitive `re.search` |
| `in` | Substring (case-insensitive) |
| `not_contains` | Substring absent |
| `one_of` | Observed in `options` list |
| `min` / `max` | Numeric `>=` / `<=` (both sides coerced to float) |
| `exists` | Observed truthy |
| `not_exists` | Observed `None`/empty |

Special flags:

- `allow_missing: true` — a missing target (registry value not set, file absent)
  maps to **`NOT_APPLICABLE`** instead of fail. Used when absence itself is
  compliant (e.g. `SMB1` value removed on hardened hosts).
- `fail_message` — custom message attached to a failing comparison.

## 4. Result statuses

| Status | Meaning | Scored? |
|---|---|---|
| `PASS` | Compliant | full weight |
| `FAIL` | Non-compliant | 0 |
| `ERROR` | Probe could not run | half weight |
| `NOT_APPLICABLE` | Target absent, `allow_missing` | excluded |
| `SKIPPED` | Needs elevation / filtered out | excluded |
| `MANUAL` | Human-verification placeholder | excluded |

## 5. Scoring

```
applicable = Σ weight(rule)   for every scored result
achieved   = Σ weight(rule)   for PASS  +  0.5 × weight  for ERROR

score      = achieved / applicable × 100        (clamped 0..100)
```

Grades: `A+ ≥95 · A ≥90 · B ≥80 · C ≥70 · D ≥60 · E ≥50 · F <50`

Rationale for the design choices:

- **Severity weighting** mirrors real-world risk: a failed critical control
  (e.g. LSA unprotected) hurts far more than a stale screensaver timeout.
- **Errors at half weight** avoid punishing hosts for tool limitations while
  still reflecting uncertainty in the score.
- **Excluded statuses** keep the denominator honest: a non-elevated scan on a
  workstation is not graded down for checks it cannot see.

## 6. Benchmarks mapping

Rule IDs (`HC-…`) are independent of any single vendor catalog, but each rule
carries a `refs` list pointing at the equivalent CIS Microsoft Windows / Linux
recommendation (e.g. `CIS 2.3.17.1 (L1)`), so mappings can be produced for
GRC tooling. Profiles follow the same L1/L2 semantics: L2 scans include all L1
rules plus the stricter L2 set.

## 7. Determinism & testing

Platform inspection is isolated behind `PlatformContext`. The test suite swaps
in a `FakeContext` with canned registry/file/service/command responses, which
makes scans fully deterministic and CI-safe. Regression tests assert exact
scores for crafted result sets (100 % pass, mixed, half-weight error, N/A
exclusion).
