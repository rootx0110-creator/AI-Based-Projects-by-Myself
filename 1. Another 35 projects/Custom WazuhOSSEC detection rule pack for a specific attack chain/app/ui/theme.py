"""Central theme for the RulePackStudio GUI."""
from __future__ import annotations

import customtkinter as ctk

# ---- palette ------------------------------------------------------------
BG = "#0b0f19"
PANEL = "#131a2b"
PANEL2 = "#1b2439"
PANEL3 = "#232e4a"
LINE = "#2b3753"
FG = "#e8edf7"
MUTED = "#8b96ad"
ACCENT = "#4f8cff"
ACCENT_HOVER = "#3d74d8"
DANGER = "#e74c3c"
DANGER_HOVER = "#c0392b"
GOOD = "#2ecc71"
WARN = "#f39c12"
HI = "#e67e22"
CRIT = "#e74c3c"

SEVERITY_COLORS = {
    "Low": "#7f8c8d",
    "Medium": "#f39c12",
    "High": "#e67e22",
    "Critical": "#e74c3c",
}

NAV = [
    ("dashboard", "Dashboard"),
    ("library", "Rule Library"),
    ("chain", "Attack Chain"),
    ("builder", "Rule Builder"),
    ("reports", "Reports"),
]


def init() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


def mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="Consolas", size=size)


def severity_level_color(level: int) -> str:
    if level >= 12:
        return CRIT
    if level >= 8:
        return HI
    if level >= 5:
        return WARN
    return "#7f8c8d"