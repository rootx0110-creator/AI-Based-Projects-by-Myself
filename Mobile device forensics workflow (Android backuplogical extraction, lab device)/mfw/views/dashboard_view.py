"""Dashboard: KPI cards, recent cases, system status."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import adb, demo
from ..widgets import Card, StatCard, add_row, make_table


def _inner_layout(card: Card, lay: QVBoxLayout) -> None:
    """Attach an inner QVBoxLayout to a Card's own layout."""
    holder = QWidget()
    holder.setLayout(lay)
    card.add(holder, 1)


class DashboardView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        kpis = QHBoxLayout()
        kpis.setSpacing(14)
        self.k_cases = StatCard("Cases on file", "0", accent="#00E5C3")
        self.k_evidence = StatCard("Evidence items", "0", accent="#8B7CF8")
        self.k_active = StatCard("Active case", "—", accent="#FFC857")
        self.k_adb = StatCard("ADB status", "…", accent="#00E5C3")
        for c in (self.k_cases, self.k_evidence, self.k_active, self.k_adb):
            kpis.addWidget(c)
        lay.addLayout(kpis)

        cols = QHBoxLayout()
        cols.setSpacing(16)

        recent = Card("Recent cases")
        self.recent_tbl = make_table(["Case", "Title", "Examiner", "Created", "Status"])
        self.recent_tbl.horizontalHeader().setStretchLastSection(False)
        self.recent_tbl.setColumnWidth(0, 110)
        self.recent_tbl.setColumnWidth(1, 240)
        self.recent_tbl.setColumnWidth(2, 140)
        self.recent_tbl.setColumnWidth(3, 160)
        recent.add(self.recent_tbl, 1)
        cols.addWidget(recent, 3)

        status = Card("System status")
        s = QVBoxLayout()
        self.lbl_adb = QLabel("…")
        self.lbl_devices = QLabel("…")
        self.lbl_demo = QLabel("…")
        for lbl in (self.lbl_adb, self.lbl_devices, self.lbl_demo):
            lbl.setWordWrap(True)
            s.addWidget(lbl)
        s.addStretch(1)
        holder = QWidget()
        holder.setLayout(s)
        status.add(holder)
        status.setFixedWidth(330)
        cols.addWidget(status, 1)

        lay.addLayout(cols, 1)

    # ------------------------------------------------------------ refresh --
    def refresh(self) -> None:
        store = self.main.store
        cases = store.list_cases()
        self.k_cases.set_value(str(len(cases)))

        evidence = 0
        for c in cases:
            evidence += len(store.chain_entries(c["case_number"]))
        self.k_evidence.set_value(str(evidence))

        active = store.active()
        self.k_active.set_value(active["case_number"] if active else "—")

        adb_path = self.main.adb_path
        if adb_path:
            self.k_adb.set_value("Ready")
            self.lbl_adb.setText(f"adb: {adb_path}")
            try:
                devs = adb.list_devices(adb_path)
                self.lbl_devices.setText(
                    f"Devices attached: {len(devs)} — "
                    + (", ".join(d["serial"] for d in devs) or "none")
                )
            except OSError:
                self.lbl_devices.setText("Devices: adb error")
        else:
            self.k_adb.set_value("Not found")
            self.lbl_adb.setText("adb.exe not found — install platform-tools. "
                                 "The Demo dataset workflow still works.")
            self.lbl_devices.setText("Devices: unknown")
        try:
            d = demo.demo_artifacts("__probe__")
            self.lbl_demo.setText(
                "Offline demo pipeline OK "
                f"(sample: {sum(len(v) for v in d.values())} records)"
            )
        except Exception as exc:  # pragma: no cover
            self.lbl_demo.setText(f"Demo pipeline error: {exc}")

        self.recent_tbl.setRowCount(0)
        for c in cases[:8]:
            add_row(self.recent_tbl, [
                c.get("case_number", ""), c.get("title", ""),
                c.get("examiner", ""), c.get("created", ""),
                c.get("status", "Open"),
            ])
