# Memory — project working notes

Persistent context for anyone (or any agent) resuming work on this project.

## Landmarks
- Entry point: `app.py` (Flask). Run with `python app.py`, serves on
  http://127.0.0.1:8600 .
- ML package: `loganomaly/` — `ingestion`, `features`, `models`, `scoring`,
  `report`, `sample_data`.
- UI: `templates/index.html`, `static/css/style.css`, `static/js/app.js`.
- Theme: deep navy canvas (`#0e1626`), antique gold (`#d9a441`), teal
  (`#2fa1a1`), warm cream text (`#e9dfcf`). **No pure black or white anywhere.**
- Environment: Windows, Python 3.14, numpy 2.5, scikit-learn 1.9, pandas 3.0.

## Key design decisions (rationale lives in architecture.md)

### D1 — Ensemble of four unbiased detectors + burst component
IsolationForest/LOF/OneClassSVM/Autoencoder each have blind spots. A
max-combination blend (`score = max(model_agg, burst)`) was chosen after
measuring that mean-averaging let one detector's low score (e.g. autoencoder
near 0.0 for repeated identical events) sink genuinely anomalous bursts.
The Burst signal is the fix for the classic IsolationForest failure on dense
duplicate clusters (verified empirically: brutal brute-force/DNS-flood bursts
ranked below median before it was added).

### D2 — Cluster-confidence bonus
`+0.08·log1p(cluster_size)` under two identity frames (per-source, per-account).
Bursts of dozens-to-hundreds of uniform events are higher-priority triage than
lone needles. Cap flags per identity (`max(5, n_flag/4)`) so a 150-event DNS
flood cannot eat the whole 5% budget.

### D3 — Feature formulation is SIEM-shaped
Behavioural aggregations (appearances, fan-out, unique ports, events/sec,
per-type severity) are extracted because they match what a SOC analyst means by
an anomaly; text is compressed with hashed uni+bigram terms (deterministic,
idf-weighted) rather than a heavy TF-IDF vectoriser.

### D4 — No black/white, self-contained report
The downloadable HTML report inlines its own CSS (navy/gold theme) and zero
external assets, so it works offline and on any device.

## Notables / gotchas
- `loganomaly/ingestion.py` detects format from *content*, not extension.
- Port scan is clustered as ONE incident because `dst_ip` is excluded from the
  identity key.
- `_flag_top_capped` needs `events` (identity mapping) — pass it or flags are
  single-event-capped.
- LOF emits duplicate-value warnings on repeated messages; suppressed inside
  `LocalOutlierFactorModel.fit_predict_anomaly` with `warnings.catch_warnings`.
- `_summarize` in app.py expects `sev_dist`/`etype_dist` keys — used by the
  report generator's distribution section.
- Scores exceed 1.0 (burst-augmented); UI/report render `min(1, x/1.5)` bars.
- New random sample feeds are generated on demand (`/api/sample`); anomaly
  quality was tuned against the seed=42 feed with 5 planted behaviours
  (brute force, exfil, port scan, privilege escalation, DNS flood).

## Quality check (ad-hoc, seed=42 sample)
- All five planted incident behaviours surface in the top incident clusters
  (scores ≈ 1.40 DNS flood, 1.36 brute force, 1.35 port scan, 1.33 exfil,
  1.30 privilege escalation with account-frame bonus) ahead of normal events
  (≈1.05).
- Sample feed: 1904 events, 404 planted.

## Open ideas (parked, do not implement without approval)
1. Live streaming mode (`/events` SSE) and real-time scoring.
2. Optional strict-vs-permissive flag threshold + incident TTL merging.
3. Export JSON of explanations for downstream EDR connectors.
4. Multi-file compare (baseline vs new feed).