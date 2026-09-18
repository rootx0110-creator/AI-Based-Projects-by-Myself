import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0d1117"
PANEL = "#161b22"
CARD = "#1c2330"
CARD_HOVER = "#232d40"
BORDER = "#2a3444"

TEXT = "#e6edf3"
MUTED = "#8b98ab"
ACCENT = "#2f81f7"
ACCENT_DARK = "#1f6feb"
ACCENT_TEXT = "#dbeafe"

OK = "#3fb950"
WARN = "#d29922"
CRIT = "#f85149"
INFO = "#58a6ff"

SEV_COLORS = {1: INFO, 2: WARN, 3: CRIT}
SEV_NAMES = {1: "Info", 2: "Warning", 3: "Critical"}
FONT_FAMILY = "Segoe UI"


def hx(color, alpha=1.0):
    """Return an rgba() string so customtkinter can render translucent colors."""
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"