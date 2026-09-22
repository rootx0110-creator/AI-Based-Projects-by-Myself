"""Extraction view: device list, method choice, threaded worker, live log."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .. import adb, extraction
from ..widgets import Card, add_row, make_table

METHOD_KEYS = ["adb_backup", "packages", "screenshot", "demo"]


class ExtractWorker(QThread):
    sig_log = Signal(str)
    sig_progress = Signal(int)
    sig_done = Signal(dict)

    def __init__(self, case_number, case_dir, method, adb_path, serial):
        super().__init__()
        self.case_number = case_number
        self.case_dir = case_dir
        self.method = method
        self.adb_path = adb_path
        self.serial = serial

    def run(self) -> None:
        try:
            record = extraction.run_extraction(
                self.case_number, self.case_dir, self.method,
                adb_path=self.adb_path, serial=self.serial,
                log=lambda m: self.sig_log.emit(m),
                progress=lambda v: self.sig_progress.emit(v),
            )
        except Exception as exc:  # keep the UI alive on any worker error
            record = {
                "method": self.method, "status": "failed",
                "detail": f"worker exception: {exc}",
                "evidence_files": [], "artifact_counts": {},
            }
        self.sig_done.emit(record)


class ExtractionView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        self.worker: ExtractWorker | None = None
        self.serial: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        cols = QHBoxLayout()
        cols.setSpacing(16)

        # ------------------------------------------------- device / method --
        left = Card("Device & method")
        left_l = QVBoxLayout()
        dev_row = QHBoxLayout()
        self.btn_refresh = QPushButton("⟳ Refresh devices")
        self.btn_info = QPushButton("Read device info")
        self.btn_refresh.setProperty("cssClass", "violet")
        dev_row.addWidget(self.btn_refresh)
        dev_row.addWidget(self.btn_info)
        dev_row.addStretch(1)
        left_l.addLayout(dev_row)

        self.dev_tbl = make_table(["Serial", "State", "Model", "Device"])
        self.dev_tbl.horizontalHeader().setStretchLastSection(False)
        self.dev_tbl.setColumnWidth(0, 130)
        self.dev_tbl.setColumnWidth(1, 90)
        self.dev_tbl.setColumnWidth(2, 120)
        self.dev_tbl.setMaximumHeight(140)
        left_l.addWidget(self.dev_tbl)
        self.dev_tbl.itemSelectionChanged.connect(self._device_selected)

        self.radios: dict[str, QRadioButton] = {}
        for key in METHOD_KEYS:
            rb = QRadioButton(extraction.METHODS[key])
            if key == "adb_backup":
                rb.setChecked(True)
            self.radios[key] = rb
            left_l.addWidget(rb)

        self.btn_start = QPushButton("▶  Start extraction")
        self.btn_start.setProperty("cssClass", "primary")
        left_l.addWidget(self.btn_start)
        left.add(left_l)
        left.setFixedWidth(430)
        cols.addWidget(left)

        # ---------------------------------------------------------- log --
        right = Card("Acquisition log")
        r_l = QVBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.log = QPlainTextEdit()
        self.log.setObjectName("logBox")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Extraction output appears here ...")
        r_l.addWidget(self.progress)
        r_l.addWidget(self.log, 1)
        right.add(r_l)
        cols.addWidget(right, 1)

        lay.addLayout(cols, 1)

        hist_card = Card("Extraction history (active case)")
        self.hist_tbl = make_table(
            ["Started", "Method", "Status", "Device", "Evidence", "Artifacts", "Detail"]
        )
        hist_card.add(self.hist_tbl, 1)
        lay.addWidget(hist_card)

        self.btn_refresh.clicked.connect(self.refresh_devices)
        self.btn_info.clicked.connect(self.read_device_info)
        self.btn_start.clicked.connect(self.start)

    # ------------------------------------------------------------ device --
    def _selected_serial(self) -> str | None:
        row = self.dev_tbl.currentRow()
        return self.dev_tbl.item(row, 0).text() if row >= 0 else None

    def _device_selected(self) -> None:
        self.serial = self._selected_serial()

    def refresh_devices(self) -> None:
        self.dev_tbl.setRowCount(0)
        if not self.main.adb_path:
            self._log("[adb] adb executable not found — connect methods disabled; use Demo dataset.")
            return
        devs = adb.list_devices(self.main.adb_path)
        for d in devs:
            add_row(self.dev_tbl, [
                d.get("serial", "?"), d.get("state", "?"),
                d.get("model", ""), d.get("device", ""),
            ])
        self._log(f"[adb] {len(devs)} device(s) attached")

    def read_device_info(self) -> None:
        serial = self._selected_serial()
        if not serial or not self.main.adb_path:
            self._log("[adb] select a device first")
            return
        info = adb.device_info(self.main.adb_path, serial)
        self._log("[device] " + ", ".join(f"{k}={v}" for k, v in info.items() if v))

    # ----------------------------------------------------------- extract --
    def _selected_method(self) -> str:
        for key, rb in self.radios.items():
            if rb.isChecked():
                return key
        return "adb_backup"

    def start(self) -> None:
        case = self.main.active_case()
        if not case:
            self._log("[error] no active case — create one in Case Manager first")
            return
        if self.worker and self.worker.isRunning():
            self._log("[busy] extraction already running")
            return
        method = self._selected_method()
        serial = self._selected_serial()
        if method != "demo" and (not self.main.adb_path or not serial):
            self._log("[error] this method needs adb and a selected device (or choose Demo dataset)")
            return
        self.btn_start.setEnabled(False)
        self.progress.setValue(2)
        self._log(f"=== {extraction.METHODS[method]} — case {case['case_number']} ===")
        self.worker = ExtractWorker(
            case["case_number"],
            self.main.store.case_dir(case["case_number"]),
            method, self.main.adb_path, serial,
        )
        self.worker.sig_log.connect(self._log)
        self.worker.sig_progress.connect(self.progress.setValue)
        self.worker.sig_done.connect(self._finished)
        self.worker.start()

    def _finished(self, record: dict) -> None:
        case = self.main.active_case()
        if case:
            store = self.main.store
            cdir = store.case_dir(case["case_number"])
            for fname in record.get("evidence_files", []):
                fpath = os.path.join(cdir, "evidence", fname)
                if os.path.isfile(fpath):
                    digest = store.log_evidence(
                        case["case_number"], fname, fpath,
                        record.get("method_label", record.get("method", "")),
                    )
                    self._log(f"[hash] {fname} sha256={digest}")
            record["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            store.add_extraction(case["case_number"], record)
        self.progress.setValue(100)
        self.btn_start.setEnabled(True)
        self.main.refresh_all()

    def _log(self, msg: str) -> None:
        self.log.appendPlainText(msg)

    # ------------------------------------------------------------ refresh --
    def refresh(self) -> None:
        case = self.main.active_case()
        self.hist_tbl.setRowCount(0)
        if not case:
            return
        for rec in reversed(case.get("extractions", [])):
            counts = rec.get("artifact_counts", {})
            add_row(self.hist_tbl, [
                rec.get("finished") or rec.get("started") or "—",
                rec.get("method_label", rec.get("method", "")),
                rec.get("status", ""),
                rec.get("device", "") or "—",
                ", ".join(rec.get("evidence_files", [])) or "—",
                ", ".join(f"{k}:{v}" for k, v in counts.items()) or "—",
                rec.get("detail", "") or "—",
            ])
