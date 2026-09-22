"""Case store: CRUD, persistence, evidence hashing, chain of custody, audit.

Single JSON index (cases_index.json) + per-case folder with metadata.json,
audit.txt, chain_of_custody.csv and evidence/extracted/reports/exports dirs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import threading
from datetime import datetime
from typing import Any

TS_FMT = "%Y-%m-%d %H:%M:%S"
FILE_TS_FMT = "%Y%m%d_%H%M%S"


def now_str() -> str:
    return datetime.now().strftime(TS_FMT)


def file_ts() -> str:
    return datetime.now().strftime(FILE_TS_FMT)


def app_dir() -> str:
    """Directory where the app lives (exe folder when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    d = os.path.join(app_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class CaseStore:
    """Thread-safe persistence for cases and forensic records."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.index_path = os.path.join(data_dir(), "cases_index.json")
        self.state_path = os.path.join(data_dir(), "state.json")
        self.audit_path = os.path.join(data_dir(), "audit.log")
        self.cases: dict[str, dict[str, Any]] = {}
        self.active_case: str | None = None
        self._load()

    # ------------------------------------------------------------ loading --
    def _load(self) -> None:
        with self._lock:
            if os.path.exists(self.index_path):
                try:
                    with open(self.index_path, "r", encoding="utf-8") as fh:
                        self.cases = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    self.cases = {}
            else:
                self.cases = {}
            if os.path.exists(self.state_path):
                try:
                    with open(self.state_path, "r", encoding="utf-8") as fh:
                        self.active_case = json.load(fh).get("active_case")
                except (json.JSONDecodeError, OSError):
                    self.active_case = None
            if self.active_case not in self.cases:
                self.active_case = None

    def _save_index(self) -> None:
        with open(self.index_path, "w", encoding="utf-8") as fh:
            json.dump(self.cases, fh, indent=2)

    def _save_state(self) -> None:
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump({"active_case": self.active_case}, fh, indent=2)

    # -------------------------------------------------------------- cases --
    def case_dir(self, case_number: str) -> str:
        safe = "".join(c for c in case_number if c.isalnum() or c in "-_")
        d = os.path.join(data_dir(), "cases", safe)
        for sub in ("evidence", "extracted", "reports", "exports"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        return d

    def create_case(
        self,
        case_number: str,
        title: str,
        examiner: str,
        agency: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            if case_number in self.cases:
                raise ValueError(f"Case '{case_number}' already exists.")
            rec: dict[str, Any] = {
                "case_number": case_number,
                "title": title or case_number,
                "examiner": examiner or "Unknown",
                "agency": agency or "",
                "notes": notes or "",
                "created": now_str(),
                "status": "Open",
                "extractions": [],
                "report_history": [],
            }
            self.cases[case_number] = rec
            cdir = self.case_dir(case_number)
            with open(os.path.join(cdir, "metadata.json"), "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2)
            self._save_index()
            self.set_active_case(case_number, silent=False)
            self.audit(case_number, "CASE_CREATED", f"title='{title}' examiner='{examiner}'")
            return rec

    def get_case(self, case_number: str) -> dict[str, Any] | None:
        with self._lock:
            return self.cases.get(case_number)

    def list_cases(self) -> list[dict[str, Any]]:
        with self._lock:
            cases = sorted(self.cases.values(), key=lambda c: c.get("created", ""), reverse=True)
            return [dict(c) for c in cases]

    def active(self) -> dict[str, Any] | None:
        with self._lock:
            return self.cases.get(self.active_case) if self.active_case else None

    def set_active_case(self, case_number: str | None, silent: bool = True) -> None:
        with self._lock:
            if case_number and case_number not in self.cases:
                raise ValueError("Unknown case")
            self.active_case = case_number
            self._save_state()
        if case_number and not silent:
            self.audit(case_number, "CASE_ACTIVATED", "case set active")

    def active_case_number(self) -> str | None:
        with self._lock:
            return self.active_case

    def delete_case(self, case_number: str) -> None:
        """Remove a case record and its entire case folder."""
        import shutil
        with self._lock:
            self.cases.pop(case_number, None)
            self._save_index()
            if self.active_case == case_number:
                self.active_case = None
                self._save_state()
            cdir = os.path.join(data_dir(), "cases", case_number)
            if os.path.isdir(cdir):
                shutil.rmtree(cdir, ignore_errors=True)
        self.audit(case_number, "CASE_DELETED", "case and folder removed")

    # ----------------------------------------------------------- evidence --
    def log_evidence(
        self,
        case_number: str,
        filename: str,
        filepath: str,
        method: str,
        note: str = "",
    ) -> str:
        """Hash an evidence file and append to chain-of-custody CSV."""
        digest = sha256_file(filepath)
        cdir = self.case_dir(case_number)
        coc_path = os.path.join(cdir, "chain_of_custody.csv")
        new_file = not os.path.exists(coc_path)
        with self._lock, open(coc_path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new_file:
                w.writerow(["timestamp", "case_number", "item", "sha256", "method", "examiner", "note"])
            w.writerow([
                now_str(), case_number, filename, digest, method,
                (self.cases.get(case_number, {}) or {}).get("examiner", "Unknown"),
                note,
            ])
        self.audit(case_number, "EVIDENCE_ADDED", f"{filename} sha256={digest[:16]}... method={method}")
        return digest

    def chain_entries(self, case_number: str) -> list[list[str]]:
        coc_path = os.path.join(self.case_dir(case_number), "chain_of_custody.csv")
        rows: list[list[str]] = []
        if os.path.exists(coc_path):
            with open(coc_path, "r", newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.reader(fh)][1:]
        return rows

    # --------------------------------------------------------- extraction --
    def add_extraction(self, case_number: str, record: dict[str, Any]) -> None:
        with self._lock:
            rec = self.cases.setdefault(case_number, {})
            rec.setdefault("extractions", []).append(record)
            self._save_index()
            cdir = self.case_dir(case_number)
            with open(os.path.join(cdir, "metadata.json"), "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2)
        self.audit(case_number, "EXTRACTION", f"method={record.get('method')} status={record.get('status')}")

    def add_report_history(self, case_number: str, record: dict[str, Any]) -> None:
        with self._lock:
            rec = self.cases.setdefault(case_number, {})
            rec.setdefault("report_history", []).append(record)
            self._save_index()

    # -------------------------------------------------------------- audit --
    def audit(self, case_number: str | None, event: str, detail: str = "") -> None:
        line = f"{now_str()} | {case_number or '-'} | {event} | {detail}"
        with self._lock:
            try:
                with open(self.audit_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                pass
            if case_number:
                try:
                    with open(
                        os.path.join(self.case_dir(case_number), "audit.txt"),
                        "a", encoding="utf-8",
                    ) as fh:
                        fh.write(line + "\n")
                except OSError:
                    pass

    def audit_lines(self, limit: int = 400) -> list[str]:
        if not os.path.exists(self.audit_path):
            return []
        with open(self.audit_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        return [ln.rstrip("\n") for ln in lines[-limit:]]


def seed_first_run(store: "CaseStore") -> None:
    """Create a sample case on first run so the app opens with data."""
    if store.cases:
        return
    try:
        rec = store.create_case(
            "DEMO-001",
            "Sample matter — offline demonstration",
            "Lab Demo",
            "Digital Forensics Lab",
            "Sample case created on first run. Run a Demo dataset extraction, "
            "then download the HTML report.",
        )
        store.audit(rec["case_number"], "FIRST_RUN", "sample case seeded")
    except (OSError, ValueError):
        pass
