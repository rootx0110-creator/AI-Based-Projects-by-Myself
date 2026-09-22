"""Unsupervised anomaly detectors.

Four independent views on the same feature matrix:

1. IsolationForest  -- isolates observations with few splits; classic SIEM pick.
2. LocalOutlierFactor -- density based; flags points in low-density regions.
3. OneClassSVM     -- kernel boundary around the "normal" bulk.
4. NanoAutoencoder -- a small feed-forward net written in pure numpy; the
                      reconstruction error of a point is its anomaly score
                      (higher error == less like the learned normal patterns).

All detectors expose `.fit_predict_anomaly(X) -> (scores, labels)` where
`scores` are dense floats (higher = more anomalous) and `labels` are
0/1 arrays (1 == anomaly) so the ensemble downstream is uniform.
"""

import warnings

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.svm import OneClassSVM
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:  # pragma: no cover
    HAS_SKLEARN = False


def _rank_normalize(scores):
    """Map raw scores into a [0, 1] space by rank so ensemble members are
    comparable despite different units."""
    s = np.asarray(scores, dtype=float)
    if s.size == 0:
        return s
    notnan = ~np.isnan(s)
    if notnan.sum() == 0:
        return s
    order = np.argsort(np.argsort(s[notnan], kind="mergesort"))
    out = np.full(s.shape, np.nan)
    out[notnan] = order / max(1, notnan.sum() - 1)
    return out


class IsolationForestModel:
    name = "Isolation Forest"
    short = "if"

    def __init__(self, n_estimators=200, max_samples="auto", contamination="auto"):
        self.params = dict(n_estimators=n_estimators, max_samples=max_samples,
                           contamination=contamination, random_state=42)

    def fit_predict_anomaly(self, X):
        if not HAS_SKLEARN:
            raise RuntimeError("scikit-learn is not installed")
        if X.shape[0] < 3:
            return np.zeros(X.shape[0]), np.zeros(X.shape[0], dtype=int)
        m = IsolationForest(**self.params)
        m.fit(X)
        if hasattr(m, "score_samples"):
            rawscores = -m.score_samples(X)
        else:
            rawscores = -m.decision_function(X)
        labels = _flag_top(rawscores)
        return rawscores, labels


class LocalOutlierFactorModel:
    name = "Local Outlier Factor"
    short = "lof"

    def __init__(self, n_neighbors=20, contamination=0.05):
        self.params = dict(n_neighbors=n_neighbors, contamination=contamination)

    def fit_predict_anomaly(self, X):
        if not HAS_SKLEARN:
            raise RuntimeError("scikit-learn is not installed")
        if X.shape[0] < max(3, self.params["n_neighbors"] + 1):
            return np.zeros(X.shape[0]), np.zeros(X.shape[0], dtype=int)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = LocalOutlierFactor(**self.params).fit(X)
            rawscores = -m.negative_outlier_factor_
            labels = np.where(m.fit_predict(X) == -1, 1, 0).astype(int)
        return rawscores, labels


class OneClassSvmModel:
    name = "One-Class SVM"
    short = "svm"

    def __init__(self, nu=0.05, kernel="rbf", gamma="scale"):
        self.params = dict(nu=nu, kernel=kernel, gamma=gamma)

    def fit_predict_anomaly(self, X):
        if not HAS_SKLEARN:
            raise RuntimeError("scikit-learn is not installed")
        if X.shape[0] < 4:
            return np.zeros(X.shape[0]), np.zeros(X.shape[0], dtype=int)
        sc = StandardScaler()
        Xs = sc.fit_transform(X)
        m = OneClassSVM(**self.params).fit(Xs)
        raw = -m.decision_function(Xs)
        labels = np.where(raw > 0, 1, 0).astype(int)
        return raw, labels


class NanoAutoencoderModel:
    """Minimal MLP autoencoder (numpy, no heavy dependencies).

    Learns to reconstruct the (centred/scaled) normal patterns; events that
    reconstruct badly are scored anomalous.
    """

    name = "Nano Autoencoder"
    short = "ae"

    def __init__(self, hidden_dim=24, epochs=40, lr=0.02, latent=None):
        self.hidden_dim = hidden_dim
        self.epochs = epochs
        self.lr = lr
        self.latent = latent
        self.mean_ = None
        self.std_ = None
        self.W1 = self.b1 = self.W2 = self.b2 = None

    def _prep(self, X):
        Xc = X - self.mean_
        Xc = Xc / np.where(self.std_ > 1e-9, self.std_, 1.0)
        return Xc

    def fit_predict_anomaly(self, X):
        rng = np.random.RandomState(7)
        n, d = X.shape
        if n < 5 or d < 2:
            return np.zeros(n), np.zeros(n, dtype=int)
        self.mean_ = X.mean(axis=0)
        self.std_ = X.std(axis=0)
        Xs = self._prep(X)

        h = self.hidden_dim
        self.W1 = rng.randn(d, h) * np.sqrt(2.0 / d)
        self.b1 = np.zeros(h)
        self.W2 = rng.randn(h, d) * np.sqrt(2.0 / h)
        self.b2 = np.zeros(d)

        for _ in range(self.epochs):
            idx = rng.permutation(n)[: min(n, 256)]
            batch = Xs[idx]
            z = np.tanh(batch @ self.W1 + self.b1)
            rec = z @ self.W2 + self.b2
            err = rec - batch
            grad_z = err @ self.W2.T
            gate = 1 - z * z
            gradW1 = batch.T @ (grad_z * gate)
            gradB1 = (grad_z * gate).sum(axis=0)
            gradW2 = z.T @ err
            gradB2 = err.sum(axis=0)
            scale = 1.0 / batch.shape[0]
            self.W1 -= self.lr * scale * gradW1
            self.b1 -= self.lr * scale * gradB1
            self.W2 -= self.lr * scale * gradW2
            self.b2 -= self.lr * scale * gradB2

        z = np.tanh(Xs @ self.W1 + self.b1)
        rec = z @ self.W2 + self.b2
        raw = np.sqrt(((rec - Xs) ** 2).sum(axis=1))
        labels = _flag_top(raw)
        return raw, labels


MODELS = {
    "if": dict(model=IsolationForestModel, default=True),
    "lof": dict(model=LocalOutlierFactorModel, default=False),
    "svm": dict(model=OneClassSvmModel, default=False),
    "ae": dict(model=NanoAutoencoderModel, default=True),
}


def get_models(selection="if,ae", **kwargs):
    """Instantiate the requested models, defaulting with sensible config."""
    keys = [k.strip() for k in selection.split(",") if k.strip() in MODELS]
    if not keys:
        keys = [k for k, v in MODELS.items() if v["default"]]
    out = []
    for k in keys:
        spec = MODELS[k]
        params = kwargs.get(k, {})
        out.append((k, spec["model"](**params)))
    return out


def fit_all(X, selection, **kwargs):
    """Run every selected detector, returning (model_key, name, raw_scores,
    labels0) tuples."""
    results = []
    for key, model in get_models(selection, **kwargs):
        raw, lab = model.fit_predict_anomaly(X)
        results.append((key, model.name, raw, lab))
    return results


def _flag_top(scores, contamination=0.05):
    """Flag the top 'contamination' fraction as anomalies (label == 1)."""
    s = np.asarray(scores, dtype=float)
    n = s.shape[0]
    labels = np.zeros(n, dtype=int)
    if n == 0:
        return labels
    valid = ~np.isnan(s)
    k = max(1, int(round(n * contamination)))
    order = np.argsort(-np.where(valid, s, -np.inf), kind="mergesort")
    labels[order[:k]] = 1
    return labels