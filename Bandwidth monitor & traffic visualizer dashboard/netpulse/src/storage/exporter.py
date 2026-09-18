"""Export helpers: CSV, JSON and PNG chart snapshots."""
from __future__ import annotations

import csv
import time
import json
import logging
import os
from typing import Any, Iterable, Mapping, Sequence

from utils.paths import appdata_dir

log = logging.getLogger(__name__)


def export_csv(path: str, rows: Iterable[Mapping[str, Any]]) -> str:
    """Write rows (dicts) to a CSV file; returns the path written."""
    rows = list(rows)
    if not rows:
        raise ValueError("no data to export")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info("exported %d rows to %s", len(rows), path)
    return path


def export_json(path: str, data: Any) -> str:
    """Write any JSON-serialisable payload; returns the path written."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    log.info("exported JSON to %s", path)
    return path


def export_png(widget: Any, path: str) -> str:
    """Grab a Qt widget (chart) to a PNG file; returns the path written."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pixmap = widget.grab()
    pixmap.save(path, "PNG")
    log.info("exported PNG to %s", path)
    return path


def default_export_dir() -> str:
    """Default export folder under %APPDATA%/NetPulse/exports."""
    path = os.path.join(appdata_dir(), "exports")
    os.makedirs(path, exist_ok=True)
    return path


def suggest_filename(prefix: str, ext: str) -> str:
    """Timestamped suggestion like 'netpulse-20260912-153000.csv'."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}.{ext}"

