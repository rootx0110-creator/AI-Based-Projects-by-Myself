"""Dark/light theme stylesheets + palette for a polished, modern look."""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK = {
    "bg": "#0f1420",
    "bg_alt": "#161d2e",
    "panel": "#1a2236",
    "panel2": "#202a44",
    "border": "#2a3654",
    "text": "#e8ecf5",
    "text_dim": "#9aa7c0",
    "accent": "#4f8cff",
    "accent2": "#22d3a6",
    "danger": "#ff5d6c",
    "warn": "#ffb547",
    "graph_grid": "#232d47",
}

LIGHT = {
    "bg": "#f4f6fb",
    "bg_alt": "#eef1f8",
    "panel": "#ffffff",
    "panel2": "#f2f5fc",
    "border": "#d8dfeb",
    "text": "#1c2438",
    "text_dim": "#5d6b8a",
    "accent": "#2f6fed",
    "accent2": "#0ea5e9",
    "danger": "#e11d48",
    "warn": "#d97706",
    "graph_grid": "#dde4f0",
}

QSS_TEMPLATE = """
* {{ font-family: 'Segoe UI'; font-size: 13px; color: {text}; }}
QMainWindow, QWidget {{ background: {bg}; }}
QToolTip {{ background: {panel2}; color: {text}; border: 1px solid {border}; padding: 6px; }}

QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px; top: -1px; background: {bg}; }}
QTabBar::tab {{
    background: transparent; color: {text_dim}; padding: 9px 20px;
    margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: {panel}; color: {text}; border: 1px solid {border}; border-bottom: 2px solid {accent}; }}
QTabBar::tab:hover {{ color: {text}; }}

QFrame#Card {{
    background: {panel}; border: 1px solid {border}; border-radius: 10px;
}}
QLabel#CardTitle {{ color: {text_dim}; font-size: 11px; letter-spacing: 1px; font-weight: 600; }}
QLabel#BigValue {{ font-size: 26px; font-weight: 700; }}
QLabel#DownValue {{ color: {accent}; }}
QLabel#UpValue {{ color: {accent2}; }}

QPushButton {{
    background: {panel2}; color: {text}; border: 1px solid {border};
    border-radius: 7px; padding: 7px 16px; font-weight: 600;
}}
QPushButton:hover {{ border-color: {accent}; color: {accent}; }}
QPushButton#Primary {{ background: {accent}; color: #ffffff; border: none; }}
QPushButton#Primary:hover {{ background: {accent}; border: 1px solid {accent}; }}
QPushButton#Danger {{ background: transparent; color: {danger}; border: 1px solid {danger}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit, QDateEdit {{
    background: {panel2}; border: 1px solid {border}; border-radius: 7px; padding: 6px 10px;
    selection-background-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {panel}; border: 1px solid {border}; selection-background-color: {panel2}; }}

QTableWidget {{
    background: {panel}; border: 1px solid {border}; border-radius: 8px;
    gridline-color: {border}; alternate-background-color: {bg_alt};
}}
QHeaderView::section {{
    background: {panel2}; color: {text_dim}; border: none; border-bottom: 1px solid {border};
    padding: 7px 10px; font-weight: 600;
}}
QTableCornerButton::section {{ background: {panel2}; border: none; }}

QTreeWidget {{ background: {panel}; border: 1px solid {border}; border-radius: 8px; alternate-background-color: {bg_alt}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {text_dim}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 30px; }}

QCheckBox::indicator, QGroupBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {border}; border-radius: 4px; background: {panel2};
}}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}

QSlider::groove:horizontal {{ height: 5px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; background: {accent}; }}

QStatusBar {{ background: {panel}; border-top: 1px solid {border}; }}
QProgressBar {{
    background: {panel2}; border: none; border-radius: 6px; height: 12px; text-align: center; color: {text};
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}

QGroupBox {{
    border: 1px solid {border}; border-radius: 8px; margin-top: 12px;
    font-weight: 600; color: {text_dim};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
"""


def palette_colors(theme: str) -> dict[str, str]:
    """Return the color dict for a theme name ('dark'|'light')."""
    return DARK if theme == "dark" else LIGHT


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the QSS stylesheet + palette to the whole application."""
    c = palette_colors(theme)
    app.setStyleSheet(QSS_TEMPLATE.format(**c))

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["panel"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["bg_alt"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["panel2"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
