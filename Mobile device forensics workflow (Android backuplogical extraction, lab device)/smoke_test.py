"""Headless smoke test: app + case + demo extraction + HTML report (offscreen).

Run:  QT_QPA_PLATFORM=offscreen python smoke_test.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)

    from mfw.main_window import MainWindow
    from mfw import extraction, report
    from mfw.case_store import app_dir

    win = MainWindow()
    win.show()
    win.refresh_all()

    store = win.store
    case = store.active()
    assert case, "no active case after startup"

    cdir = store.case_dir(case["case_number"])

    # 1. offline demo extraction (headless, no threads)
    rec = extraction.run_extraction(
        case["case_number"], cdir, "demo", log=print)
    assert rec["status"] == "completed", rec
    assert sum(rec["artifact_counts"].values()) > 0, rec

    # 2. evidence hashing -> chain of custody
    ev_dir = os.path.join(cdir, "evidence")
    for fname in rec["evidence_files"]:
        digest = store.log_evidence(case["case_number"], fname,
                                    os.path.join(ev_dir, fname), "Demo dataset")
        assert len(digest) == 64

    # 3. HTML report build + save
    arts = {"calls": [], "sms": [], "contacts": [], "apps": []}
    import json
    with open(os.path.join(cdir, "extracted", "artifacts.json"), encoding="utf-8") as fh:
        arts = json.load(fh)
    dev_path = os.path.join(cdir, "extracted", "device_info.json")
    device_info = json.load(open(dev_path, encoding="utf-8")) if os.path.exists(dev_path) else None
    html_text = report.build_html(
        case, device_info, arts, rec,
        store.chain_entries(case["case_number"]),
        {"title": "Smoke Test Report", "classification": "TEST", "summary": "auto"},
    )
    path = report.save_report(cdir, f"smoke_test_{os.getpid()}.html", html_text)
    size = os.path.getsize(path)
    assert size > 5000, f"report too small: {size}"
    print(f"[OK] app window, case, extraction, hash, report ({size} bytes) -> {path}")
    print(f"[OK] data dir: {os.path.join(app_dir(), 'data')}")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
