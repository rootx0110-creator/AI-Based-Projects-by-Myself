# Endpoint Hardening & Compliance Checker

**Read-only CIS-style benchmark auditing for Windows endpoints** (Linux/macOS optional) with a modern desktop dashboard and professional **HTML + PDF** compliance reports.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![GUI](https://img.shields.io/badge/GUI-PySide6-41cd52) ![Tests](https://img.shields.io/badge/tests-26%20passing-brightgreen) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## ✨ What it does

| Capability | Details |
|---|---|
| 🔍 **Automated assessment** | 45+ Windows rules across 11 categories: Account Policies, UAC, LSA, BitLocker, Defender, Firewall, RDP, Audit Policy, Network (SMB/LLMNR/WPAD), Session Lock, Updates |
| 📊 **Modern dashboard** | Score gauge, pass/fail tiles, status donut, per-category pass-rate bars — dark fluent theme |
| 🧾 **Findings explorer** | Severity/status filters, live search, per-rule detail with rationale, evidence, and remediation guidance |
| 📄 **Professional reports** | Self-contained interactive **HTML**, print-ready **PDF** (ReportLab — no external binaries), plus **JSON/CSV** for GRC pipelines |
| 🖥️ **Two interfaces** | Full **PySide6 GUI** and a headless **CLI** with CI-friendly exit codes |
| 🔒 **Safe by design** | 100 % read-only: registry `KEY_READ` only, inspection-only commands, no services touched, remediation shown but never executed |
| 🧪 **Tested** | 26 unit + end-to-end tests, deterministic `FakeContext` — no OS calls in CI |

## 🚀 Quick start

### Prebuilt executable
```
dist\HardeningChecker.exe
```
Double-click to launch the GUI. Right-click → **Run as administrator** to unlock elevated checks (otherwise they are marked `SKIPPED`).

### From source
```bash
pip install -r requirements.txt
python run.py                 # GUI
python run.py --cli scan      # headless scan
```

### CLI examples
```bash
python run.py --cli scan --profile l1 --json out.json --html out.html --pdf out.pdf
python run.py --cli scan --profile l2 --no-info --quiet
python run.py --cli rules                      # list rules for this machine
```

**Exit codes:** `0` compliant · `1` failures found · `2` tool error — safe for CI/scheduled jobs.

## 🏗️ Build the .exe

```bash
pip install -r requirements.txt
python -m PyInstaller --clean packaging/hardening-checker.spec
# → dist/HardeningChecker.exe  (onefile, windowed, ~59 MB)
```

Helper scripts: `packaging\build_exe.cmd` or `bash packaging/build_exe.sh`.

## 🧮 Scoring model

Severity weights: `critical=10, high=6, medium=3, low=1, info=0`

```
score = achieved_weight / applicable_weight × 100
```

- **PASS** → full weight · **ERROR** → half weight (unknown ≠ penalized) · **FAIL** → 0
- `N/A`, `SKIPPED`, `MANUAL` excluded from the denominator

Grades: `A+ ≥95` · `A ≥90` · `B ≥80` · `C ≥70` · `D ≥60` · `E ≥50` · `F <50`

## 🔒 Safety model

- Registry access via `winreg` with **`KEY_READ` only** — nothing is ever written
- All commands are inspection-only (`net accounts`, `auditpol /get`, `Get-MpComputerStatus`, `Get-BitLockerVolume`, `sshd -T`, `sysctl -n`, …)
- No services started/stopped, no tasks scheduled, no policies modified
- Remediation snippets in reports are **text suggestions** — never executed
- All data stays local; nothing is transmitted

## 📁 Project layout

```
hardening_checker/
├── core/            models, platform contexts, evaluator, scanner, scoring
├── rules/           windows_rules · linux_rules · macos_rules
├── reporting/       Jinja2 HTML + ReportLab PDF generators, templates
├── gui/             PySide6 theme, custom widgets, main window, scan worker
├── cli.py           headless interface
└── __main__.py      python -m hardening_checker
packaging/           PyInstaller spec + build scripts
tests/               pytest suite (26 tests)
docs/                METHODOLOGY · BUILDING · SAFETY · USAGE
run.py               convenience launcher
README.txt           plain-text manual
```

## 🧪 Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

Covers the evaluator (registry/command/service/file checks, bool & numeric comparisons), scoring math, rule integrity (unique IDs, valid specs, ≥40 Windows rules), HTML/PDF rendering, CLI round-trip, and a full simulated scan.

## 📚 Documentation

- `README.txt` — plain-text manual (quick start, troubleshooting)
- `docs/METHODOLOGY.md` — check kinds, expected-value semantics, scoring math
- `docs/BUILDING.md` — dev setup, spec internals, code signing, cross-platform notes
- `docs/SAFETY.md` — the full read-only guarantees and threat model
- `docs/USAGE.md` — GUI walkthrough, CLI reference, JSON schema, scheduling

## ⚖️ License

MIT — see `LICENSE`. CIS Benchmark references are for mapping purposes only; this tool ships its own independent rule set.

---

*Generated with Codebuff 🤖*
