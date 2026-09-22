"""Report view: metadata, preview, Download HTML report, open last report."""
from __future__ import annotations

import os
import webbrowser
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import report
from ..widgets import Card


class ReportView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        self._last_report_path: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)

        # ---------------------------------------------------------- meta --
        meta_card = Card("Report details")
        form = QFormLayout()
        self.f_title = QLineEdit()
        self.f_title.setPlaceholderText("Forensic Examination Report")
        self.f_classification = QLineEdit("Unclassified / For official use")
        self.f_summary = QTextEdit()
        self.f_summary.setPlaceholderText("Summary of findings, scope, and examiner observations …")
        self.f_summary.setFixedHeight(110)
        form.addRow("Report title", self.f_title)
        form.addRow("Classification", self.f_classification)
        form.addRow("Summary", self.f_summary)
        meta_card.add(form)

        btns = QHBoxLayout()
        self.btn_generate = QPushButton("⭳  DOWNLOAD HTML REPORT")
        self.btn_generate.setProperty("cssClass", "primary")
        self.btn_generate.setToolTip("Generate the report and save it as a self-contained HTML file")
        self.btn_open_last = QPushButton("Open last report")
        self.btn_open_folder = QPushButton("Open reports folder")
        btns.addWidget(self.btn_generate)
        btns.addWidget(self.btn_open_last)
        btns.addWidget(self.btn_open_folder)
        btns.addStretch(1)
        meta_card.add(btns)
        meta_card.setFixedWidth(460)
        top.addWidget(meta_card)

        # -------------------------------------------------------- preview --
        prev_card = Card("Preview (saved HTML is the authoritative copy)")
        pv = QVBoxLayout()
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet(
            "background: rgba(6,4,18,0.55); border:1px solid rgba(255,255,255,0.09);"
            "border-radius:10px; font-family: Consolas, monospace; font-size: 11px;"
        )
        pv.addWidget(self.preview, 1)
        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("small", "true")
        pv.addWidget(self.lbl_status)
        prev_card.add(pv)
        top.addWidget(prev_card, 1)

        lay.addLayout(top, 1)

        self.btn_generate.clicked.connect(self.download_report)
        self.btn_open_last.clicked.connect(self.open_last)
        self.btn_open_folder.clicked.connect(self.open_folder)

    # --------------------------------------------------------- download --
    def _build(self) -> tuple[str, str, dict, dict] | None:
        case = self.main.active_case()
        if not case:
            QMessageBox.warning(self, "No active case", "Create a case and run an extraction first.")
            return None
        meta = {
            "title": self.f_title.text().strip() or "Forensic Examination Report",
            "classification": self.f_classification.text().strip() or "Unclassified",
            "summary": self.f_summary.toPlainText().strip(),
        }
        cdir = self.main.store.case_dir(case["case_number"])

        import json
        device_info: dict | None = None
        dev_path = os.path.join(cdir, "extracted", "device_info.json")
        if os.path.exists(dev_path):
            try:
                with open(dev_path, "r", encoding="utf-8") as fh:
                    device_info = json.load(fh)
            except (json.JSONDecodeError, OSError):
                device_info = None

        artifacts: dict[str, list] = {"calls": [], "sms": [], "contacts": [], "apps": []}
        art_path = os.path.join(cdir, "extracted", "artifacts.json")
        if os.path.exists(art_path):
            try:
                with open(art_path, "r", encoding="utf-8") as fh:
                    artifacts = json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass

        extractions = case.get("extractions", [])
        extraction_rec = extractions[-1] if extractions else None
        html_text = report.build_html(
            case, device_info, artifacts, extraction_rec,
            self.main.store.chain_entries(case["case_number"]), meta,
        )
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{case['case_number']}_{stamp}.html"
        return html_text, filename, meta, case

    def download_report(self) -> None:
        built = self._build()
        if not built:
            return
        html_text, filename, meta, case = built
        cdir = self.main.store.case_dir(case["case_number"])
        default_path = os.path.join(cdir, "reports", filename)

        # "Download" = pick destination, pre-filled with the case reports folder
        target, _filter = QFileDialog.getSaveFileName(
            self, "Download HTML report", default_path,
            "HTML report (*.html);;All files (*.*)",
        )
        if not target:
            return
        if not target.lower().endswith(".html"):
            target += ".html"
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(html_text)
        self._last_report_path = target
        self.main.store.add_report_history(case["case_number"], {
            "file": os.path.basename(target),
            "path": target,
            "title": meta["title"],
            "classification": meta["classification"],
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.main.store.audit(case["case_number"], "REPORT_DOWNLOADED",
                              f"{os.path.basename(target)} ({os.path.getsize(target)} bytes)")
        self.lbl_status.setText(f"✔ Report downloaded: {target}")
        self.main.refresh_all()
        QMessageBox.information(
            self, "Report downloaded",
            f"HTML report saved to:\n{target}\n\nOpen it in any browser.",
        )

    def open_last(self) -> None:
        case = self.main.active_case()
        path = self._last_report_path
        if not path and case:
            hist = case.get("report_history", [])
            if hist:
                path = hist[-1].get("path")
        if path and os.path.isfile(path):
            webbrowser.open("file://" + path.replace("\\", "/"))
        else:
            QMessageBox.information(self, "No report yet", "Download a report first.")

    def open_folder(self) -> None:
        case = self.main.active_case()
        if not case:
            return
        rdir = os.path.join(self.main.store.case_dir(case["case_number"]), "reports")
        os.makedirs(rdir, exist_ok=True)
        if os.name == "nt":
            os.startfile(rdir)  # type: ignore[attr-defined]
        else:
            webbrowser.open("file://" + rdir)

    # ------------------------------------------------------------ refresh --
    def refresh(self) -> None:
        case = self.main.active_case()
        if not case:
            self.lbl_status.setText("No active case.")
            self.preview.setPlainText("")
            return
        self.lbl_status.setText(
            f"Active case: {case['case_number']} — "
            f"{len(case.get('extractions', []))} extraction(s), "
            f"{len(case.get('report_history', []))} report(s) generated."
        )
        built = self._build()
        if built:
            html_text = built[0]
            self.preview.setPlainText(
                html_text[:8000] + ("\n\n… (truncated preview — download for the full report)" if len(html_text) > 8000 else "")
            )
