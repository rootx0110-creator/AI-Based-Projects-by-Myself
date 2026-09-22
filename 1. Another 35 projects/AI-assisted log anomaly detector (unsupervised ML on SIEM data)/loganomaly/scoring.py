"""Ensemble scoring, anomaly flagging and local explainability."""

import numpy as np

from .models import fit_all, _rank_normalize, _flag_top
from .features import BEHAV_FEATURES


def _standardize(X):
    """Column-wise z-scoring so every feature competes fairly regardless of
    raw unit/magnitude. Near-constant columns are kept as zeros."""
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd < 1e-9, 1.0, sd)
    return (X - mu) / sd


def run_detection(events, X, feature_names, meta, selection="if,ae",
                  contamination=0.05, **model_kwargs):
    """Run the model ensemble over a feature matrix.

    Returns a result dict consumed by the report / UI:
      scores   -- (n,) ensemble anomaly score in [0, 1]
      labels   -- (n,) boolean anomaly flags
      models   -- list of {key, name, score} raw per-model info
      explains -- dict event_index -> list of (feature, reason, weight) for
                  flagged events
    """
    n = X.shape[0]
    if n == 0:
        return {"scores": np.array([]), "labels": np.zeros(0, dtype=int),
                "models": [], "explains": {}, "incidents": [], "n_features": 0}

    per_model = []
    members = []
    results = fit_all(_standardize(X), selection, **model_kwargs)
    for key, name, raw, lab in results:
        norm = _rank_normalize(raw)
        per_model.append({"key": key, "name": name, "raw": raw.tolist(),
                          "normalized": norm.tolist(),
                          "flagged": int(lab.sum())})
        members.append(np.nan_to_num(norm, nan=0.0))

    # Burst component: dense duplicate/aggregate attacks (brute force, DNS
    # flash, port fan-out) are pathological for point-based detectors like
    # IsolationForest, so we surface the behavioural dimensions directly.
    # Blend rule: a loud, confident call from *either* the point-detector
    # ensemble *or* the burst signal flags an event (max-combination is the
    # safest choice when any detector can be decisive in its own regime).
    burst = _burst_score(X, feature_names)
    members.append(burst)
    per_model.append({"key": "burst", "name": "Burst / Façade",
                      "raw": burst.tolist(), "normalized": burst.tolist(),
                      "flagged": int((burst >= 0.95).sum())})

    model_agg = np.mean(np.column_stack(members[:-1]), axis=1)
    # Cluster-confidence bonus: large, uniform bursts are higher-priority
    # triage than lone needles. Each event inherits the size of the largest
    # behaviour identity it participates in (per-source and per-account), and
    # the bonus grows with that size.
    sizes = _cluster_sizes(events)
    bonus = 0.08 * np.log1p(sizes)
    agg = np.minimum(np.maximum(model_agg, burst) + bonus, 1.5)
    labels = _flag_top_capped(agg, contamination, events)
    explains = _explain_flagged(events, X, feature_names, labels, meta)
    incidents = _build_incidents(events, agg, labels, top=15)

    return {
        "scores": agg,
        "labels": labels,
        "models": per_model,
        "explains": explains,
        "incidents": incidents,
        "n_features": X.shape[1],
    }


def _cluster_sizes(events):
    """Per-event incident-cluster size, using two identity views.

    Per-source key      (src_ip, user, event_type): captures single-host
                        bursts (a box hammering a service).
    Per-account key     (user, event_type):          captures source-spread
                        activity from one account (privilege abuse across
                        many hosts).
    An event's size is the maximum over both views, so either frame yields
    the bonus.
    """
    from collections import Counter

    n = len(events)
    if n == 0:
        return np.zeros(0)
    src_c = Counter()
    acct_c = Counter()
    for e in events:
        src_c[(str(e.get("src_ip") or "-"), str(e.get("user") or "-"),
               str(e.get("event_type") or "-"))] += 1
        acct_c[(str(e.get("user") or "-"), str(e.get("event_type") or "-"))] += 1
    sizes = np.zeros(n)
    for i, e in enumerate(events):
        a = src_c[(str(e.get("src_ip") or "-"), str(e.get("user") or "-"),
                   str(e.get("event_type") or "-"))]
        b = acct_c[(str(e.get("user") or "-"), str(e.get("event_type") or "-"))]
        sizes[i] = max(a, b)
    return sizes


def _flag_top_capped(scores, contamination=0.05, events=None, cap=None):
    """Flag the top `contamination` events by score, but cap how many events
    a single incident identity may contribute to the triage queue. This keeps
    one massive burst (e.g. a 150-event DNS flood) from crowding out every
    other incident class while still flagging its representative events.
    """
    s = np.asarray(scores, dtype=float)
    n = s.shape[0]
    if n == 0:
        return np.zeros(n, dtype=int)
    n_flag = max(1, int(round(n * contamination)))
    if cap is None:
        cap = max(5, int(round(n_flag / 4)))
    from collections import Counter

    labels = np.zeros(n, dtype=int)
    per_ident = Counter()
    order = np.argsort(-np.nan_to_num(s), kind="mergesort")
    flagged = 0
    for i in order:
        if flagged >= n_flag:
            break
        ident = _ident(events[i]) if events is not None else None
        if ident is not None and per_ident[ident] >= cap:
            continue
        labels[i] = 1
        flagged += 1
        if ident is not None:
            per_ident[ident] += 1
    return labels


def _build_incidents(events, scores, labels, top=15):
    """Group events into incident clusters by behaviour identity.

    Standard SIEM practice: hundreds of near-identical events are one
    incident. Identity key = (src_ip, user, event_type) with dst_ip folded in
    when stable. Clusters are ranked by the peak anomaly score within them.
    """
    from collections import Counter

    if labels is None:
        labels = np.zeros(len(events), dtype=int)

    counts = Counter()
    for e in events:
        k = _ident(e)
        counts[k] += 1

    clusters = {}
    for i, e in enumerate(events):
        k = _ident(e)
        c = clusters.setdefault(k, {
            "key": k, "size": counts[k], "indices": [],
            "max_score": 0.0, "score_sum": 0.0,
            "events": [], "event_types": Counter(), "users": set(),
            "src_ips": set(), "dst_ips": set(),
        })
        c["indices"].append(i)
        c["score_sum"] += float(scores[i])
        if scores[i] > c["max_score"]:
            c["max_score"] = float(scores[i])
        c["event_types"][e.get("event_type")] += 1
        if e.get("user"):
            c["users"].add(e["user"])
        if e.get("src_ip"):
            c["src_ips"].add(e["src_ip"])
        if e.get("dst_ip"):
            c["dst_ips"].add(e["dst_ip"])

    ranked = sorted(clusters.values(), key=lambda c: -c["max_score"])[:top]
    for c in ranked:
        c["mean_score"] = round(c["score_sum"] / max(1, c["size"]), 3)
        c["max_score"] = round(c["max_score"], 3)
        c["flagged"] = int(any(labels[i] for i in c["indices"]))
        top_event = max(c["indices"], key=lambda i: scores[i])
        c["top_event"] = int(top_event)
        c["severity"] = int(max((events[i].get("severity") or 0) for i in c["indices"]))
    return ranked


def _ident(e):
    """Behaviour identity used for incident clustering.

    A source acting in a burst is one incident regardless of how many target
    hosts it touches, so dst_ip is excluded from the key (it is kept as a
    display field on the cluster instead).
    """
    return "|".join([str(e.get("src_ip") or "-"), str(e.get("user") or "-"),
                     str(e.get("event_type") or "-")])


def _burst_score(X, feature_names):
    """Saturating burst score per event on the behavioural (beh_*) block.

    For each behavioural column we compute a robust deviation (|x - med|/MAD);
    the event score is the larges column deviation mapped through
    1 - exp(-dev/k). Any real burst saturates near 1.0 regardless of how much
    larger the biggest burst in the feed is, so small and large incidents
    remain comparable (the incident-size bonus provides the extra weight for
    massive floods).
    """
    n = X.shape[0]
    beh = [j for j, name in enumerate(feature_names) if name.startswith("beh_")]
    if not beh:
        return np.zeros(n)
    cols = X[:, beh]
    med = np.nanmedian(cols, axis=0)
    mad = np.nanmedian(np.abs(cols - med), axis=0)
    mad = np.where(mad < 1e-3, 1e-3, mad)
    dev = np.abs(cols - med) / mad
    per_event = np.max(dev, axis=1)
    return 1.0 - np.exp(-per_event / 6.0)


def _explain_flagged(events, X, feature_names, labels, meta, k=5):
    """Attribute each flagged event to its most deviating features.

    Uses robust statistics (median / MAD) per feature. For behavioural
    features the explanation is phrased in SIEM terms via `meta`.
    """
    explains = {}
    if X.shape[0] == 0:
        return explains
    med = np.nanmedian(X, axis=0)
    mad = np.nanmedian(np.abs(X - med), axis=0)
    mad = np.where(mad < 1e-6, 1e-6, mad)
    n_feat = X.shape[1]

    for i in range(X.shape[0]):
        if not labels[i]:
            continue
        row = X[i]
        dev = np.zeros(n_feat)
        for j in range(n_feat):
            val, m = float(row[j]), float(med[j])
            if val >= 0.0 and m >= 0.0:
                dev[j] = (val - m) / mad[j]
            else:
                dev[j] = abs(val - m) / mad[j]
        dev = np.clip(dev, 0.0, 30.0)
        top = np.argsort(-dev)[:k]
        items = []
        for j in top:
            if dev[j] < 0.01:
                continue
            name = feature_names[j]
            reason = _reason(name, meta, events[i])
            items.append({
                "feature": name,
                "reason": reason,
                "weight": round(float(dev[j]), 2),
                "value": round(float(row[j]), 3),
                "norm": round(float(med[j]), 3),
            })
        if items:
            items.sort(key=lambda t: -t["weight"])
            explains[int(i)] = items
    return explains


def _reason(feature, meta, event):
    if feature.startswith("text."):
        return "message text carries an unusual term/blend signature"
    if feature in meta:
        template, key = meta[feature]
        return template.format(key=key, val=event.get(key) or "none")
    return feature.replace("_", " ")