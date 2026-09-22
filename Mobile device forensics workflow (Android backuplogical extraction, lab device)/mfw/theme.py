"""Theme: palette + application-wide QSS.

Background is a deep indigo->violet gradient (deliberately not black/white),
with teal and violet accents and translucent "glass" cards.
"""
from __future__ import annotations

# ---------------------------------------------------------------- palette --
BG_TOP = "#1B1140"      # deep indigo
BG_MID = "#2A1B5E"      # violet-indigo
BG_BOT = "#3A2380"      # violet
ACCENT = "#00E5C3"      # teal
ACCENT_DARK = "#00B398"
VIOLET = "#8B7CF8"
PANEL = "rgba(255, 255, 255, 0.06)"
PANEL_BORDER = "rgba(255, 255, 255, 0.14)"
TEXT = "#EDEBFF"
TEXT_DIM = "rgba(237, 235, 255, 0.65)"
DANGER = "#FF6B81"
WARN = "#FFC857"

# ------------------------------------------------------------------- QSS --
QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {TEXT};
    selection-background-color: {ACCENT_DARK};
    selection-color: #062A24;
}}
QMainWindow, QDialog {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_TOP}, stop:0.55 {BG_MID}, stop:1 {BG_BOT});
}}
QWidget[card="true"] {{
    background: {PANEL};
    border: 1px solid {PANEL_BORDER};
    border-radius: 14px;
}}
QLabel {{ background: transparent; border: none; }}
QLabel[h1="true"] {{ font-size: 26px; font-weight: 800; }}
QLabel[h2="true"] {{ font-size: 18px; font-weight: 700; }}
QLabel[small="true"] {{ color: {TEXT_DIM}; font-size: 11px; }}
QLabel[chip="true"] {{
    background: rgba(255,255,255,0.08);
    border: 1px solid {PANEL_BORDER};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
}}
QLabel[chipOk="true"] {{
    background: rgba(0, 229, 195, 0.14);
    border: 1px solid rgba(0, 229, 195, 0.45);
    color: {ACCENT};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel[chipBad="true"] {{
    background: rgba(255, 107, 129, 0.12);
    border: 1px solid rgba(255, 107, 129, 0.45);
    color: {DANGER};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}}

/* -------- buttons -------- */
QPushButton {{
    background: rgba(255,255,255,0.08);
    border: 1px solid {PANEL_BORDER};
    border-radius: 9px;
    padding: 7px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: rgba(255,255,255,0.14); }}
QPushButton:pressed {{ background: rgba(255,255,255,0.05); }}
QPushButton:disabled {{ color: rgba(255,255,255,0.35); }}
QPushButton[cssClass="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    border: none;
    color: #05281F;
    font-weight: 800;
}}
QPushButton[cssClass="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2FF2D6, stop:1 {ACCENT});
}}
QPushButton[cssClass="primary"]:disabled {{
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.35);
}}
QPushButton[cssClass="violet"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {VIOLET}, stop:1 #6A5BE0);
    border: none; color: #16103A; font-weight: 800;
}}
QPushButton[cssClass="danger"] {{
    background: rgba(255, 107, 129, 0.16);
    border: 1px solid rgba(255, 107, 129, 0.5);
    color: {DANGER};
}}

/* -------- inputs -------- */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDateTimeEdit {{
    background: rgba(255,255,255,0.07);
    border: 1px solid {PANEL_BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {BG_MID};
    border: 1px solid {PANEL_BORDER};
    selection-background-color: rgba(0,229,195,0.25);
    outline: none;
}}

/* -------- sidebar -------- */
QListWidget#navList {{
    background: transparent;
    border: none;
    outline: none;
    padding: 8px 6px;
}}
QListWidget#navList::item {{
    color: {TEXT_DIM};
    border-radius: 10px;
    padding: 11px 14px;
    margin: 3px 6px;
    font-weight: 600;
}}
QListWidget#navList::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(0,229,195,0.18), stop:1 rgba(139,124,248,0.18));
    color: {TEXT};
    border: 1px solid rgba(0,229,195,0.35);
}}
QListWidget#navList::item:hover:!selected {{ background: rgba(255,255,255,0.06); }}

/* -------- tables -------- */
QTableWidget {{
    background: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.08);
    alternate-background-color: rgba(255,255,255,0.03);
}}
QTableWidget::item {{ padding: 5px 8px; }}
QTableWidget::item:selected {{ background: rgba(0,229,195,0.22); color: {TEXT}; }}
QHeaderView::section {{
    background: rgba(255,255,255,0.07);
    border: none;
    border-bottom: 1px solid {PANEL_BORDER};
    padding: 7px 8px;
    font-weight: 700;
    color: {TEXT_DIM};
}}

/* -------- misc -------- */
QProgressBar {{
    background: rgba(255,255,255,0.08);
    border: 1px solid {PANEL_BORDER};
    border-radius: 8px;
    text-align: center;
    height: 16px;
    color: {TEXT};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 {VIOLET});
    border-radius: 7px;
}}
QPlainTextEdit#logBox {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    background: rgba(6, 4, 18, 0.55);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.18); border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(0,229,195,0.5); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.18); border-radius: 5px; min-width: 30px;
}}
QToolTip {{
    background: {BG_MID}; color: {TEXT};
    border: 1px solid {ACCENT}; padding: 5px;
}}
QSplitter::handle {{ background: rgba(255,255,255,0.08); }}
"""


def apply_style(app) -> None:
    """Install the global stylesheet on the QApplication."""
    app.setStyleSheet(QSS)
