import hashlib
import os


def hash_file(path, algo="sha256", max_bytes=None):
    """Hash a single file. Returns (hexdigest, size_bytes) or (None, size) if skipped."""
    if max_bytes is not None and os.path.getsize(path) > max_bytes:
        return None, os.path.getsize(path)
    h = hashlib.new(algo)
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def _iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _: None):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            yield os.path.join(dirpath, fn)


class BaselineResult:
    def __init__(self, path, total=0, skipped=0, errors=0):
        self.path = path
        self.total = total
        self.skipped = skipped
        self.errors = errors


class ScanResult:
    def __init__(self, path):
        self.path = path
        self.added = []
        self.modified = []
        self.removed = []
        self.unchanged = 0
        self.skipped = 0
        self.errors = 0

    @property
    def changed(self):
        return len(self.added) + len(self.modified) + len(self.removed)


class FIMEngine:
    """File Integrity Monitor: creates baselines (hash manifest) and detects drift."""

    def __init__(self, storage, config):
        self.storage = storage
        self.config = config

    def _max_bytes(self):
        mb = self.config.get("max_file_size_mb", 100)
        return int(mb * 1024 * 1024)

    def _algo(self):
        return self.config.get("hash_algorithm", "sha256")

    def _dir_baseline_files(self, path):
        return {r["rel_path"]: r for r in self.storage.baseline_files(path)}

    def build_baseline(self, path, progress_cb=None):
        """Walk path, hash everything, store snapshot in DB."""
        total = 0
        skipped = 0
        errors = 0

        paths = []
        for fp in _iter_files(path):
            try:
                os.stat(fp)
            except OSError:
                continue
            paths.append(fp)

        self.storage.clear_baseline(path)
        for i, fp in enumerate(paths, 1):
            if progress_cb:
                need_cancel = progress_cb(i, len(paths), fp)
                if need_cancel:
                    return BaselineResult(path, total=i, skipped=skipped)
            try:
                digest, size = hash_file(fp, self._algo(), self._max_bytes())
                if digest is None:
                    skipped += 1
                    continue
                rel = os.path.relpath(fp, path)
                mtime = os.path.getmtime(fp)
                self.storage.upsert_file(path, rel, digest, size, mtime)
                total += 1
            except OSError:
                errors += 1

        if progress_cb:
            progress_cb(len(paths), len(paths), "")
        return BaselineResult(path, total=total, skipped=skipped, errors=errors)

    def scan(self, path, progress_cb=None):
        """Compare live filesystem against baseline."""
        result = ScanResult(path)
        baseline = self._dir_baseline_files(path)
        current = {}
        paths = []
        for fp in _iter_files(path):
            try:
                os.stat(fp)
            except OSError:
                continue
            paths.append(fp)

        for i, fp in enumerate(paths, 1):
            if progress_cb:
                if progress_cb(i, len(paths), fp):
                    return result
            rel = os.path.relpath(fp, path)
            prev = baseline.get(rel)
            if prev is None:
                result.added.append(rel)
                continue
            try:
                digest, size = hash_file(fp, self._algo(), self._max_bytes())
                if digest is None:
                    result.skipped += 1
                    del baseline[rel]
                    continue
            except OSError:
                result.errors = getattr(result, "errors", 0) + 1
                del baseline[rel]
                continue
            current[rel] = digest
            if digest != prev["file_hash"] or size != prev["size"]:
                result.modified.append(rel)
            else:
                result.unchanged += 1

        baseline_set = set(baseline) - set(current)
        result.removed = sorted(rel for rel in baseline_set)

        if progress_cb:
            progress_cb(len(paths), len(paths), "")
        return result


