"""Modern dark theme (QSS) shared across the app."""

from __future__ import annotations

# Palette constants (also used by charts)
BG_DARK = "#0b1220"
PANEL = "#111a2e"
PANEL2 = "#0e1626"
LINE = "#1f2a40"
TEXT = "#e8eefc"
MUTED = "#8fa3c4"
ACCENT = "#22d3ee"

SEV_COLORS = {
    "critical": "#f43f5e",
    "high": "#fb923c",
    "medium": "#facc15",
    "low": "#38bdf8",
    "info": "#60a5fa",
}
STATUS_COLORS = {
    "pass": "#34d399",
    "fail": "#f87171",
    "error": "#fbbf24",
    "not_applicable": "#94a3b8",
    "skipped": "#94a3b8",
    "manual": "#60a5fa",
}

_QSS = """
* { font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: #0b1220; }
QWidget { color: #e8eefc; }

/* ---------- sidebar ---------- */
#Sidebar { background: #0e1626; border-right: 1px solid #1f2a40; }
#BrandName { font-size: 15px; font-weight: 600; color: #e8eefc; }
#BrandSub { font-size: 10.5px; color: #8fa3c4; }
QPushButton#NavButton {
  text-align: left; padding: 10px 14px; border: none; border-radius: 9px;
  color: #8fa3c4; background: transparent; font-size: 13.5px;
}
QPushButton#NavButton:hover { background: #16203a; color: #e8eefc; }
QPushButton#NavButton:checked {
  background: #14304a; color: #22d3ee; font-weight: 600;
}

/* ---------- generic panels ---------- */
QFrame#Card, QFrame#Panel {
  background: #111a2e; border: 1px solid #1f2a40; border-radius: 12px;
}
QLabel#CardTitle { color: #8fa3c4; font-size: 11px; letter-spacing: 1px;
  text-transform: uppercase; }
QLabel#BigNumber { font-size: 30px; font-weight: 700; }
QLabel#Muted { color: #8fa3c4; font-size: 12px; }
QLabel#H1 { font-size: 21px; font-weight: 600; }
QLabel#H2 { font-size: 15px; font-weight: 600; color: #22d3ee; }

/* ---------- inputs & buttons ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {
  background: #0e1626; border: 1px solid #1f2a40; border-radius: 8px;
  padding: 7px 10px; selection-background-color: #164e63;
}
QLineEdit:focus, QComboBox:focus { border-color: #22d3ee; }
QComboBox QAbstractItemView {
  background: #111a2e; border: 1px solid #1f2a40;
  selection-background-color: #14304a;
}
QPushButton {
  background: #16203a; color: #e8eefc; border: 1px solid #24304d;
  border-radius: 8px; padding: 8px 16px; font-weight: 500;
}
QPushButton:hover { background: #1b2a4a; border-color: #2d3d60; }
QPushButton:disabled { color: #55617e; background: #101827; }
QPushButton#Primary {
  background: #0891b2; border: none; color: white; font-weight: 600;
}
QPushButton#Primary:hover { background: #0aa3c9; }
QPushButton#Primary:disabled { background: #14505f; color: #9fc7d4; }
QPushButton#Danger { background: #7f1d1d; border: none; }
QPushButton#Danger:hover { background: #991b1b; }
QToolButton { background: transparent; border: none; padding: 4px; border-radius: 6px; }
QToolButton:hover { background: #16203a; }

/* ---------- tables / trees ---------- */
QTableWidget, QTableView, QTreeWidget, QTreeView, QListWidget {
  background: #111a2e; alternate-background-color: #0e1626;
  border: 1px solid #1f2a40; border-radius: 10px; gridline-color: #1a2338;
  selection-background-color: #14304a; selection-color: #e8eefc;
}
QHeaderView::section {
  background: #0e1626; color: #8fa3c4; padding: 8px 10px; border: none;
  border-bottom: 1px solid #1f2a40; font-size: 11px; font-weight: 600;
}
QTableCornerButton::section { background: #0e1626; border: none; }

/* ---------- progress & bars ---------- */
QProgressBar {
  background: #0a0f1c; border: none; border-radius: 6px; height: 8px;
  text-align: center; color: transparent;
}
QProgressBar::chunk { background: #22d3ee; border-radius: 6px; }

/* ---------- misc ---------- */
QStatusBar { background: #0e1626; color: #8fa3c4; border-top: 1px solid #1f2a40; }
QToolTip {
  background: #16203a; color: #e8eefc; border: 1px solid #24304d; padding: 6px;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #24304d; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #31426b; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal { background: #24304d; border-radius: 5px; min-width: 30px; }
QSplitter::handle { background: #1f2a40; width: 1px; }
QGroupBox {
  border: 1px solid #1f2a40; border-radius: 10px; margin-top: 12px;
  color: #8fa3c4; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QMenu { background: #111a2e; border: 1px solid #1f2a40; }
QMenu::item:selected { background: #14304a; }
QTabWidget::pane { border: 1px solid #1f2a40; border-radius: 8px; }
QTabBar::tab {
  background: transparent; color: #8fa3c4; padding: 8px 16px;
  border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #22d3ee; border-bottom-color: #22d3ee; }
"""


def qss() -> str:
    """Return the full stylesheet."""
    return _QSS


__all__ = ["qss", "SEV_COLORS", "STATUS_COLORS", "ACCENT", "MUTED", "PANEL"]
