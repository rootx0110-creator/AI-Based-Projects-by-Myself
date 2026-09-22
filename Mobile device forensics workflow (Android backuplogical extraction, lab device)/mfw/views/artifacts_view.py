"""Artifacts browser: type filter, search, CSV export."""
from __future__ import annotations

import csv
import os

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..widgets import Card, add_row, make_table

ARTIFACT_COLUMNS = {
    "calls": (["Date / time", "Number", "Type", "Duration (s)"],
              ["datetime", "number", "call_type", "duration_s"]),
    "sms": (["Date / time", "Address", "Direction", "Body"],
            ["datetime", "address", "sms_type", "body"]),
    "contacts": (["Name", "Phone"], ["name", "phone"]),
    "apps": (["Package", "Kind"], ["package", "kind"]),
}


class ArtifactsView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        bar = Card()
        h = QHBoxLayout()
        self.lbl_case = QLabel("No active case")
        self.lbl_case.setProperty("h2", "true")
        h.addWidget(self.lbl_case)
        h.addStretch(1)
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["calls", "sms", "contacts", "apps"])
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search …")
        self.txt_search.setFixedWidth(240)
        self.btn_export = QPushButton("⭳ Export CSV")
        h.addWidget(QLabel("Type:"))
        h.addWidget(self.cmb_type)
        h.addWidget(self.txt_search)
        h.addWidget(self.btn_export)
        bar.add(h)
        lay.addWidget(bar)

        tbl_card = Card()
        v = QVBoxLayout()
        self.tbl = make_table(["—"])
        v.addWidget(self.tbl, 1)
        self.lbl_count = QLabel("")
        self.lbl_count.setProperty("small", "true")
        v.addWidget(self.lbl_count)
        tbl_card.add(v)
        lay.addWidget(tbl_card, 1)

        self.cmb_type.currentTextChanged.connect(self.refresh)
        self.txt_search.textChanged.connect(self.refresh)
        self.btn_export.clicked.connect(self.export_csv)

    # ------------------------------------------------------------ helpers --
    def _rows(self, kind: str) -> list[dict]:
        case = self.main.active_case()
        if not case:
            return []
        import json
        path = os.path.join(
            self.main.store.case_dir(case["case_number"]),
            "extracted", "artifacts.json",
        )
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return []
        return data.get(kind, [])

    # ------------------------------------------------------------ export --
    def export_csv(self) -> None:
        case = self.main.active_case()
        if not case:
            return
        kind = self.cmb_type.currentText()
        rows = self._rows(kind)
        headers, keys = ARTIFACT_COLUMNS[kind]
        out_dir = os.path.join(self.main.store.case_dir(case["case_number"]), "exports")
        os.makedirs(out_dir, exist_ok=True)
        stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"{kind}_{stamp}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(headers)
            for r in rows:
                w.writerow([r.get(k, "") for k in keys])
        self.main.store.audit(case["case_number"], "EXPORT_CSV", f"{kind} -> {os.path.basename(path)}")
        QMessageBox.information(self, "Export complete", f"Saved:\n{path}")

    # ------------------------------------------------------------ refresh --
    def refresh(self) -> None:
        case = self.main.active_case()
        kind = self.cmb_type.currentText()
        headers, keys = ARTIFACT_COLUMNS[kind]
        self.tbl.clear()
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)

        if not case:
            self.lbl_case.setText("No active case — create one in Case Manager")
            self.tbl.setRowCount(0)
            self.lbl_count.setText("")
            return
        self.lbl_case.setText(f"Artifacts — {case['case_number']}")

        term = self.txt_search.text().strip().lower()
        rows = self._rows(kind)
        self.tbl.setRowCount(0)
        shown = 0
        for r in rows:
            joined = " ".join(str(r.get(k, "")) for k in keys).lower()
            if term and term not in joined:
                continue
            add_row(self.tbl, [str(r.get(k, "")) for k in keys])
            shown += 1
            if shown >= 2000:
                break
        self.lbl_count.setText(f"{shown} of {len(rows)} records shown" + (f" (filter: '{term}')" if term else ""))
