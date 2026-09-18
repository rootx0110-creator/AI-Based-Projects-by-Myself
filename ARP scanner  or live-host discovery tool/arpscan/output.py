"""Output formatting: human table, JSON, and CSV."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from .models import Host


def format_table(hosts: List[Host]) -> str:
    """Render hosts as an aligned plain-text table."""
    if not hosts:
        return "No live hosts found.\n"
    rows = [[h.ip, h.mac, h.vendor or ""] for h in hosts]
    widths = [max(len(r[i]) for r in rows) for i in range(3)]
    widths = [
        max(widths[0], len("IP")),
        max(widths[1], len("MAC address")),
        max(widths[2], len("Vendor")),
    ]
    header = (
        f"{'IP'.ljust(widths[0])}  {'MAC address'.ljust(widths[1])}  "
        f"{'Vendor'.ljust(widths[2])}"
    )
    sep = f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}"
    lines = [header, sep]
    for ip, mac, vendor in rows:
        lines.append(
            f"{ip.ljust(widths[0])}  {mac.ljust(widths[1])}  {vendor.ljust(widths[2])}"
        )
    return "\n".join(lines) + "\n"


def format_json(hosts: List[Host]) -> str:
    """Render hosts as a JSON array of objects."""
    return json.dumps([h.to_dict() for h in hosts], indent=2) + "\n"


def format_csv(hosts: List[Host]) -> str:
    """Render hosts as CSV with a header row."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ip", "mac", "vendor"])
    for h in hosts:
        writer.writerow([h.ip, h.mac, h.vendor or ""])
    return buf.getvalue()


FORMATTERS = {
    "table": format_table,
    "json": format_json,
    "csv": format_csv,
}


def format_hosts(hosts: List[Host], fmt: str = "table") -> str:
    """Format hosts with the named formatter (``table``, ``json``, ``csv``)."""
    try:
        return FORMATTERS[fmt](hosts)
    except KeyError:
        raise ValueError(
            f"unknown output format {fmt!r} (choose from {', '.join(FORMATTERS)})"
        ) from None