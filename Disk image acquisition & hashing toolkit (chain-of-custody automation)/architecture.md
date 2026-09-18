# Architecture — Disk Image Acquisition & Hashing Toolkit (Chain of Custody Automation)

## Purpose

A local-first Windows desktop application for digital forensic examiners that:

- **Acquires disk images** from physical drives (`\\.\PhysicalDriveN` raw imaging, `dd`-style, single streaming pass with live hashing) or logical folders (STORE-mode `.zip` archive; the finalized archive is then hashed so the recorded digest matches the evidence file).
2. **Hashes evidence** (MD5, SHA-1, SHA-256) so the image and its integrity hashes are produced in a single verifiable flow.
3. **Automates chain of custody** with an append-only, tamper-evident, cryptographically chained log.
4. **Generates professional HTML reports** (evidence manifest, acquisition metadata, hash set, verification results, full custody log) that can be saved and printed/archived.

## Technology Stack

| Layer        | Choice                                                        |
|--------------|---------------------------------------------------------------|
| Language     | Python 3.14 (single-file-friendly, stdlib hashlib/zipfile)    |
| GUI          | CustomTkinter 6.0 (modern dark theme, native widgets)         |
| Packaging    | PyInstaller 6.x → single-folder/windowed EXE                   |
| Persistence  | JSON files (human-readable, portable, audit-friendly)          |
| Hashing      | `hashlib` streaming with progress callbacks                    |
| Imaging      | Raw byte streaming for physical disks; zipfile STORE for folders |
| Reporting    | Self-contained HTML + embedded CSS (opens in default browser) |

## Process Flow

```
┌──────────────────────────┐
│   Investigator (UI)      │
└────────────┬─────────────┘
             │ create / select case
             ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│   Case Manager           │───────▶│  Custody Log (chained)   │
│  cases.json  evidence.json│        │  custody.json            │
└────────────┬─────────────┘        └──────────────────────────┘
             │ acquire / verify
             ▼
┌──────────────────────────┐
│ Acquisition Engine       │  source: \\.\PhysicalDriveN | folder
│  streaming hasher        │  target: .dd image | .zip image
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ HTML Report Generator    │  evidence manifest + hashes + log
└──────────────────────────┘
```

## Module Layout

```
app/
  main.py                  # Entry point (frozen / script aware)
  ui/
    app.py                 # Main window, sidebar navigation, header
    dashboard.py           # Overview cards
    cases.py               # Case CRUD + evidence management
    acquire.py             # Acquisition wizard (source→target→hash)
    verify.py              # Verify images against recorded hashes
    custody.py             # Chain-of-custody log viewer + append
    reports.py             # HTML report generation + download
  core/
    models.py              # Dataclasses: Case, Evidence, CustodyEntry, ...
    store.py               # JSON persistence (atomic writes, versioning)
    hasher.py              # Streaming MD5/SHA1/SHA256 + progress
    acquire.py             # Disk imaging + folder packaging threads
    custody.py             # TMAC-chained append-only log (HMAC integrity)
    report.py              # HTML generator (self-contained styles)
data/                      # Runtime data dir (created next to EXE)
  cases.json               # Case + evidence registry
  custody.json             # Chained custody log
  images/                  # Acquired images
  reports/                 # Generated HTML reports
```

## Data Model

- **Case**: id, case_number, title, agency, investigator, role, description, created_at, status, notes.
- **Evidence**: id, case_id, name, source_type (`physical_disk`|`folder`|`image`), source, target_image,
  image_format (`dd`|`zip`), media_info, size_bytes, hashes (`md5`, `sha1`, `sha256`), acquired_at, acquired_by, verified, status.
- **CustodyEntry**: seq, timestamp, hmac (of previous block + own payload), actor, role, action, detail, hash_chain_ref, immutability_marker.
- **Report**: case_id, generated_at, generated_by, evidence subset, verification results, custody excerpt, report_signature.

## Integrity & Chain-of-Custody Design

- Each custody entry is **chained**: `HMAC(secret, previous_hmac || timestamp || actor || action || detail)`,
  making retrospective tampering detectable and giving an auditable, append-only record.
- Hashes embedded in the HTML report are cross-checked against the live `.json` registry at report time.
- Images are hashed while being written (single streaming pass) — no post-acquisition copy is trusted.
- Every UI action (case create, acquire, verify, report) is automatically appended to the custody log.

## Security & Privacy Notes

- Runs fully **offline**; no telemetry, no network calls.
- Physical-drive imaging (`\\.\PhysicalDriveN`) requires administrator privileges.
- Acquisition is write-only to the target image path; the source drive is opened read-only (`CreateFile` GENERIC_READ).

## Build & Run

- Source: `python -m app.main`
- EXE: `python build.py` → `dist/Forensic Toolkit.exe` (windowed, no console)
- Data lives next to the EXE in `data/`, keeping the tool portable on removable media.