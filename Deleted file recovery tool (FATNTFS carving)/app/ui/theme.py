"""Central UI theme & colors for the Deleted File Recovery Tool."""

APP_NAME = "Deleted File Recovery Tool"
APP_VERSION = "2.1"
APP_TAGLINE = "FAT / NTFS Analysis & Raw File Carving"

COLORS = {
    "bg": "#f3f5f9",
    "panel": "#ffffff",
    "card": "#eaeef5",
    "card_hover": "#dfe5f0",
    "border": "#d7dde9",
    "text": "#1c2537",
    "muted": "#5f6b85",
    "accent": "#2f6bff",
    "accent2": "#7a4fef",
    "cyan": "#0e9bc4",
    "teal": "#0f9d76",
    "green": "#12b981",
    "amber": "#b8860b",
    "red": "#e03e3e",
    "sidebar": "#eceff5",
}

THEME_MODE = "light"
WINDOW_W = 1240
WINDOW_H = 800
WINDOW_MIN_W = 1080
WINDOW_MIN_H = 680

FONT_FAMILY = "Segoe UI"


def setup_ctk():
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode(THEME_MODE)
        ctk.set_default_color_theme("blue")
        return ctk
    except Exception:
        return None