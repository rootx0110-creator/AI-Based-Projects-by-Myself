import time
from datetime import datetime

import psutil

_REFRESH_ATTRS = ["pid", "name", "username", "cpu_percent", "memory_info", "exe",
                  "create_time", "status"]


def proc_key(proc):
    exe = (proc.get("exe") or "").strip().lower()
    if exe:
        return "exe:" + exe
    return "name:" + (proc.get("name") or "?").lower()


def snapshot(attrs=_REFRESH_ATTRS):
    """Return a list of running process rows (already opened via process_iter)."""
    rows = []
    for p in psutil.process_iter(attrs):
        info = p.info
        try:
            mem = info.get("memory_info")
            mem_mb = round((mem.rss or 0) / (1024 * 1024), 1) if mem else 0.0
            created = info.get("create_time")
            started = ""
            if created:
                started = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
            rows.append({
                "pid": info["pid"],
                "name": info["name"] or "?",
                "user": info.get("username") or "system",
                "cpu": round(info.get("cpu_percent") or 0.0, 1),
                "mem_mb": mem_mb,
                "exe": info.get("exe") or "",
                "started": started,
                "status": info.get("status") or "",
                "key": proc_key(info),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue
    rows.sort(key=lambda r: r["pid"])
    return rows


class ProcessEngine:
    def __init__(self, storage, config):
        self.storage = storage
        self.config = config

    def snapshot(self):
        return snapshot()

    def whitelist_rows(self):
        return self.storage.process_keys()

    def whitelist_keys(self):
        return {r["key"] for r in self.whitelist_rows()}

    def update_whitelist(self, rows):
        self.storage.save_process_snapshot(rows)

    def new_processes(self, rows):
        known = self.whitelist_keys()
        return [r for r in rows if r["key"] not in known]

    def resource_hogs(self, rows):
        cpu_t = self.config.get("high_cpu_threshold", 80.0)
        mem_t = self.config.get("high_mem_threshold_mb", 1024)
        offenders = []
        for r in rows:
            if r["name"].lower() in ("system idle process",) or r["pid"] <= 4:
                continue
            if r["cpu"] >= cpu_t:
                offenders.append((r, "cpu", r["cpu"]))
            if r["mem_mb"] >= mem_t:
                offenders.append((r, "mem", r["mem_mb"]))
        return offenders