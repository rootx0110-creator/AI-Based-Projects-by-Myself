"""Reusable themed widgets."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("background: rgba(255,255,255,0.10); max-height: 1px; border: none;")
    return line


class Card(QFrame):
    """Translucent glass panel."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 14, 16, 14)
        self._lay.setSpacing(10)
        if title:
            t = QLabel(title)
            t.setProperty("h2", "true")
            self._lay.addWidget(t)

    def add(self, w: QWidget | QLayout, stretch: int = 0) -> None:
        if isinstance(w, QLayout):
            holder = QWidget()
            holder.setLayout(w)
            self._lay.addWidget(holder, stretch)
        else:
            self._lay.addWidget(w, stretch)


class StatCard(QFrame):
    """KPI card with a big value and a caption."""

    def __init__(self, title: str, value: str = "0", accent: str | None = None):
        super().__init__()
        self.setProperty("card", "true")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        self.value_lbl = QLabel(value)
        self.value_lbl.setProperty("h1", "true")
        if accent:
            self.value_lbl.setStyleSheet(f"color: {accent};")
        self.title_lbl = QLabel(title)
        self.title_lbl.setProperty("small", "true")
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.title_lbl)
        lay.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_lbl.setText(value)


def make_table(headers: list[str]) -> QTableWidget:
    """Styled, read-only table with sensible column behaviour."""
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setWordWrap(False)
    hdr = t.horizontalHeader()
    hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    hdr.setStretchLastSection(True)
    return t


def add_row(t: QTableWidget, values: list[str], data: object = None) -> None:
    row = t.rowCount()
    t.insertRow(row)
    for col, text in enumerate(values):
        item = QTableWidgetItem("" if text is None else str(text))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        t.setItem(row, col, item)
    if data is not None:
        t.item(row, 0).setData(Qt.ItemDataRole.UserRole, data)


def chip(text: str, kind: str = "plain") -> QLabel:
    lbl = QLabel(text)
    if kind == "ok":
        lbl.setProperty("chipOk", "true")
    elif kind == "bad":
        lbl.setProperty("chipBad", "true")
    else:
        lbl.setProperty("chip", "true")
    return lbl
