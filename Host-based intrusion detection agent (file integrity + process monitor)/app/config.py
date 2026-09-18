import json
import os

APP_NAME = "HIDS Agent"
APP_VERSION = "1.1.0"

if os.name == "nt":
    _base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    DATA_DIR = os.path.join(_base, "HIDS_Agent")
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".hids_agent")

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
DB_PATH = os.path.join(DATA_DIR, "agent.db")

DEFAULTS = {
    "fim_enabled": True,
    "process_enabled": True,
    "fim_watch_dirs": [],
    "scan_interval_sec": 300,
    "process_interval_sec": 60,
    "hash_algorithm": "sha256",
    "max_file_size_mb": 100,
    "auto_whitelist_processes": True,
    "high_cpu_threshold": 80.0,
    "high_mem_threshold_mb": 1024,
    "statusbar_min_severity": 1,
}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_config():
    ensure_data_dir()
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            for k, v in stored.items():
                if k in cfg:
                    cfg[k] = v
    except (FileNotFoundError, json.JSONDecodeError):
        save_config(cfg)
    return cfg


def save_config(cfg):
    ensure_data_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


def fmt_bytes(n):
    if n is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_secs(s):
    if s < 60:
        return f"{s}s"
    m = int(s // 60)
    r = int(s % 60)
    if m < 60:
        return f"{m}m {r}s"
    return f"{m // 60}h {m % 60}m"