# Architecture - Wazuh/OSSEC Detection Rule Pack Studio

## 1. Purpose

A desktop engineering tool for authoring, curating, validating and distributing a
custom Wazuh/OSSEC rule pack that covers a **single, rehearsed attack chain**:

> **Web Initial Access -> Execution -> Persistence -> Privilege Escalation ->
> Credential Access -> Discovery -> Lateral Movement -> Command & Control ->
> Exfiltration** (targeting a Linux + Windows estate exposing a web application).

The tool is delivered as a standalone Windows GUI application (`.exe`) with
HTML report export capability.

## 2. High-level view

```
+---------------------------------------------------------------+
|                        Wazuh/OSSEC Rule Pack Studio            |
|                         (customtkinter GUI)                   |
+---------------------------------------------------------------+
   |                      |                     |               |
   v                      v                     v               v
+-----------+    +--------------+    +----------------+  +---------------+
| Dashboard |    | Rule Library |    | Attack Chain   |  | Reports       |
+-----------+    +--------------+    +----------------+  +---------------+
                                            |                    |
                                            v                    v
                                  +----------------+    +------------------+
                                  | Rule Builder   |    | HTML Report      |
                                  | + validation   |    | Generator        |
                                  +----------------+    +------------------+
                                            |                    |
                                            v                    v
                                  +----------------+    +------------------+
                                  | Rule pack core |    |  (exports)       |
                                  | (data model,   |    |  *.html, *.xml   |
                                  |  XML engine)   |    +------------------+
                                  +----------------+
```

## 3. Components

### 3.1 Rule pack core (`app/rules_core.py`)
- Data model: `Rule`, `AttackStage`, `RulePack`.
- Embedded library `LIBRARY_STAGES`, `LIBRARY_RULES` (26 rules across 11 stages).
- Persistence: pack saved as JSON at `data/rulepack.json` next to the executable.
- Validation:
  - unique rule ids within the pack,
  - level bounds (0-16) and reserved values,
  - well-formed rule XML (generated and re-parsed),
  - mandatory description and MITRE reference.

### 3.2 Rule Builder (`app/builder` logic in core)
Generates canonical Wazuh `local_rules.xml` fragments from structured fields
(decoder, match/regex/field conditions, `if_sid` parent, level, description, group).

### 3.3 HTML Report Generator (`app/report.py`)
Zero-dependency HTML output (embedded CSS + inline charts) for:
- **Full pack report**  - summary, severity distribution, XML listing per rule.
- **Coverage matrix**  - stage x rule table with MITRE ATT&CK mapping.
- **Severity report**  - group by level.
- **Single rule report** - one rule addressed in detail.

### 3.4 GUI layer (`app/ui/`)
MV-ish view layer on top of the core:
- `DashboardView`  - KPI cards, severity bar chart (Canvas), stage coverage.
- `LibraryView`    - searchable/filterable table + rule detail + XML export.
- `ChainView`      - attack-chain stage list with rule coverage.
- `BuilderView`    - form-based rule authoring with live XML preview.
- `ReportsView`    - report type selection, destination folder, generate + open.

## 4. Data flow

1. App start -> load pack (embedded library JSON -> `rulepack.json`).
2. User edits/adds rules via Builder; pack re-validated; persisted.
3. User generates report -> HTML written to `data/exports/` and opened in
   the default browser.
4. User exports the XML pack -> `local_rules.xml` written for deployment to
   Wazuh/OSSEC manager (`/var/ossec/etc/rules/`).

## 5. Exe packaging

- `requirements.txt` pinned packages (customtkinter, pyinstaller).
- Built with PyInstaller `--onefile --windowed --collect-data customtkinter`.
- Bundled resources are all embedded in Python modules -> no external assets
  are required at runtime.

## 6. Directories

| Path            | Description                                      |
|-----------------|--------------------------------------------------|
| `app/`          | Application sources                              |
| `app/ui/`       | GUI views                                        |
| `data/`         | Runtime state, pack JSON, exports (next to exe)  |
| `*.md`, `*.txt` | Engineering documentation & deliverables         |

## 7. Security notes

- Rules are detection expressions only; no data exfiltration or automation.
- HTML reports embed no remote resources (fully offline-safe).