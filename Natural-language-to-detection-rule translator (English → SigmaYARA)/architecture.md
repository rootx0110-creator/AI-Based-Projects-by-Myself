# Architecture — NL2Rule Translator

## Overview

A Flask single-page application that converts English descriptions of
malicious activity into detection rules. The translation engine is fully
local, deterministic, and self-contained (no external model / network
calls). The same codebase ships as a web app (Flask dev server) and as a
standalone Windows EXE (PyInstaller onefile).

```
browser UI (templates/ + static/)
        |
        | POST /api/translate          POST /api/report
        v                                     v
  engine/translator.py            engine/report.py (self-contained HTML)
        |
        +----> entities.py   (regex artifact extraction)
        +----> concepts.py   (NL intent detection + MITRE scoring)
        +----> sigma.py      (Sigma YAML builder)
        +----> yara.py       (YARA builder)
        +----> lexicon.py    (vocabulary / concept / technique data)
```

## Modules

### engine/lexicon.py
Pure data. Contains:
- `KNOWN_PROCESSES` — well-known tooling/LOLBins, each with display name,
  attack tactic and MITRE technique id (powershell->T1059.001, mimikatz->
  T1003.001, ...).
- `DETECTION_CONCEPTS` — concept dictionary. Every concept defines the
  trigger words, preferred Sigma logsource, selection field names,
  MITRE technique list and default severity.
- `MITRE_NAMES` — technique id -> human name for rendering.
- `LOGSOURCE_PRESETS` — category/product mappings per concept.

### engine/entities.py
Regex-backed extractor (`extract_entities`). Returns an `EntitySet` that
dedups values into categories: ip, domain, url, hash_sha256/sha1/md5,
file_path, process, port, registry_key, user, mutex, pipe, command,
scheduled_task, event_id, email, mitre_id, string.

### engine/concepts.py
`detect_concepts(text, entities)` scores wording against the concept
dictionary and enriches with entity knowledge (a detected mimikatz.exe
forces the credential-dumping concept, an IP forces network context).
Produces a `ConceptHits` object holding concept hits plus MITRE technique
scoring. Also resolves the final logsource + severity and a rough
confidence heuristic.

### engine/sigma.py
`build_sigma(...)` assembles a standard Sigma rule:
- `selection_img` — `Image|endswith` on detected processes
- `selection_cmd` — `CommandLine|contains` keywords per concept
- `selection_net` / `selection_dns` / `selection_http` — IP/domain/URL
- `selection_file` / `selection_reg` — file & registry targets
- condition = `1 of (...)` over the emitted selections
Rule metadata: uuid id, status experimental, MITRE tags, level.

### engine/yara.py
`build_yara(...)` maps the same concepts + entities to a YARA rule with
meta (author/description/mitre/date/hash) and a ranked list of `$sN`
strings with ascii/wide modifiers. Condition = `any of them`.

### engine/report.py
`build_report_html(result)` — renders the whole translation into a single
self-contained dark-theme HTML document (inline CSS, no external deps):
stat cards, extracted-artifact chips, concept table, MITRE mapping,
syntax-tinted Sigma/YARA dumps.

### engine/translator.py
Orchestrator. `translate(text)` -> JSON-ready dict consumed by both the
UI and the report generator.

## API surface

| Route                 | Method | Purpose                                |
|-----------------------|--------|----------------------------------------|
| `/`                   | GET    | Translator UI                          |
| `/examples`           | GET    | Scenario library page                  |
| `/about`              | GET    | Pipeline explainer                     |
| `/api/translate`      | POST   | Full translation (JSON)                |
| `/api/report`         | POST   | Download self-contained HTML report    |
| `/api/examples`       | GET    | Example list (JSON)                    |
| `/api/examples-by-index` | GET | Single example by index              |
| `/api/health`         | GET    | Liveness / version check               |

## Packaging (EXE)

`build_exe.ps1` runs PyInstaller `--onefile --console` over
`exe_entry.py`, embedding `templates/` and `static/` as data. At runtime
the entry points boots Flask on a free localhost port and opens the
default browser. `app.py` resolves `BASE_DIR` from `__file__`, which
PyInstaller rewrites to the extraction dir so bundled templates/static
are found automatically.

## Tests

```
python tests\test_app.py     # Flask route + API + report smoke tests
python tests\smoke.py        # engine-level translation smoke tests
```