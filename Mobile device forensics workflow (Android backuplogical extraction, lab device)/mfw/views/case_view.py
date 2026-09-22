"""Case Manager: intake form + case table + set active case."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..widgets import Card, add_row, make_table


class CaseView(QWidget):
    def __init__(self, main) -> None:
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        form_card = Card("New case intake")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.f_number = QLineEdit()
        self.f_number.setPlaceholderText("e.g. 2026-DET-014")
        self.f_title = QLineEdit()
        self.f_title.setPlaceholderText("Short matter title")
        self.f_examiner = QLineEdit()
        self.f_examiner.setPlaceholderText("Examiner name")
        self.f_agency = QLineEdit()
        self.f_agency.setPlaceholderText("Agency / lab (optional)")
        self.f_notes = QLineEdit()
        self.f_notes.setPlaceholderText("Notes (optional)")
        form.addRow("Case number *", self.f_number)
        form.addRow("Title *", self.f_title)
        form.addRow("Examiner *", self.f_examiner)
        form.addRow("Agency", self.f_agency)
        form.addRow("Notes", self.f_notes)
        form_card.add(form)

        btns = QHBoxLayout()
        self.btn_create = QPushButton("＋ Create case")
        self.btn_create.setProperty("cssClass", "primary")
        self.btn_activate = QPushButton("Set as active case")
        self.btn_delete = QPushButton("Delete case")
        self.btn_delete.setProperty("cssClass", "danger")
        btns.addWidget(self.btn_create)
        btns.addWidget(self.btn_activate)
        btns.addStretch(1)
        btns.addWidget(self.btn_delete)
        form_card.add(btns)
        lay.addWidget(form_card)

        list_card = Card("All cases")
        self.tbl = make_table(["Case", "Title", "Examiner", "Agency", "Created", "Extractions", "Status"])
        self.tbl.horizontalHeader().setStretchLastSection(False)
        for i, w in enumerate([110, 260, 140, 140, 160, 90, 80]):
            self.tbl.setColumnWidth(i, w)
        list_card.add(self.tbl, 1)
        lay.addWidget(list_card, 1)

        self.btn_create.clicked.connect(self._create)
        self.btn_activate.clicked.connect(self._activate)
        self.btn_delete.clicked.connect(self._delete)
        self.tbl.itemSelectionChanged.connect(self._selection_changed)
        self.btn_activate.setEnabled(False)
        self.btn_delete.setEnabled(False)

    # ------------------------------------------------------------ helpers --
    def _selected_case(self) -> str | None:
        row = self.tbl.currentRow()
        if row < 0:
            return None
        return self.tbl.item(row, 0).text()

    def _selection_changed(self) -> None:
        has = self._selected_case() is not None
        self.btn_activate.setEnabled(has)
        self.btn_delete.setEnabled(has)

    # ------------------------------------------------------------ actions --
    def _create(self) -> None:
        number = self.f_number.text().strip()
        if not number:
            QMessageBox.warning(self, "Case number required", "Enter a unique case number first.")
            return
        try:
            rec = self.main.store.create_case(
                number,
                self.f_title.text().strip(),
                self.f_examiner.text().strip(),
                self.f_agency.text().strip(),
                self.f_notes.text().strip(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Duplicate case", str(exc))
            return
        for f in (self.f_number, self.f_title, self.f_examiner, self.f_agency, self.f_notes):
            f.clear()
        self.main.store.audit(rec["case_number"], "CASE_CREATED", "via Case Manager UI")
        self.main.refresh_all()
        self.main.goto(2)  # jump to Extraction

    def _activate(self) -> None:
        case = self._selected_case()
        if case:
            self.main.store.set_active_case(case, silent=False)
            self.main.refresh_all()

    def _delete(self) -> None:
        case = self._selected_case()
        if not case:
            return
        ret = QMessageBox.question(
            self, "Delete case",
            f"Delete case '{case}' and ALL of its evidence, reports and logs?\nThis cannot be undone.",
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.main.store.delete_case(case)
        self.main.refresh_all()

    # ------------------------------------------------------------ refresh --
    def refresh(self) -> None:
        self.tbl.setRowCount(0)
        active = self.main.store.active_case_number()
        for c in self.main.store.list_cases():
            add_row(self.tbl, [
                c.get("case_number", ""), c.get("title", ""),
                c.get("examiner", ""), c.get("agency", ""),
                c.get("created", ""), str(len(c.get("extractions", []))),
                c.get("status", "Open"),
            ])
            if c.get("case_number") == active:
                row = self.tbl.rowCount() - 1
                for col in range(self.tbl.columnCount()):
                    item = self.tbl.item(row, col)
                    if item:
                        item.setForeground(QBrush(QColor("#00E5C3")))
