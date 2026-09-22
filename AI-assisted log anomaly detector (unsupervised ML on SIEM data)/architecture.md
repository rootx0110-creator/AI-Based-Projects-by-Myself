# Architecture — AI-assisted log anomaly detector (unsupervised ML on SIEM data)

## Purpose
Detect suspicious and anomalous events in raw SIEM / firewall / OS log feeds with
**no labels, no signatures and no training set**. Every event is compared against
the rest of the feed using a voting ensemble of unsupervised detectors, then
grouped into triage-friendly incident clusters with per-event, feature-level
explanations.

## High-level layout

```
┌────────────┐   ┌────────────────────────────────────────────────────────┐
│  Browser   │   │               Flask web application (app.py)           │
│  dashboard │◄──│  GET /            dashboard UI (Jinja2)                 │
│  (classy   │   │  POST /api/analyze  ingest + run ensemble -> JSON       │
│   navy/    │   │  POST /api/report   produce standalone HTML report      │
│   gold UI) │   │  GET  /api/sample   bundled synthetic SIEM feed (CSV)   │
└────────────┘   └────────┬───────────────────────────────────────────────┘
                          │
        loganomaly package (pure Python, numpy + scikit-learn only)
                          │
   ┌──────────────┬───────┴───────┬────────────────┬──────────────────┐
   │  ingestion   │   features    │    models      │     scoring      │   report
   │ parse CSV/   │ behavioural + │ Isolation      │ ensemble blend,  │  self-contained
   │ JSON/JSONL   │ numeric +     │ Forest, LOF,   │ burst component, │  HTML builder
   │ Syslog/CEF/  │ hashed text   │ One-Class SVM, │ incident cluster,│  (inline CSS no
   │ raw text     │ (log1p ratios)│ Nano Autoenc.  │ explanations     │   external assets)
   └──────────────┴───────┬───────┴────────────────┴──────────────────┘
                          │
                    synthetic generator (sample_data.py) for demo/testing
```

## Data flow

1. **Ingestion** (`loganomaly/ingestion.py`) — bytes are decoded and normalised to a
   canonical event record (`timestamp, source, src_ip, dst_ip, ports, user,
   event_type, protocol, severity 0..10, bytes, duration, message`). CSV/TSV, JSON
   array, JSONL, RFC3164 Syslog, CEF and raw free-text lines are detected by
   content, not file extension.
2. **Feature engineering** (`loganomaly/features.py`):
   - *Behavioural block* (`beh_*`): appearances of each identity value, unique
     destination/source fan-out, unique port neighbours, mean severity per event
     type, and events-per-second rate per identity. Values are log1p-compressed.
   - *Numeric block*: ports, severity, bytes in/out, duration.
   - *Text block*: dependency-free hashed uni-gram + bigram terms over `message`
     (deterministic MD5 buckets) with inverse-log-frequency weighting.
3. **Modelling** (`loganomaly/models.py`) — the matrix is column-standardised and
   each selected detector emits a raw anomaly score plus 0/1 labels:
   - `IsolationForest` (isolation depth)
   - `LocalOutlierFactor` (local density)
   - `OneClassSVM` (single-class boundary, RBF)
   - `NanoAutoencoder` (tiny MLP written in pure numpy; reconstruction error)
4. **Scoring / ensemble** (`loganomaly/scoring.py`):
   - Per-detector raw scores are mapped to comparable [0,1] ranks.
   - `Burst` component: saturating deviation on the `beh_*` block
     (`1 - exp(-dev/6)`). This is the standard remedy for the well-known
     IsolationForest weakness on dense duplicate clusters (brute force, DNS
     floods).
   - Blend rule: `score = max(model_ensemble, burst) + 0.08·log1p(cluster_size)`,
     clamped at 1.5. Cluster size is computed under two frames (per-source identity,
     per-account identity) so source-spread attacks are rewarded too.
   - Flagging: top `contamination` events **capped per incident identity** so one
     massive burst cannot monopolise the triage queue.
   - Explanations: robust `|x − med| / MAD` deviation per feature, phrased in SIEM
     terms for behavioural features (e.g. "appearances of src_ip '192.168.0.7'").
   - Incidents: events grouped by `(src_ip, user, event_type)` with per-account
     override, ranked by peak score, carrying size / severity / representative event.
5. **Reporting** (`loganomaly/report.py`) — standalone HTML (inline CSS, same navy/
   gold visual language, no external assets) with summary cards, method list,
   incident clusters, distribution bars and the flagged-events table.

## Why it is unsupervised
No ground-truth labels, no training/validation split, no threshold tuning per
dataset. The scoring is self-referential (compare each event with the whole feed
in feature space), which is exactly the requirement for "unsupervised ML on SIEM
data" where labelled corporate incidents are rarely available.

## Reproducibility
- Deterministic hash vectorisation (MD5 of token text).
- Fixed `random_state` for IsolationForest; seeded numpy RNG for the autoencoder.
- Scores/decisions depend only on the uploaded feed + selected detectors.

## Non-goals / notes
- Not a correlation engine; no cross-feed linking, no live streaming ingestion.
- Single-user, in-memory state (`app.py::AppState`) — suitable for demo/forensics,
  not a multi-tenant SIEM replacement.