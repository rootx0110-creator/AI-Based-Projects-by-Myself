"""Settings tab — theme toggle + app config."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QCheckBox, QComboBox
from PyQt6.QtCore import Qt

class SettingsTab(QWidget):
    theme_changed = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(str)
    settings_applied = __import__("PyQt6.QtCore", fromlist=["pyqtSignal"]).pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        # Theme
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("<b>Theme:</b>"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark (default)", "Light"])
        self._theme_combo.currentIndexChanged.connect(self._on_theme)
        theme_row.addWidget(self._theme_combo)
        theme_layout.addLayout(theme_row)

        # App config
        app_group = QGroupBox("Application")
        app_layout = QVBoxLayout(app_group)
        app_layout.addWidget(QLabel("<b>Frontend port:</b> 8000 (configurable)"))
        app_layout.addWidget(QLabel("<b>Backend count:</b> 3–5 mock servers"))
        app_layout.addWidget(QLabel("<b>Config path:</b> %APPDATA%/LBSimulator/"))
        app_layout.addStretch()
        theme_layout.addWidget(app_group)

        # Hotkeys
        hotkey_group = QGroupBox("Hotkeys")
        hotkey_layout = QVBoxLayout(hotkey_group)
        hotkey_layout.addWidget(QLabel("<b>Ctrl+S</b> — Start/Stop simulator"))
        hotkey_layout.addWidget(QLabel("<b>Ctrl+R</b> — Reset all metrics"))
        hotkey_layout.addWidget(QLabel("<b>Ctrl+Shift+S</b> — Snapshot (export metrics)"))
        hotkey_layout.addWidget(QLabel("<b>Ctrl+,</b> — Open settings"))
        hotkey_layout.addWidget(QLabel("<b>F11</b> — Toggle fullscreen"))
        theme_layout.addWidget(hotkey_group)

        self._layout.addWidget(theme_group)
        self._layout.addStretch()

    def _on_theme(self, idx):
        theme = "dark" if idx == 0 else "light"
        self.theme_changed.emit(theme)
