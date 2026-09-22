"""Feature engineering for SIEM events.

Produces a numeric matrix from the normalized event records using:

1. Behavioural aggregation features  -- counts, cardinalities and rates per
   categorical value (rare/massive sources, single actors fanning out to many
   targets, etc.). These capture the semantics security analysts look for.
2. Numeric features                  -- ports, bytes, duration, severity.
3. Text features                     -- hashed bag-of-words + n-grams over the
   free-text message field, so novel/misspelled/rare payload strings stand out.
"""

import hashlib
import re
from collections import Counter

import numpy as np

NAME_KEYS = ("src_ip", "dst_ip", "source", "user", "event_type", "protocol")
NUM_MAPPING = {
    "src_port": "src_port",
    "dst_port": "dst_port",
    "severity": "severity",
    "bytes_in": "bytes_in",
    "bytes_out": "bytes_out",
    "duration": "duration",
}
TEXT_DIM = 128
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")

# Behavioural features that are attached to the value identity of a categorical
# key so the explainer can phrase them in SIEM terms.
BEHAV_FEATURES = {
    "count": "appearances of {key} value '{val}'",
    "uniq_dst": "unique destination count for {key} '{val}'",
    "uniq_src": "unique source count for {key} '{val}'",
    "sev_mean": "mean severity of {key} '{val}'",
    "rate": "events per second among {key} '{val}'",
}


def _val(v):
    return str(v).lower() if v is not None else "<none>"


def _sev(e):
    return float(e.get("severity") or 0.0)


def _log1p(x):
    return float(np.log1p(x))


def build_behavioural(events, idx):
    """Compute per-event behavioural features.

    Returns (matrix, feature_names, meta) where meta maps feature name ->
    (human-readable template, source categorical key) used by the explainer
    to phrase the feature in SIEM terms.
    """
    n = len(events)
    if n == 0:
        return np.zeros((0, 0)), [], {}

    timestamps = [e.get("timestamp") for e in events]
    epochs = [ts2e(t) for t in timestamps]
    can_rate = any(t == t for t in epochs)  # any non-NaN epoch

    counts = {}
    for i in range(n):
        for k in NAME_KEYS:
            if k == "dst_ip":
                continue
            v = _val(events[i].get(k))
            counts.setdefault(k, Counter())[v] += 1

    # unique neighbours (src -> dst, dst -> src, src -> user, host -> event type)
    nb = {("src_ip", "dst_ip"): {}, ("dst_ip", "src_ip"): {},
          ("src_ip", "user"): {}, ("source", "event_type"): {},
          ("user", "event_type"): {}, ("src_ip", "dst_port"): {},
          ("dst_ip", "src_port"): {}}
    sev_acc = Counter()
    ts_acc = {}
    for i in range(n):
        e = events[i]
        for (a, b), store in nb.items():
            va, vb = _val(e.get(a)), _val(e.get(b))
            store.setdefault(va, set()).add(vb)
        sev_acc[_val(e.get("event_type"))] += _sev(e)
        if can_rate:
            t = epochs[i]
            if t == t:
                for k in ("src_ip", "dst_ip", "user", "source"):
                    ts_acc.setdefault(k, {}).setdefault(_val(e.get(k)), set()).add(t)

    cols = []
    names = []
    meta = {}

    def add_col(name, values, key, template):
        cols.append(values)
        names.append(name)
        meta[name] = (template, key)

    for k in NAME_KEYS:
        c = counts.get(k, Counter())
        if not c:
            continue
        base = f"beh_{k}"
        add_col(f"{base}.count",
                np.array([_log1p(c[_val(events[i].get(k))]) for i in range(n)]),
                k, BEHAV_FEATURES["count"])
        if (k, "dst_ip") in nb:
            store = nb[(k, "dst_ip")]
            add_col(f"{base}.uniq_dst",
                    np.array([_log1p(len(store[_val(events[i].get(k))])) for i in range(n)]),
                    k, BEHAV_FEATURES["uniq_dst"])
        if (k, "src_ip") in nb:
            store = nb[(k, "src_ip")]
            add_col(f"{base}.uniq_src",
                    np.array([_log1p(len(store[_val(events[i].get(k))])) for i in range(n)]),
                    k, BEHAV_FEATURES["uniq_src"])

    # src_port/dst_port-neighbour features (port fan-out fan-in)
    for (a, b), store in nb.items():
        if (a, b) in (("src_ip", "dst_ip"), ("dst_ip", "src_ip"), ("src_ip", "user"),
                      ("source", "event_type"), ("user", "event_type")):
            continue
        fmt = f"unique {b} count for {{key}} '{{val}}'"
        base = f"beh_{a.replace('_ip', '')}_neigh_{b.replace('_ip', '').split('_')[0]}"
        add_col(f"{base}.uniq",
                np.array([_log1p(len(store[_val(events[i].get(a))])) for i in range(n)]),
                a, fmt)

    # mean severity per event_type
    et_counts = counts.get("event_type", Counter())
    if et_counts and sev_acc:
        add_col("beh_event_type.sev_mean",
                np.array([sev_acc[_val(events[i].get("event_type"))] /
                          max(1, et_counts[_val(events[i].get("event_type"))])
                          for i in range(n)]),
                "event_type", BEHAV_FEATURES["sev_mean"])

    # event rate per identity (events per second over the feed)
    if can_rate:
        for k, store in ts_acc.items():
            values = np.zeros(n, dtype=float)
            for i in range(n):
                v = _val(events[i].get(k))
                tlist = sorted(store[v]) if hasattr(store[v], "__iter__") else []
                if len(tlist) > 1:
                    span = max(1e-6, tlist[-1] - tlist[0])
                    values[i] = _log1p(len(tlist) / span)
            add_col(f"beh_{k}.rate", values, k, BEHAV_FEATURES["rate"])

    if not cols:
        return np.zeros((n, 0)), [], {}

    X = np.column_stack(cols).astype(float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X, names, meta


def ts2e(ts):
    """Best-effort timestamp -> epoch. Returns float seconds or nan."""
    if ts is None:
        return float("nan")
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f", "%d/%b/%Y:%H:%M:%S", "%b %d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S"):
        try:
            from datetime import datetime
            return datetime.strptime(s[:19], fmt).timestamp()
        except ValueError:
            continue
    try:
        from datetime import datetime
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return float("nan")


def build_numeric(events):
    n = len(events)
    names = []
    cols = []
    for out_name, canon in NUM_MAPPING.items():
        col = np.zeros(n, dtype=float)
        for i in range(n):
            val = events[i].get(canon)
            col[i] = float(val) if isinstance(val, (int, float)) else 0.0
        if col.shape[0]:
            cols.append(col)
            names.append(out_name)
    if not cols:
        return np.zeros((n, 0)), []
    return np.column_stack(cols), names


def build_text(events, dim=24):
    """Hashed term + bigram features over the message field.

    Dependency-free stand-in for a TF-style vectorizer. `dim` is the number
    of buckets per flavour (terms and bigrams), so the column count is 2*dim.
    """
    n = len(events)
    X = np.zeros((n, dim * 2), dtype=float)
    masks = np.zeros((n, dim * 2), dtype=float)
    total_terms = np.zeros(n, dtype=float)
    for i in range(n):
        msg = (events[i].get("message") or "")[:512].lower()
        if not msg:
            continue
        toks = _TOKEN_RE.findall(msg)
        for t in toks:
            h = int(hashlib.md5(t.encode()).hexdigest(), 16)
            X[i, h % dim] += 1.0
        for j in range(len(toks) - 1):
            g = toks[j] + ":" + toks[j + 1]
            h = int(hashlib.md5(g.encode()).hexdigest(), 16)
            X[i, dim + (h % dim)] += 1.0
        total_terms[i] = X[i].sum()

    # Global inverse-log-frequency weighting: tokens that appear in very few
    # events carry more signal, but common structural words are damped.
    df = (X > 0).sum(axis=0)
    w = np.log(1.0 + n / np.maximum(1.0, df))
    for i in range(n):
        if total_terms[i] > 0:
            X[i] = np.log1p(X[i] * w) / np.log1p(total_terms[i])
            masks[i] = 1.0
    names = [f"text.t{i}" for i in range(dim)] + [f"text.g{i}" for i in range(dim)]
    return X, names, masks


def build_feature_matrix(events, text_dim=TEXT_DIM):
    """Assemble the full numeric feature matrix.

    Returns (X, feature_names, meta).
    meta: dict feature_name -> (template, key, value) for readable explains.
    """
    parts, names, metas = [], [], {}
    Xb, nb, mb = build_behavioural(events, list(range(len(events))))
    if Xb.shape[1]:
        parts.append(Xb)
        names += nb
        metas.update(mb)
    Xn, nn = build_numeric(events)
    if Xn.shape[1]:
        parts.append(Xn)
        names += nn
    Xt, nt, masks = build_text(events, text_dim)
    if Xt.shape[1] and masks.any():
        parts.append(Xt)
        names += nt

    if not parts:
        raise ValueError("no usable features could be extracted")

    X = np.column_stack(parts).astype(float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X, names, metas