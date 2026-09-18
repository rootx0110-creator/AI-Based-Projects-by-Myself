"""Tests for the HTML report generator."""
from __future__ import annotations

import os
import tempfile
import time

from analytics.report import gather_report_data, render_html_report
from storage.database import Database, ProcessRow, SampleRow


def _tmp_db() -> Database:
    path = os.path.join(tempfile.mkdtemp(), "report.db")
    db = Database(path=path)
    db.open()
    return db


def test_report_contains_sections_and_data() -> None:
    db = _tmp_db()
    try:
        now = time.time()
        db.enqueue_sample(SampleRow(ts_ms=int(now * 1000), iface="eth0", bytes_sent=1500, bytes_recv=2500))
        db.enqueue_process_sample(ProcessRow(ts_ms=int(now * 1000), pid=1, process_name="chrome.exe", bytes_sent=500, bytes_recv=900))
        db._drain()

        data = gather_report_data(db, range_secs=24 * 3600)
        html = render_html_report(data)

        assert "<!DOCTYPE html>" in html
        assert "NetPulse" in html
        assert "Top talkers" in html
        assert "Daily volume" in html
        assert "chrome.exe" in html
        assert "eth0" in html or "Interfaces" in html
        # summary cards show formatted bytes
        assert "kB" in html or "KB" in html
        # SVG charts are inline
        assert "<svg" in html
    finally:
        db.close()


def test_report_empty_db_renders_gracefully() -> None:
    db = _tmp_db()
    try:
        html = render_html_report(gather_report_data(db, range_secs=24 * 3600))
        assert "No data in this range yet" in html
        assert "No per-process data" in html
        assert "No samples" in html
    finally:
        db.close()


def test_report_escapes_process_names() -> None:
    db = _tmp_db()
    try:
        now = time.time()
        db.enqueue_process_sample(
            ProcessRow(ts_ms=int(now * 1000), pid=7, process_name="<script>alert(1)</script>", bytes_sent=1, bytes_recv=1)
        )
        db._drain()
        html = render_html_report(gather_report_data(db, range_secs=3600))
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
    finally:
        db.close()
