# Architecture — Mobile Device Forensic Workflow (MFW)

Android logical-acquisition lab toolkit with an eye-catching desktop UI and
self-contained HTML report output.

## 1. Purpose

A lab-workstation application that walks an examiner through the standard
logical-acquisition workflow for an Android device:

```
Case intake -> Device connection -> Logical extraction -> Artifact parsing
           -> Review (artifacts) -> HTML report download -> Audit trail
```

## 2. Technology Stack

| Layer      | Choice                          | Rationale                                        |
|------------|---------------------------------|--------------------------------------------------|
| Language   | Python 3.10+ (tested on 3.14)   | Rich stdlib (sqlite3, tarfile, zlib, hashlib)    |
| UI         | PySide6 (Qt 6, LGPL)            | Native desktop widgets, QSS theming, no browser  |
| Packaging  | PyInstaller `--onefile --windowed` | Single distributable `MobileForensicWorkflow.exe` |
| ADB        | External `adb.exe` (found on PATH / common SDK paths) | Real device I/O via subprocess |

No third-party runtime dependencies beyond PySide6. All parsing uses the
Python standard library.

## 3. Module Map

```
main.py                     Entry point: QApplication, global QSS, excepthook
mfw/
  __init__.py               App name / version constants
  theme.py                  Color palette + application-wide stylesheet (QSS)
  widgets.py                Reusable widgets: Card, StatCard, make_table, hline
  case_store.py             Case CRUD, persistence, SHA-256 evidence hashing,
                            chain-of-custody CSV, audit logs
  adb.py                    ADB wrapper: locate adb, devices, getprop, backup,
                            screencap, pm list packages
  parsers.py                Android .ab container unpack (zlib+tar), SQLite
                            parsers for calls / SMS / contacts, package lists
  demo.py                   Deterministic synthetic dataset (offline demo mode)
  extraction.py             Core extraction pipeline (device-independent logic;
                            used by both the UI worker thread and tests)
  report.py                 Self-contained HTML report generator
  main_window.py            Shell: sidebar navigation + header + QStackedWidget
  dashboard_view.py         KPI cards, recent cases, system status
  case_view.py              Case intake form + case table / activate
  extraction_view.py        Device list, method selector, QThread worker, log
  artifacts_view.py         Artifact browser (Calls/SMS/Contacts/Apps), search,
                            CSV export
  report_view.py            Report metadata, preview, Download HTML, open file
  audit_view.py             Global audit log viewer
```

## 4. Data Flow

1. **Case intake** — `CaseStore.create_case()` writes case metadata and creates
   the on-disk case folder (see §5). The case becomes the *active case*.
2. **Extraction** — `ExtractionView` runs `extraction.run_extraction()` inside a
   `QThread`. Depending on the selected method it either:
   - `adb_backup`  : `adb backup -noapk -noshared` for the contacts / telephony
     / settings providers; the `.ab` container is zlib-inflated and unpacked
     from tar; `contacts2.db` and `mmssms.db` are parsed with sqlite3.
   - `packages`    : `pm list packages` (third-party + system) saved as evidence
     and parsed into the Apps artifact set.
   - `screenshot`  : `adb exec-out screencap -p` saved as PNG evidence.
   - `demo`        : synthetic dataset (`demo.py`) so the workflow is fully
     demonstrable with no device attached.
3. **Evidence integrity** — every evidence file is hashed (SHA-256) via
   `CaseStore.log_evidence()`, which appends a row to the case's
   `chain_of_custody.csv` and the case audit trail.
4. **Artifacts** — parsed records are merged into `extracted/artifacts.json`
   keyed by type (`calls`, `sms`, `contacts`, `apps`).
5. **Reporting** — `report.build_html()` renders a fully self-contained HTML
   document (inline CSS, no external assets). `ReportView` offers preview,
   **Download Report** (save dialog; default location is the case `reports/`
   folder) and open-in-browser.
6. **Audit** — every significant action appends to `data/audit.log` (global)
   and `<case>/audit.txt` (per case).

## 5. Storage Layout (created at runtime)

```
data/
  state.json                Active case id
  cases_index.json          All case metadata (single source of truth)
  audit.log                 Global audit trail: "ts | case | event | detail"
  cases/<CASE_NUMBER>/
    metadata.json           Case record (mirrors index entry)
    audit.txt               Per-case audit trail
    chain_of_custody.csv    timestamp, case_number, item, sha256, method, examiner, note
    evidence/               Raw acquisition files (.ab, .png, .txt, .json)
    extracted/              Unpacked payload + artifacts.json
    reports/                Generated HTML reports
    exports/                CSV exports
```

`data/` resolves next to the executable when frozen (PyInstaller) and next to
the project root when running from source.

## 6. UI Map

Single `QMainWindow` shell:

- **Left sidebar** — navigation list (Dashboard, Case Manager, Extraction,
  Artifacts, Reports, Audit Log) over the app gradient background.
- **Header** — app title, ADB status chip, active-case chip.
- **Stack** — one page per navigation entry; each page implements
  `refresh()` so it re-reads the store when shown or when the active case
  changes.

Theme: deep indigo/violet gradient background with teal accent (`#00E5C3`),
violet secondary (`#8B7CF8`), translucent "glass" cards, gradient primary
buttons — deliberately not black/white.

## 7. Packaging

```
pyinstaller --noconfirm --clean --onefile --windowed --name MobileForensicWorkflow main.py
```

Output: `dist/MobileForensicWorkflow.exe`. The exe creates/uses `data/` in its
own folder, so it is portable to any lab workstation.

## 8. Extension Points

- New artifact types: add a parser in `parsers.py`, a key in
  `artifacts_view.ARTIFACT_COLUMNS`, and a section in `report.py`.
- New acquisition methods: add a branch in `extraction.py` and a radio option
  in `extraction_view.py`.
- Physical/advanced acquisitions (rooted images, ADB pull of full /data) can
  reuse the same evidence-hashing + CoC + report pipeline.

## 9. Forensic Integrity Notes

- Logical-only scope: the tool performs user-level acquisitions (adb backup /
  package inventory / screencap) appropriate for lab triage; no rooted device
  is modified.
- All writes are append-only logs; original evidence files are never edited
  after hashing.
- The report embeds SHA-256 digests and the chain-of-custody table so findings
  can be re-verified independently.
