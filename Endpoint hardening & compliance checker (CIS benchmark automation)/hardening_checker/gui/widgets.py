"""Reusable dashboard widgets: cards, custom-painted charts, delegates."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .theme import ACCENT, PANEL, SEV_COLORS, STATUS_COLORS


# --------------------------------------------------------------------------- #
# Cards
# --------------------------------------------------------------------------- #
class StatCard(QFrame):
    """A titled numeric card (Passed / Failed / ...)."""

    def __init__(self, title: str, color: str = "#e8eefc", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumSize(132, 92)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(2)

        self._title = QLabel(title.upper())
        self._title.setObjectName("CardTitle")
        self._value = QLabel("\u2013")
        self._value.setObjectName("BigNumber")
        self._value.setStyleSheet(f"color:{color};")

        lay.addWidget(self._title)
        lay.addWidget(self._value)
        lay.addStretch(1)

    def set_value(self, v) -> None:
        self._value.setText(str(v))


class ScoreGauge(QWidget):
    """Custom-painted arc gauge showing the compliance score + grade."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._score = 0.0
        self._grade = "F"
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_score(self, score: float, grade: str) -> None:
        self._score = score
        self._grade = grade
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt naming
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        cx = self.width() / 2
        cy = self.height() / 2 + 6
        r = side / 2 - 14

        track = QPen(QColor("#1f2a40"), 12, Qt.PenStyle.SolidLine,
                     Qt.PenCapStyle.RoundCap)
        p.setPen(track)
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 40 * 16, -260 * 16)

        if self._score > 0:
            color = QColor(STATUS_COLORS["pass"] if self._score >= 80 else
                           "#facc15" if self._score >= 60 else
                           STATUS_COLORS["fail"])
            arc = QPen(color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(arc)
            span = int(-260 * 16 * (self._score / 100.0))
            p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 40 * 16, span)

        # text
        p.setPen(QColor("#e8eefc"))
        f = QFont(self.font())
        f.setPointSizeF(max(20.0, side / 12))
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, cy - r * 0.55, self.width(), r * 0.8),
                   Qt.AlignmentFlag.AlignCenter, f"{self._score:.0f}%")

        p.setPen(QColor("#8fa3c4"))
        f2 = QFont(self.font())
        f2.setPointSizeF(max(8.0, side / 24))
        p.setFont(f2)
        p.drawText(QRectF(0, cy + r * 0.18, self.width(), 26),
                   Qt.AlignmentFlag.AlignCenter, f"GRADE {self._grade}")
        p.end()


class DonutChart(QWidget):
    """Donut of statuses with centered total."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._segments: list[tuple[str, int, str]] = []
        self.setMinimumHeight(180)

    def set_data(self, segments: list[tuple[str, int, str]]) -> None:
        """segments: list of (label, count, hexcolor)."""
        self._segments = [s for s in segments if s[1] > 0]
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = sum(c for _l, c, _col in self._segments)
        if total == 0:
            p.setPen(QColor("#8fa3c4"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            p.end()
            return

        side = min(self.width() * 0.62, self.height())
        cx = self.width() * 0.32
        cy = self.height() / 2
        rect = QRectF(cx - side / 2, cy - side / 2, side, side)

        start = 90 * 16
        for _label, count, color in self._segments:
            span = int(-360 * 16 * (count / total))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(color)))
            p.drawPie(rect, start, span)
            start += span

        hole = QRectF(cx - side * 0.30, cy - side * 0.30, side * 0.60, side * 0.60)
        p.setBrush(QBrush(QColor(PANEL)))
        p.drawEllipse(hole)
        p.setPen(QColor("#e8eefc"))
        f = QFont(self.font())
        f.setBold(True)
        f.setPointSizeF(15)
        p.setFont(f)
        p.drawText(hole, Qt.AlignmentFlag.AlignCenter, str(total))

        # legend
        lx = self.width() * 0.58
        ly = cy - (len(self._segments) * 20) / 2
        f.setPointSizeF(9.5)
        f.setBold(False)
        p.setFont(f)
        for label, count, color in self._segments:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(QRectF(lx, ly + 4, 10, 10), 3, 3)
            p.setPen(QColor("#cbd5e1"))
            p.drawText(QRectF(lx + 18, ly - 2, self.width() - lx - 20, 20),
                       Qt.AlignmentFlag.AlignVCenter, f"{label} ({count})")
            ly += 20
        p.end()


class CategoryBars(QWidget):
    """Horizontal pass-rate bars per category."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[str, int, int]] = []  # (name, passed, total)
        self.setMinimumHeight(160)

    def set_data(self, rows: list[tuple[str, int, int]]) -> None:
        self._rows = rows
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._rows:
            p.setPen(QColor("#8fa3c4"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            p.end()
            return

        fm = QFontMetrics(self.font())
        row_h = max(20, self.height() // max(1, len(self._rows)))
        label_w = min(190, fm.horizontalAdvance("Session Lock") + 24)
        bar_x = label_w + 8
        bar_w = self.width() - bar_x - 64

        y = 6
        for name, passed, total in self._rows[:12]:
            rate = (passed / total * 100) if total else 0
            p.setPen(QColor("#cbd5e1"))
            p.drawText(QRectF(0, y, label_w, row_h), Qt.AlignmentFlag.AlignVCenter,
                       fm.elidedText(name, Qt.TextElideMode.ElideRight, label_w - 4))

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0a0f1c"))
            p.drawRoundedRect(QRectF(bar_x, y + row_h / 2 - 5, bar_w, 10), 5, 5)

            color = QColor(STATUS_COLORS["pass"] if rate >= 80 else
                           "#facc15" if rate >= 50 else STATUS_COLORS["fail"])
            p.setBrush(color)
            p.drawRoundedRect(QRectF(bar_x, y + row_h / 2 - 5,
                                     max(bar_w * rate / 100, 2), 10), 5, 5)

            p.setPen(QColor("#8fa3c4"))
            p.drawText(QRectF(bar_x + bar_w + 6, y, 56, row_h),
                       Qt.AlignmentFlag.AlignVCenter, f"{passed}/{total}")
            y += row_h
        p.end()


# --------------------------------------------------------------------------- #
# Findings table
# --------------------------------------------------------------------------- #
class SevPillDelegate(QStyledItemDelegate):
    """Renders severity / status cells as colored pills."""

    def paint(self, painter: QPainter, option, index) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        kind = index.data(Qt.ItemDataRole.UserRole) or ""
        if not kind:
            super().paint(painter, option, index)
            return

        p = painter
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        color_hex = SEV_COLORS.get(kind) or STATUS_COLORS.get(kind, "#94a3b8")
        if index.column() == 0:
            base = QColor(color_hex)
            bg = QColor(base)
            bg.setAlpha(30)
            fg = base
        else:
            base = QColor(color_hex)
            bg = QColor(base)
            bg.setAlpha(30)
            fg = base

        rect = option.rect.adjusted(4, 4, -4, -4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, 6, 6)

        p.setPen(fg)
        f = QFont(option.font)
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() - 0.5)
        p.setFont(f)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text.upper())
        p.restore()


class FindingsTable(QTableWidget):
    """Main findings table with severity/status pills and detail row."""

    COLS = ["Severity", "Rule", "Check", "Status"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(self.COLS)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setWordWrap(False)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 96)
        self.setColumnWidth(1, 128)
        self.setColumnWidth(3, 118)

        self._sev_del = SevPillDelegate(self)
        self.setItemDelegateForColumn(0, self._sev_del)
        self._st_del = SevPillDelegate(self)
        self.setItemDelegateForColumn(3, self._st_del)

        self.itemSelectionChanged.connect(self._emit_detail)
        self._rows: list = []

    # --------------------------------------------------------------- fill
    def load_results(self, results: list) -> None:
        self.setUpdatesEnabled(False)
        self.setRowCount(0)
        self._rows = list(results)
        for r in results:
            row = self.rowCount()
            self.insertRow(row)

            sev_item = QTableWidgetItem(r.severity.value)
            sev_item.setData(Qt.ItemDataRole.UserRole, r.severity.value)
            self.setItem(row, 0, sev_item)

            rid = QTableWidgetItem(r.rule.rule_id)
            rid.setToolTip(r.rule.title)
            self.setItem(row, 1, rid)

            title = QTableWidgetItem(f"{r.rule.title}  \u2014  {r.message}")
            title.setToolTip(r.message)
            self.setItem(row, 2, title)

            st = QTableWidgetItem(r.status.value.replace("_", " "))
            st.setData(Qt.ItemDataRole.UserRole, r.status.value)
            self.setItem(row, 3, st)
        self.setUpdatesEnabled(True)

    def _emit_detail(self) -> None:
        sel = self.currentRow()
        if sel < 0 or sel >= len(self._rows):
            return
        res = self._rows[sel]
        # results are loaded sorted; table row order matches self._rows
        if hasattr(self.parent(), "show_result_detail"):
            self.parent().show_result_detail(res)

    def results(self) -> list:
        return self._rows


__all__ = [
    "StatCard",
    "ScoreGauge",
    "DonutChart",
    "CategoryBars",
    "FindingsTable",
    "SevPillDelegate",
]
