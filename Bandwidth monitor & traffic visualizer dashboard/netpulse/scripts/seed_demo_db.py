"""Seed the NetPulse SQLite DB with 7 days of plausible synthetic data.

Run:  python scripts/seed_demo_db.py [--days 7]
Used for demoing the History tab without waiting a week.
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from storage.database import Database, ProcessRow, SampleRow  # noqa: E402
from utils.paths import db_path  # noqa: E402


def main() -> int:
    """Generate and insert synthetic samples."""
    parser = argparse.ArgumentParser(prog="seed_demo_db")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    db = Database(path=db_path())
    db.open()

    random.seed(42)
    now = time.time()
    step = 60  # one row per minute per iface
    n_rows = 0
    processes = [("chrome.exe", 0.35), ("steam.exe", 0.25), ("spotify.exe", 0.15), ("svchost.exe", 0.1)]

    for day in range(args.days):
        day_start = now - (args.days - day) * 86400
        for minute in range(0, 24 * 60, step // 60):
            ts = day_start + minute * 60
            hour = time.localtime(ts).tm_hour
            # day-night curve + noise
            load = 0.3 + 0.7 * math.exp(-((hour - 14) ** 2) / 40) + random.random() * 0.15
            down = int(load * 2.5e6 * 60)  # bytes over the minute
            up = int(down * 0.25)
            db.enqueue_sample(SampleRow(ts_ms=int(ts * 1000), iface="Ethernet", bytes_sent=up, bytes_recv=down))
            db.enqueue_sample(SampleRow(ts_ms=int(ts * 1000), iface="Wi-Fi", bytes_sent=up // 4, bytes_recv=down // 6))
            for pname, share in processes:
                db.enqueue_process_sample(
                    ProcessRow(ts_ms=int(ts * 1000), pid=abs(hash(pname)) % 30000, process_name=pname,
                               bytes_sent=int(up * share), bytes_recv=int(down * share))
                )
            n_rows += 5

    db._drain()
    print(f"seeded {n_rows} rows into {db_path()} ({args.days} days)")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
