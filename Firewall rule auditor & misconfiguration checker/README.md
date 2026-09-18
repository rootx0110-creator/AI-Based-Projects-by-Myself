# FRAMC — Firewall Rule Auditor & Misconfiguration Checker

Audit firewall rule-sets for shadowing, ordering overrides, world-open permits,
duplicates and other misconfigurations — and get a graded security posture.

Runs as a **web app** (Flask) and can be packaged as a **standalone Windows EXE**.

## Quick start

```bash
pip install -r requirements.txt
python run.py                  # → http://127.0.0.1:8765 (opens browser)
```

1. Open the **Analyze** tab.
2. Pick a vendor format (or let it auto-guess) and paste / drag a config.
3. Hit **Run Analysis** — results appear on the Dashboard, Rules, Findings and Report tabs.

Or audit headlessly:

```bash
python backend/cli.py audit samples/iptables.txt --format iptables --json out.json
python backend/cli.py audit samples --all-formats                 # sanity sweep
python -m unittest discover -s backend/tests -p "test_*.py"        # tests
```

## Build a Windows EXE

```bash
pip install pyinstaller
python build_exe.py
dist\FRAMC\FRAMC.exe             # standalone; opens localhost UI
```

## Supported formats

iptables/iptables-save · Cisco ASA access-lists · FortiGate config · pfSense config.xml ·
Windows/netsh advfirewall · Palo Alto `set rulebase security` · plain tables.

## Documentation

- `architecture.md` — design, components, detection suite, scoring, packaging.
- `state.md` — state model and invariants (backend, UI, analysis).
- `memory.md` — decision log, golden checks, how to extend parsers/detectors.

## Engine at a glance

```
config ─► parsers ─► canonical rules ─► detectors ─► scoring ─► report
              │                            │              │
          warnings                  findings        posture 0–100 + grade
```

Detected misconfigurations include **shadowed rules**, **ALLOW-overrides-DENY**,
**ANY/ANY world-open**, **sensitive port exposure**, **duplicates**, **missing
default-deny**, **invalid CIDR**, **port/protocol mismatch**, non-logged allows.

## Layout

```
backend/          Flask API + pure analysis engine (engine/)
frontend/         SPA (index.html, static/css, static/js, vendor/chart.js)
samples/          demo configs (iptables, ASA, FortiGate, pfSense, Windows, PA, plain)
architecture.md   system design
state.md          state model & invariants
memory.md         decisions & operational memory
```