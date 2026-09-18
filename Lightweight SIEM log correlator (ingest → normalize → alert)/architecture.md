# Lightweight SIEM Log Correlator — Architecture

## Overview

A lightweight, self-contained SIEM (Security Information and Event Management) log correlator that follows the core pipeline: **Ingest → Normalize → Correlate → Alert → Report**.

It is built as a **web application** (Flask backend + single-page frontend) so it can run anywhere Python is available — no heavy ELK stack, no external databases. All state is retained in memory with JSON snapshotting.

## System Architecture

```
                          ┌──────────────────────────────┐
                          │         Web Frontend          │
                          │   (HTML/CSS/JS - dashboard,   │
                          │    logs, alerts, correlation) │
                          └──────────────┬───────────────┘
                                         │ HTTP / JSON
                          ┌──────────────▼───────────────┐
                          │         Flask Backend         │
                          │           (app.py)            │
                          └──────────────┬───────────────┘
                                         │
              ┌──────────────┬───────────┼────────────┬──────────────┐
              ▼              ▼           ▼            ▼              ▼
        ┌───────────┐  ┌───────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
        │  INGEST   │──▶│ NORMALIZE │─▶│ CORRELATE │─▶│   ALERT   │─▶│  REPORT    │
        └───────────┘  └───────────┘ └────────────┘ └────────────┘ └────────────┘
              │              │           │              │              │
        ┌──────▼─────┐  ┌────▼────┐ ┌────▼────┐  ┌─────▼────┐  ┌────▼───────┐
        │ Bulk JSON  │  │ Common  │ │ Rule     │  │ Severity │  │ HTML       │
        │ file/API/  │  │ Event   │ │ Engine   │  │ Ranking  │  │ export +   │
        │ sample gen │  │ Schema  │ │ + history│  │ + Fan-   │  │ terminal   │
        └────────────┘  └─────────┘ │ tracking │  │ out      │  └────────────┘
                                    └──────────┘  └──────────┘
```

## Pipeline Stages

### 1. Ingest
- **Sources:**
  - JSON line ingestion via REST API (`POST /api/ingest`)
  - File upload (`.log`, `.json`, `.txt`) via web UI
  - Built-in **sample log generator** for demos
  - Direct event push for real-time simulations
- **Record keeping:** every ingested line is stored with a monotonically increasing `ingest_id`, raw text, and nanosecond timestamp.

### 2. Normalize
- Each raw log is classified by source type (Apache, Nginx, Suricata, Firewall, Auth, JSON, generic).
- All events are converted to a **Common Event Schema**:
  - `timestamp`, `source`, `event_type`, `severity` (info/low/medium/high/critical)
  - `src_ip`, `dst_ip`, `src_port`, `dst_port`, `user`, `protocol`
  - `message`, `raw`, `hash`, `ingest_id`
- Normalization supports regex-based extraction for common formats and graceful fallback to generic parsing.
- Failed/normalized ratio is tracked for pipeline health metrics.

### 3. Correlate
The correlation engine applies **rule-based temporal correlation**:
- Rules match on fields (src_ip, dst_ip, user, event_type, severity, protocol).
- A **sliding time window** (default 60 s) groups matching events; when the match threshold (default 3) is reached, a correlation event is fired.
- Supports:
  - **Single-source correlation** (e.g., 5 failed logins from same IP)
  - **Pattern correlation** (e.g., brute force → auth success)
  - **Severity escalation aggregation**
  - Optional **fan-out / fan-in** chain tracking across event types
- Each correlation records: rule name, matched events, time window, severity, risk score.

### 4. Alert
- Correlation hits become **alerts**.
- Alerts carry: severity, risk score (0–100), status (open / ack / closed), generated time, correlated event refs.
- Escalation tier is derived from risk score:
  - 0–39 → LOW, 40–69 → MEDIUM, 70–89 → HIGH, 90+ → CRITICAL
- Alerts can be acknowledged or closed from the UI.

### 5. Report
- Whole-pipeline dashboard report exported as a **standalone HTML file** (self-contained, inline CSS).
- Includes: summary KPIs, log timeline by source, event type distribution, top source IPs, alerts table, and canned insight text.
- Downloadable via one click from the UI.

## Components

| Component | File | Responsibility |
|---|---|---|
| Flask app / API | `app.py` | HTTP layer, routes, JSON API |
| Normalizer | `correlator/normalizer.py` | raw → Common Event Schema |
| Correlation engine | `correlator/correlator.py` | pattern/temporal matching + risk |
| Alert manager | `correlator/alerter.py` | alert lifecycle + escalation |
| Data model / store | `correlator/store.py` | in-memory store + JSON snapshots |
| Sample generator | `correlator/samples.py` | realistic demo log stream |
| Frontend | `templates/index.html` | single-page UI |
| Styles | `static/css/style.css` | dark SOC dashboard theme |
| Frontend logic | `static/js/app.js` | polling, charts, report triggers |
| Docs | `architecture.md` `memory.md` `state.md` | project living memory |

## Data Flow Example

```
Raw:   "Jan 15 09:12:01 sshd[1234]: Failed password for root from 1.2.3.4 port 22"
       │
       ▼ Normalize
       { timestamp: 09:12:01, source: auth, event_type: ssh_failed,
         severity: medium, src_ip: 1.2.3.4, user: root }
       │
       ▼ Correlate  (rule: brute_force, window 60s, threshold 5)
       1.2.3.4 → 5 ssh_failed in 60s  ⇒  CORRELATION
       │
       ▼ Alert
       { severity: high, risk: 78, status: open, ... }
       │
       ▼ Report
       HTML dashboard download
```

## Design Decisions

- **Flask over FastAPI:** zero extra deps beyond Flask; simpler for beginners; runs anywhere.
- **No external database:** keeps it "lightweight"; state persisted via JSON snapshots to `state.json`.
- **Single-page frontend:** one HTML file, vanilla JS, no build step.
- **Bot-free UI:** pure HTML/CSS fan-out charts — no chart library needed (keeps it offline-capable).

## Non-Goals

- No Elasticsearch, Kafka, or cloud dependencies.
- Not a production-grade distributed SIEM (that's "lightweight" by design).
- No authentication layer (intended for local lab use).