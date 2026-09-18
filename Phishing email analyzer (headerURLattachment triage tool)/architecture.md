# Phishing Email Analyzer - Architecture Document

## Overview

The Phishing Email Analyzer is a desktop security tool designed to triage suspicious emails by
analyzing three core vectors: **email headers**, **embedded URLs**, and **file attachments**.
It delivers a holistic risk assessment with a risk score, detailed forensic evidence, and
exportable HTML reports for incident documentation.

## Technology Stack

| Layer          | Technology                               | Purpose                                  |
| -------------- | ---------------------------------------- | ---------------------------------------- |
| GUI            | CustomTkinter                           | Modern, dark-themed, gorgeous interface  |
| Core Parsing   | Python `email`, `email.headerregistry`   | RFC-5322 email parsing & header decode   |
| URL Analysis   | `urllib.parse`, custom heuristics        | URL decoding, de-obfuscation, analysis   |
| Hashing        | `hashlib`                                | SHA-256 / MD5 attachment fingerprinting  |
| Reporting      | HTML/CSS templates (string-based)        | Standalone styled HTML report export     |
| Packaging      | PyInstaller                              | Single-file `.exe` distribution          |
| Config         | `json`                                   | Application configuration & state        |

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION ENTRYPOINT                        │
│                            (main.py → App)                             │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           GUI LAYER (views/)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Dashboard  │  │ Header View │  │   URL View  │  │ Attach View │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│       ▲                 ▲                ▲                 ▲          │
│       └─────────────────┴────────────────┴─────────────────┘          │
│                    (single analysis session)                            │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ANALYZER ENGINE (engine/)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ HeaderAnalyzer  │  │  URLAnalyzer    │  │ AttachmentAnz.  │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                    ┌──────────────────────────┐                        │
│                    │      RiskScorer          │                        │
│                    │  (weighted evidence sum) │                        │
│                    └──────────────────────────┘                        │
└───────────────────────────────┬────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       OUTPUT / PERSISTENCE (utils/)                    │
│  ┌────────────────────┐  ┌─────────────────────┐                        │
│  │ ReportGenerator    │  │ StateManager / Data │                        │
│  │   (HTML export)    │  │   (history)         │                        │
│  └────────────────────┘  └─────────────────────┘                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. Entry Point — `main.py`
- Bootstraps the application window.
- Loads saved configuration and dark/light preference.
- Routes to `App` (root GUI).

### 2. GUI Layer — `views/` (`app.py`)
Uses CustomTkinter widgets with a cohesive dark theme:

| Component            | Purpose                                                |
| -------------------- | ------------------------------------------------------ |
| Top bar              | App title, sample-email loader, "Export HTML Report"   |
| Input panel          | File picker for `.eml` / `.msg` emails + paste textbox |
| Navigation tabs      | Dashboard / Headers / URLs / Attachments               |
| Dashboard view       | Big risk gauge, verdict badge, evidence summary cards  |
| Tabs                | Forensically formatted header/source, URL table with  |
|                      | classifications, attachment table with hashes          |
| Footer bar           | Status, elapsed-time, session model indicator          |

### 3. Analyzer Engine — `engine/`

#### HeaderAnalyzer (`engine/header_analyzer.py`)
- Extracts RFC-5322 headers via the `email` package.
- Decodes non-ASCII header values (`RFC 2047` encoded-words).
- Identifies the envelope From, To/CC, Subject, Date, Message-ID, SPF/DKIM/DMARC
  Received-Spam status fields if present.
- Computes header-fraud signals:
  - Display-name mismatch vs actual `From` address
  - IP / domain anomalies in `Received` chains
  - Missing SPF/DKIM/DMARC results
  - `Reply-To` not matching `From`
  - Mismatched `Message-ID` domains

#### URLAnalyzer (`engine/url_analyzer.py`)
- Extracts URLs from email body and decoded HTML parts.
- Decodes obfuscation: unicode homoglyphs, URL-encoding, `@`-sign redirects.
- Flags dangerous patterns: `http` vs `https`, dotless domains, IP literal hosts,
  suspicious TLDs, excess subdomain depth, keyword-stuffed hostnames
  (e.g. `amazon-login.secure-checkout.xyz`).
- Classifies each URL: benign / suspicious / malicious.

#### AttachmentAnalyzer (`engine/attachment_analyzer.py`)
- Extracts MIME attachments and list of filenames (no content extraction of
  malicious binaries—only metadata + hash).
- Computes SHA-256 / MD5 hashes for malware-hash lookups.
- Flags high-risk extensions (`.exe`, `.scr`, `.js`, `.docm`, `.lnk`, ...).
- Detects double extensions (`invoice.pdf.exe`) and trailing-space tricks.

#### RiskScorer (`engine/risk_scorer.py`)
Aggregates evidence with tunable weights:

| Signal            | Weight |
| ----------------- | ------ |
| Spoofed sender    | 40     |
| Dangerous URL     | 35     |
| Malicious attachment | 40  |
| Suspicious attachment | 20  |
| Missing auth (SPF/DKIM/DMARC) | 15 |
| Suspicious header only | 10     |

Final score = `min(100, floor(Σ weighted_evidence))`.
Verdict mapping:

| Score | Verdict      |
| ----- | ------------ |
| 0–14  | SAFE         |
| 15–39 | LOW RISK     |
| 40–69 | MODERATE     |
| 70–89 | HIGH RISK    |
| 90+   | CRITICAL     |

### 4. Output — `utils/`

#### ReportGenerator (`utils/report_generator.py`)
- Builds a standalone, responsive HTML report with embedded CSS.
- Sections: header, risk summary (score + verdict), detailed findings per
  vector, URL table, attachment table, raw header view.
- Reports are saveable via file dialog → `Save As…`.

#### StateManager (`utils/state.py`)
- Persists last-used settings (theme, history of past analyses) to
  `data/app_state.json`.
- Keeps a rolling history of the last N analyses for the session dashboard.

## Data Flow

```
Raw EMail ──► Parser ──► {headers, urls, attachments, body}
                         │
                         ▼
              Analyzers (parallel-safe, pure functions)
                         │
                         ▼
              Heat Evidence List ──► Risk Scorer ──► Score + Verdict
                         │
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
        Dashboard render       HTML report export
```

## Security & Privacy

- **100% offline**: No data leaves the machine. URL analysis is heuristic-based,
  no network lookups.
- Attachment payloads are never executed or de-compressed beyond MIME decode;
  only metadata and hash values are recorded.
- Reports may be re-run from a sample without persistent storage of the email body.

## Build & Distribution

Built as a single Windows executable via:

```bash
pyinstaller --noconfirm --onefile --windowed \
  --name "PhishingEmailAnalyzer" \
  --icon=assets/icon.ico \
  --add-data "assets;assets" \
  main.py
```

Output: `dist/PhishingEmailAnalyzer.exe`

## Forward Compatibility

The analyzer is designed so additional checks (VirusTotal integration, DNS SPF
verification, YARA rules) can be dropped in as new `*Analyzer` classes without
touching the GUI or report layers.