"""Main window: sidebar navigation + stacked pages."""

from __future__ import annotations

import csv
import json
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core.models import Profile, ResultStatus, ScanReport
from ..core.scoring import failing_by_severity
from ..reporting import render_html, render_pdf
from .theme import ACCENT, MUTED, STATUS_COLORS
from .widgets import (
    CategoryBars,
    DonutChart,
    FindingsTable,
    ScoreGauge,
    SevPillDelegate,
    StatCard,
)
from .workers import ScanWorker


class MainWindow(QMainWindow):
    """Application shell: sidebar + page stack + scan orchestration."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Endpoint Hardening & Compliance Checker")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self.current_report: ScanReport | None = None
        self._worker: ScanWorker | None = None

        self._build_ui()
        self._wire_shortcuts()
        self._update_nav_state()

    # ================================================================= UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard_page())   # 0
        self.stack.addWidget(self._build_scan_page())        # 1
        self.stack.addWidget(self._build_findings_page())    # 2
        self.stack.addWidget(self._build_reports_page())     # 3
        self.stack.addWidget(self._build_about_page())       # 4
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready \u2014 read-only mode. No settings will be changed.")

    # ----------------------------------------------------------- sidebar
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(224)

        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 18, 14, 14)
        lay.setSpacing(6)

        brand = QLabel("&#127760; Hardening Checker")  # noqa: RUF001
        brand.setObjectName("BrandName")
        sub = QLabel("Endpoint compliance auditing")
        sub.setObjectName("BrandSub")

        lay.addWidget(brand)
        lay.addWidget(sub)
        lay.addSpacing(14)

        self._nav_group = QButtonGroup(self)
        self._nav_buttons: list[QPushButton] = []
        for i, (label, icon) in enumerate([
                ("Dashboard", "\U0001f4ca"),
                ("Run Scan", "\u25b6"),
                ("Findings", "\U0001f50d"),
                ("Reports", "\U0001f4c4"),
                ("About", "\u2139")]):
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c, idx=i: self.switch_page(idx))
            self._nav_group.addButton(btn, i)
            self._nav_buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch(1)

        self._nav_footer = QLabel(f"v{__version__}\nread-only audit mode")
        self._nav_footer.setObjectName("Muted")
        self._nav_footer.setStyleSheet("font-size:10.5px;")
        lay.addWidget(self._nav_footer)

        self._nav_buttons[0].setChecked(True)
        return side

    # --------------------------------------------------------- dashboard
    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(14)

        title = QLabel("Compliance Dashboard")
        title.setObjectName("H1")
        subtitle = QLabel(
            "Overview of the most recent scan on this endpoint. "
            "Run a scan to populate the dashboard.")
        subtitle.setObjectName("Muted")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # row 1: gauge + stat cards
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        gauge_card = QFrame()
        gauge_card.setObjectName("Card")
        g_lay = QVBoxLayout(gauge_card)
        g_lay.setContentsMargins(16, 12, 16, 12)
        self.gauge = ScoreGauge()
        g_lay.addWidget(self.gauge)
        row1.addWidget(gauge_card, 2)

        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)
        self.card_pass = StatCard("Passed", STATUS_COLORS["pass"])
        self.card_fail = StatCard("Failed", STATUS_COLORS["fail"])
        self.card_err = StatCard("Errors", STATUS_COLORS["error"])
        self.card_na = StatCard("N/A + Skipped", "#94a3b8")
        self.card_man = StatCard("Manual", STATUS_COLORS["manual"])
        self.card_total = StatCard("Total Checks", ACCENT)
        for i, card in enumerate([
                self.card_total, self.card_pass, self.card_fail,
                self.card_err, self.card_na, self.card_man]):
            cards_grid.addWidget(card, i // 3, i % 3)
        row1.addLayout(cards_grid, 3)
        outer.addLayout(row1, 2)

        # row 2: donut + bars
        row2 = QHBoxLayout()
        row2.setSpacing(14)
        donut_card = QFrame()
        donut_card.setObjectName("Card")
        d_lay = QVBoxLayout(donut_card)
        self.donut = DonutChart()
        d_lay.addWidget(self.donut)
        row2.addWidget(donut_card, 2)

        bars_card = QFrame()
        bars_card.setObjectName("Card")
        b_lay = QVBoxLayout(bars_card)
        self.bars = CategoryBars()
        b_lay.addWidget(self.bars)
        row2.addWidget(bars_card, 3)
        outer.addLayout(row2, 3)

        # row 3: scan info strip
        self.scan_meta = QLabel("No scan yet \u2014 go to \u2018Run Scan\u2019 to begin.")
        self.scan_meta.setObjectName("Muted")
        outer.addWidget(self.scan_meta)

        outer.addStretch(1)
        return page

    # -------------------------------------------------------------- scan
    def _build_scan_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(14)

        title = QLabel("Run Scan")
        title.setObjectName("H1")
        outer.addWidget(title)

        # options card
        card = QFrame()
        card.setObjectName("Card")
        form = QGridLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setVerticalSpacing(12)

        lbl_prof = QLabel("Benchmark profile")
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Level 1 \u2014 essential hardening", Profile.L1)
        self.profile_combo.addItem("Level 2 \u2014 strict (adds L2 rules)", Profile.L2)

        lbl_scope = QLabel("Scope")
        self.info_chk = QCheckBox("Include informational checks")
        self.info_chk.setChecked(True)
        self.manual_chk = QCheckBox("Run manual-review placeholders (no-op checks)")
        self.admin_hint = QLabel(
            "Tip: run the app elevated to unlock checks that need admin rights. "
            "Non-elevated runs simply skip those rules.")
        self.admin_hint.setObjectName("Muted")
        self.admin_hint.setWordWrap(True)

        self.scan_btn = QPushButton("\u25b6  Start scan")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setMinimumHeight(38)
        self.scan_btn.clicked.connect(self.start_scan)

        r = 0
        form.addWidget(lbl_prof, r, 0)
        form.addWidget(self.profile_combo, r, 1)
        r += 1
        form.addWidget(lbl_scope, r, 0)
        wrap = QWidget()
        w_lay = QHBoxLayout(wrap)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.addWidget(self.info_chk)
        w_lay.addWidget(self.manual_chk)
        form.addWidget(wrap, r, 1)
        r += 1
        form.addWidget(self.admin_hint, r, 1)
        r += 1
        form.addWidget(self.scan_btn, r, 1)

        form.setColumnStretch(1, 1)
        outer.addWidget(card)

        # progress card
        prog_card = QFrame()
        prog_card.setObjectName("Card")
        p_lay = QGridLayout(prog_card)
        p_lay.setContentsMargins(18, 16, 18, 16)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.stage_lbl = QLabel("Idle.")
        self.stage_lbl.setObjectName("Muted")
        self.current_lbl = QLabel("")
        self.current_lbl.setObjectName("Muted")

        p_lay.addWidget(QLabel("Progress"), 0, 0)
        p_lay.addWidget(self.progress, 0, 1)
        p_lay.addWidget(self.stage_lbl, 1, 1)
        p_lay.addWidget(self.current_lbl, 2, 1)
        p_lay.setColumnStretch(1, 1)
        outer.addWidget(prog_card)

        outer.addStretch(1)
        return page

    # ---------------------------------------------------------- findings
    def _build_findings_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(12)

        head = QHBoxLayout()
        title = QLabel("Findings")
        title.setObjectName("H1")
        self.findings_count = QLabel("")
        self.findings_count.setObjectName("Muted")
        head.addWidget(title)
        head.addSpacing(10)
        head.addWidget(self.findings_count)
        head.addStretch(1)

        self.filter_sev = QComboBox()
        self.filter_sev.addItem("All severities", "")
        for sev in ("critical", "high", "medium", "low", "info"):
            self.filter_sev.addItem(sev.capitalize(), sev)
        self.filter_st = QComboBox()
        self.filter_st.addItem("All statuses", "")
        for st in ("fail", "pass", "error", "manual", "skipped", "not_applicable"):
            self.filter_st.addItem(st.replace("_", " ").capitalize(), st)
        self.filter_q = QLineEdit()
        self.filter_q.setPlaceholderText("Search rule id, title, message\u2026")
        self.filter_q.setClearButtonEnabled(True)
        self.filter_q.setMinimumWidth(240)

        for w in (self.filter_sev, self.filter_st, self.filter_q):
            head.addWidget(w)
        outer.addLayout(head)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.findings_table = FindingsTable()
        splitter.addWidget(self.findings_table)

        detail_wrap = QFrame()
        detail_wrap.setObjectName("Panel")
        d_lay = QVBoxLayout(detail_wrap)
        d_lay.setContentsMargins(14, 12, 14, 12)
        self.detail_view = QTextBrowser()
        self.detail_view.setOpenExternalLinks(True)
        self.detail_view.setStyleSheet("QTextBrowser{background:transparent;border:none;}")
        d_lay.addWidget(self.detail_view)
        splitter.addWidget(detail_wrap)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([420, 260])
        outer.addWidget(splitter, 1)

        self.filter_sev.currentIndexChanged.connect(self._apply_filters)
        self.filter_st.currentIndexChanged.connect(self._apply_filters)
        self.filter_q.textChanged.connect(self._apply_filters)

        return page

    # ----------------------------------------------------------- reports
    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(14)

        title = QLabel("Reports")
        title.setObjectName("H1")
        sub = QLabel(
            "Generate a shareable compliance report from the most recent scan. "
            "HTML is self-contained; PDF is print-ready.")
        sub.setObjectName("Muted")
        outer.addWidget(title)
        outer.addWidget(sub)

        card = QFrame()
        card.setObjectName("Card")
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setVerticalSpacing(12)

        btn_html = QPushButton("Generate HTML report")
        btn_html.setObjectName("Primary")
        btn_html.clicked.connect(self.export_html)
        btn_pdf = QPushButton("Generate PDF report")
        btn_pdf.setObjectName("Primary")
        btn_pdf.clicked.connect(self.export_pdf)
        btn_json = QPushButton("Export JSON")
        btn_csv = QPushButton("Export CSV")
        btn_json.clicked.connect(self.export_json)
        btn_csv.clicked.connect(self.export_csv)

        grid.addWidget(btn_html, 0, 0)
        grid.addWidget(btn_pdf, 0, 1)
        grid.addWidget(btn_json, 1, 0)
        grid.addWidget(btn_csv, 1, 1)
        grid.setColumnStretch(2, 1)
        outer.addWidget(card)

        hint = QLabel(
            "Reports honor the filters you applied on the Findings page? No \u2014 "
            "reports always include the full result set for fidelity.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)
        outer.addStretch(1)
        return page

    # ------------------------------------------------------------- about
    def _build_about_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 22, 24, 22)

        title = QLabel("About")
        title.setObjectName("H1")
        outer.addWidget(title)

        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        about = QTextBrowser()
        about.setOpenExternalLinks(True)
        about.setStyleSheet("QTextBrowser{background:transparent;border:none;}")
        about.setHtml(f"""
        <h2 style="color:{ACCENT}">Endpoint Hardening &amp; Compliance Checker</h2>
        <p>Version {__version__} &middot; read-only CIS-style benchmark auditor.</p>
        <p>This tool <b>never modifies system configuration</b>. Every check reads
        registry values, runs read-only commands, or inspects service state.
        Remediation snippets shown in reports are <i>suggestions only</i> and are
        not executed by this application.</p>
        <h3 style="color:{ACCENT}">Safety model</h3>
        <ul>
          <li>Registry: read via <code>winreg</code> with <code>KEY_READ</code> only</li>
          <li>Commands: no writes; every probe is an inspection command</li>
          <li>No scheduled tasks, services, or policies are created</li>
        </ul>
        <h3 style="color:{ACCENT}">Data handling</h3>
        <ul>
          <li>Scans stay local; nothing is transmitted</li>
          <li>Reports contain only configuration state, not user files</li>
        </ul>
        <p style="color:{MUTED}">See README.txt for the full manual.</p>
        """)
        lay.addWidget(about)
        outer.addWidget(card)
        outer.addStretch(1)
        return page

    # ============================================================ actions
    def switch_page(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)
        self._update_nav_state()

    def _update_nav_state(self) -> None:
        has_report = self.current_report is not None
        self._nav_buttons[2].setEnabled(has_report)
        self._nav_buttons[3].setEnabled(has_report)

    # ------------------------------------------------------------- scan
    def start_scan(self) -> None:
        if self._worker is not None:
            return
        profile = self.profile_combo.currentData()
        include_info = self.info_chk.isChecked()
        include_manual = self.manual_chk.isChecked()

        self.scan_btn.setEnabled(False)
        self.progress.setValue(0)
        self.stage_lbl.setText("Starting\u2026")
        self.statusBar().showMessage("Scan in progress\u2026")

        self._worker = ScanWorker(profile, include_info, include_manual)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.stage.connect(self._on_scan_stage)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.failed.connect(self._on_scan_failed)
        self._worker.start()

    def _on_scan_stage(self, text: str) -> None:
        self.stage_lbl.setText(text)

    def _on_scan_progress(self, rule_id: str, current: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.current_lbl.setText(f"[{current}/{total}] {rule_id}")

    def _on_scan_finished(self, report) -> None:
        self.current_report = report
        self._worker = None
        self.scan_btn.setEnabled(True)

        s = report.summary
        self.card_total.set_value(s.total)
        self.card_pass.set_value(s.passed)
        self.card_fail.set_value(s.failed)
        self.card_err.set_value(s.errors)
        self.card_na.set_value(s.not_applicable + s.skipped)
        self.card_man.set_value(s.manual)

        self.gauge.set_score(report.score, report.grade)

        segs = [
            ("Pass", s.passed, STATUS_COLORS["pass"]),
            ("Fail", s.failed, STATUS_COLORS["fail"]),
            ("Error", s.errors, STATUS_COLORS["error"]),
            ("N/A", s.not_applicable, "#94a3b8"),
            ("Skipped", s.skipped, "#64748b"),
            ("Manual", s.manual, STATUS_COLORS["manual"]),
        ]
        self.donut.set_data(segs)

        cat_data: dict[str, list[int]] = {}
        for res in report.results:
            d = cat_data.setdefault(res.rule.category, [0, 0])
            d[0] += 1
            if res.status is ResultStatus.PASS:
                d[1] += 1
        self.bars.set_data([
            (name, v[1], v[0]) for name, v in sorted(cat_data.items())
        ])

        self.findings_table.load_results(report.results)
        self.findings_count.setText(
            f"{s.total} checks \u00b7 score {report.score:.1f}% (grade {report.grade})")

        p = report.platform
        self.scan_meta.setText(
            f"Scan {report.scan_id} \u00b7 {p.hostname} \u00b7 {p.os_name} "
            f"{p.os_version} \u00b7 {report.profile.replace('_', ' ').upper()} \u00b7 "
            f"{report.started_at} \u2192 {report.finished_at}")

        self._update_nav_state()
        self.switch_page(0)
        self.statusBar().showMessage(
            f"Scan complete \u2014 score {report.score:.1f}% ({report.grade})", 8000)

    def _on_scan_failed(self, message: str) -> None:
        self._worker = None
        self.scan_btn.setEnabled(True)
        self.stage_lbl.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", message)
        self.statusBar().showMessage("Scan failed.", 8000)

    # ---------------------------------------------------------- findings
    def show_result_detail(self, res) -> None:
        sev_color = {"critical": "#f43f5e", "high": "#fb923c", "medium": "#facc15",
                     "low": "#38bdf8", "info": "#60a5fa"}.get(res.severity.value, "#94a3b8")
        st_color = STATUS_COLORS.get(res.status.value, "#94a3b8")

        parts = [
            f"<h2 style='margin:0 0 2px;color:{sev_color}'>{res.rule.rule_id} "
            f"&mdash; {res.rule.title}</h2>",
            f"<p style='margin:4px 0'><span style='color:{sev_color}'><b>"
            f"{res.severity.value.upper()}</b></span> &middot; "
            f"{res.rule.category} &middot; {res.rule.profile.value.replace('_',' ').upper()} "
            f"&middot; <span style='color:{st_color}'><b>{res.status.value.replace('_',' ').upper()}</b></span></p>",
            f"<p style='margin:8px 0'>{res.rule.description}</p>",
        ]
        if res.rule.rationale:
            parts.append(f"<p style='color:{MUTED}'><b>Why:</b> {res.rule.rationale}</p>")
        if res.rule.audit_hint:
            parts.append(f"<p style='color:{MUTED}'><b>How it's audited:</b> "
                         f"{res.rule.audit_hint}</p>")
        if res.message:
            parts.append(f"<p><b>Result:</b> {res.message}</p>")
        if res.evidence:
            parts.append("<b>Evidence</b><ul>")
            for e in res.evidence:
                raw = (e.raw or "").replace("<", "&lt;").replace(">", "&gt;")
                parts.append(f"<li><code>{e.source}: {e.detail}</code><br>"
                             f"<pre style='color:#a5f3fc'>{raw[:1500]}</pre></li>")
            parts.append("</ul>")
        rem = res.rule.remediation
        if rem and res.status is ResultStatus.FAIL:
            parts.append(
                f"<div style='background:rgba(52,211,153,.08);border:1px solid "
                f"rgba(52,211,153,.25);border-radius:8px;padding:10px'>"
                f"<b>Suggested remediation</b> (not executed): "
                f"{rem.summary}")
            if rem.steps:
                parts.append("<ol>" + "".join(f"<li>{s}</li>" for s in rem.steps) + "</ol>")
            if rem.script:
                parts.append(f"<pre style='color:#a5f3fc'>{rem.script}</pre>")
            parts.append("</div>")
        if res.rule.refs:
            parts.append(f"<p style='color:{MUTED}'>Refs: {', '.join(res.rule.refs)}</p>")
        self.detail_view.setHtml("".join(parts))

    def _apply_filters(self) -> None:
        if self.current_report is None:
            return
        sev = self.filter_sev.currentData() or ""
        st = self.filter_st.currentData() or ""
        q = self.filter_q.text().strip().lower()

        rows = self.current_report.results
        if sev:
            rows = [r for r in rows if r.severity.value == sev]
        if st:
            rows = [r for r in rows if r.status.value == st]
        if q:
            rows = [
                r for r in rows
                if q in r.rule.rule_id.lower()
                or q in r.rule.title.lower()
                or q in r.message.lower()
                or q in r.rule.category.lower()
            ]
        self.findings_table.load_results(rows)

    # ----------------------------------------------------------- reports
    def _ensure_report(self) -> bool:
        if self.current_report is None:
            QMessageBox.information(self, "No scan", "Run a scan first.")
            return False
        return True

    def export_html(self) -> None:
        if not self._ensure_report():
            return
        default = f"compliance-report-{self.current_report.scan_id}.html"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML report", default, "HTML report (*.html)")
        if not path:
            return
        try:
            out = render_html(self.current_report, path, open_browser=True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Report failed", str(exc))
            return
        self.statusBar().showMessage(f"HTML report saved: {out}", 8000)

    def export_pdf(self) -> None:
        if not self._ensure_report():
            return
        default = f"compliance-report-{self.current_report.scan_id}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF report", default, "PDF report (*.pdf)")
        if not path:
            return
        try:
            out = render_pdf(self.current_report, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Report failed", str(exc))
            return
        if QMessageBox.question(
                self, "Open report?", "PDF generated. Open it now?") == \
                QMessageBox.StandardButton.Yes:
            webbrowser.open(Path(out).as_uri())
        self.statusBar().showMessage(f"PDF report saved: {out}", 8000)

    def export_json(self) -> None:
        if not self._ensure_report():
            return
        default = f"scan-{self.current_report.scan_id}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", default, "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(
            json.dumps(self.current_report.to_dict(), indent=2, default=str),
            encoding="utf-8")
        self.statusBar().showMessage(f"JSON exported: {path}", 8000)

    def export_csv(self) -> None:
        if not self._ensure_report():
            return
        default = f"scan-{self.current_report.scan_id}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default, "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["rule_id", "title", "severity", "profile", "category",
                        "status", "message", "observed", "expected"])
            for r in self.current_report.results:
                w.writerow([
                    r.rule.rule_id, r.rule.title, r.rule.severity.value,
                    r.rule.profile.value, r.rule.category, r.status.value,
                    r.message, str(r.observed)[:500], str(r.expected)[:500],
                ])
        self.statusBar().showMessage(f"CSV exported: {path}", 8000)

    # ---------------------------------------------------------- shortcuts
    def _wire_shortcuts(self) -> None:
        for i in range(5):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self,
                      activated=lambda idx=i: self.switch_page(idx))
        QShortcut(QKeySequence("F5"), self, activated=self.start_scan)
        quit_act = QAction(self)
        quit_act.setShortcut(QKeySequence("Ctrl+Q"))
        quit_act.triggered.connect(self.close)
        self.addAction(quit_act)


__all__ = ["MainWindow"]
