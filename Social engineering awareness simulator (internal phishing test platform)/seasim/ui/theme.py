"""Visual theme for SeaSim: colors, fonts, and ttk styling.

A single dark-slate sidebar + light content palette. All views pull
tokens from here so the app stays visually consistent.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Palette -------------------------------------------------------------------
INK = "#0f172a"          # slate-900 (sidebar, headings)
INK_2 = "#1e293b"        # slate-800
MUTED = "#64748b"        # slate-500
LINE = "#e2e8f0"         # slate-200
BG = "#f8fafc"           # slate-50 (content bg)
CARD = "#ffffff"
ACCENT = "#2563eb"       # blue-600 (primary actions)
ACCENT_DARK = "#1d4ed8"
GOOD = "#16a34a"         # green-600
WARN = "#d97706"         # amber-600
BAD = "#dc2626"          # red-600
CHIP_BG = "#eef2ff"      # indigo-50
SAFE_BG = "#ecfdf5"      # emerald-50
SAFE_FG = "#065f46"
DANGER_BG = "#fef2f2"

FONT = "Segoe UI"
MONO = "Consolas"


def configure(root: tk.Misc) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    base = (FONT, 10)
    bold = (FONT, 10, "bold")

    style.configure(".", background=BG, font=base, borderwidth=0)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("Card.TLabel", background=CARD, foreground=INK)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
    style.configure("H1.TLabel", background=BG, foreground=INK,
                    font=(FONT, 20, "bold"))
    style.configure("H2.TLabel", background=CARD, foreground=INK,
                    font=(FONT, 12, "bold"))
    style.configure("H3.TLabel", background=BG, foreground=INK,
                    font=(FONT, 12, "bold"))
    style.configure("Bold.TLabel", background=CARD, foreground=INK,
                    font=bold)

    # Buttons
    style.configure("TButton", font=base, padding=(12, 6))
    style.map("TButton",
              background=[("active", "#e2e8f0"), ("!disabled", "#ffffff")],
              foreground=[("!disabled", INK)])
    style.configure("Accent.TButton", font=bold, padding=(14, 7))
    style.map("Accent.TButton",
              background=[("active", ACCENT_DARK), ("!disabled", ACCENT)],
              foreground=[("!disabled", "#ffffff")])
    style.configure("Danger.TButton", font=bold, padding=(12, 6))
    style.map("Danger.TButton",
              background=[("active", "#b91c1c"), ("!disabled", BAD)],
              foreground=[("!disabled", "#ffffff")])

    # Treeview
    style.configure("Treeview", background=CARD, fieldbackground=CARD,
                    foreground=INK, rowheight=30, font=base)
    style.configure("Treeview.Heading", background="#f1f5f9",
                    foreground=MUTED, font=(FONT, 9, "bold"), padding=6)
    style.map("Treeview", background=[("selected", "#dbeafe")],
              foreground=[("selected", INK)])

    # Check/Radio indicators: clam can draw them nearly invisible
    # (white-on-white) on light pages - force clear colors as a safety
    # net. Critical forms use classic tk widgets instead.
    for name, bgc in (("TCheckbutton", BG), ("TRadiobutton", BG),
                      ("Card.TCheckbutton", CARD),
                      ("Card.TRadiobutton", CARD)):
        style.configure(name, background=bgc, foreground=INK,
                        focuscolor=bgc)
        style.map(name,
                  background=[("active", bgc)],
                  indicatorcolor=[("selected", ACCENT),
                                  ("!selected", "#ffffff")])

    # Notebook (used in reports)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 7), font=base)

    # Entries / comboboxes
    style.configure("TEntry", padding=4)
    style.configure("TCombobox", padding=4)


def card(parent: tk.Misc, **pack_kw) -> tk.Frame:
    """White card frame with a subtle border."""
    f = tk.Frame(parent, bg=CARD, highlightbackground=LINE,
                 highlightthickness=1)
    f.pack(**pack_kw)
    return f


def stat_tile(parent: tk.Misc, value: str, label: str, color: str = INK,
              wide: int = 0) -> tk.Frame:
    """Small metric tile used on the dashboard."""
    tile = tk.Frame(parent, bg=CARD, highlightbackground=LINE,
                    highlightthickness=1)
    tk.Label(tile, text=value, bg=CARD, fg=color,
             font=(FONT, 22, "bold")).pack(anchor="w", padx=14, pady=(10, 0))
    tk.Label(tile, text=label, bg=CARD, fg=MUTED,
             font=(FONT, 9, "bold")).pack(anchor="w", padx=14, pady=(0, 10))
    if wide:
        tile.configure(width=wide)
    return tile


def badge(parent: tk.Misc, text: str, fg: str, bg: str) -> tk.Label:
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=(FONT, 8, "bold"),
                    padx=8, pady=2)


def status_colors(status: str) -> tuple:
    """(fg, bg) chips for event/campaign statuses."""
    return {
        "Sent": (MUTED, "#f1f5f9"),
        "Opened": (WARN, "#fef3c7"),
        "Clicked": (BAD, DANGER_BG),
        "Reported": (GOOD, SAFE_BG),
        "Dismissed": (MUTED, "#f1f5f9"),
        "Draft": (MUTED, "#f1f5f9"),
        "Active": (ACCENT, "#dbeafe"),
        "Completed": (GOOD, SAFE_BG),
        "Archived": (MUTED, "#f1f5f9"),
    }.get(status, (INK, "#f1f5f9"))
