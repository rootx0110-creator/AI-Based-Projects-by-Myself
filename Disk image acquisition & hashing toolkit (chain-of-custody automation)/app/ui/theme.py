import customtkinter as ctk

ctk.set_appearance_mode("dark")

# Palette
BG = "#0b0f14"
PANEL = "#141925"
PANEL2 = "#1a2230"
BORDER = "#28323f"
ACCENT = "#2dd4bf"
ACCENT2 = "#38bdf8"
GOOD = "#22c55e"
BAD = "#ef4444"
WARN = "#f59e0b"
TEXT = "#e8eef6"
MUTED = "#8ea0b3"

ACCENT_BTN = "#155e6b"


def font(size=13, weight="normal", family="Segoe UI"):
    w = {"bold": "bold", "normal": "normal"}.get(weight, "normal")
    return ctk.CTkFont(family=family, size=int(size), weight=w)


def style_label(widget: ctk.CTkLabel, color=None, size=None, weight=None):
    if color is not None:
        widget.configure(text_color=color)
    if size is not None:
        widget.configure(font=font(size, weight))
    return widget


def subtitle(parent, text, size=12.5, color=MUTED):
    return ctk.CTkLabel(parent, text=text, font=font(size), text_color=color, anchor="w")


def title(parent, text, size=20, color=TEXT):
    return ctk.CTkLabel(parent, text=text, font=font(size, "bold"), text_color=color, anchor="w")