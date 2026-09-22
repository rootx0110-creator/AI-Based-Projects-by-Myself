"""Central design tokens and ttk style configuration (dark, flat, modern)."""

import tkinter as tk
from tkinter import ttk

# --- palette -------------------------------------------------------------
BG = "#0e141b"          # app background
BG_SOFT = "#0b1017"     # sidebar / darker wells
PANEL = "#161f2a"       # cards
PANEL_ALT = "#1b2634"   # inputs / code wells
BORDER = "#263443"
BORDER_SOFT = "#1e2a38"
TEXT = "#e8eef6"
MUTED = "#8fa3b8"
ACCENT = "#2dd4bf"      # primary teal
ACCENT_DIM = "#153f42"
ACCENT_ALT = "#38bdf8"  # sky (secondary)
GOOD = "#34d399"
WARN = "#fbbf24"
DANGER = "#f87171"
HOVER = "#223040"

# --- fonts ---------------------------------------------------------------
FONT = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_NAV = ("Segoe UI", 10, "bold")
FONT_H2 = ("Segoe UI", 12, "bold")


def apply(tk_root: tk.Tk) -> None:
    """Configure ttk theme + app-wide defaults."""
    tk_root.configure(bg=BG)
    tk_root.option_add("*Font", FONT)

    style = ttk.Style(tk_root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("Rail.TFrame", background=BG_SOFT)
    style.configure("Card.TFrame", background=PANEL)

    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
    style.configure("Card.TLabel", background=PANEL, foreground=TEXT)
    style.configure("Rail.TLabel", background=BG_SOFT, foreground=TEXT)
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
    style.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("H2.TLabel", background=PANEL, foreground=TEXT, font=FONT_H2)
    style.configure("Section.TLabel", background=BG, foreground=ACCENT_ALT,
                    font=("Segoe UI", 9, "bold"))

    style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT,
                    insertcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, padding=6)
    style.configure("TRadiobutton", background=PANEL, foreground=TEXT)
    style.map("TRadiobutton", background=[("active", PANEL)])
    style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
    style.map("TCheckbutton", background=[("active", PANEL)])
    style.configure("TSpinbox", fieldbackground=PANEL_ALT, foreground=TEXT,
                    arrowsize=14)

    style.configure("TLabelframe", background=PANEL, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER)
    style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT)
    style.configure("TNotebook", background=BG, bordercolor=BORDER)
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", PANEL_ALT), ("active", PANEL_ALT)],
              foreground=[("selected", TEXT)])

    # buttons
    style.configure("TButton", background=PANEL_ALT, foreground=TEXT,
                    bordercolor=BORDER, focuscolor=PANEL_ALT,
                    padding=(12, 6), relief="flat")
    style.map("TButton",
              background=[("active", HOVER), ("pressed", HOVER)],
              bordercolor=[("active", ACCENT)])

    style.configure("Accent.TButton", background=ACCENT_DIM, foreground=ACCENT,
                    bordercolor=ACCENT, focuscolor=ACCENT_DIM, padding=(14, 7),
                    font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", "#1c4f52"), ("pressed", "#1c4f52")],
              foreground=[("active", TEXT)])

    style.configure("Ghost.TButton", background=BG, foreground=MUTED,
                    bordercolor=BORDER, focuscolor=BG, padding=(10, 5))
    style.map("Ghost.TButton", background=[("active", PANEL_ALT)],
              foreground=[("active", TEXT)])

    style.configure("Danger.TButton", background="#3a1d20", foreground=DANGER,
                    bordercolor="#5a2a30", focuscolor="#3a1d20", padding=(12, 6))
    style.map("Danger.TButton", background=[("active", "#4a2428")],
              foreground=[("active", TEXT)])

    style.configure("Nav.TButton", background=BG_SOFT, foreground=MUTED,
                    anchor="w", padding=(14, 11), relief="flat", font=FONT_NAV)
    style.map("Nav.TButton",
              background=[("active", PANEL_ALT)],
              foreground=[("active", TEXT)])
    style.configure("NavActive.TButton", background=ACCENT_DIM, foreground=ACCENT,
                    anchor="w", padding=(14, 11), relief="flat", font=FONT_NAV)
    style.map("NavActive.TButton", background=[("active", ACCENT_DIM)])

    # treeview
    style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=TEXT, bordercolor=BORDER, rowheight=30,
                    font=FONT)
    style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT,
                    bordercolor=BORDER, relief="flat", padding=(6, 6),
                    font=("Segoe UI", 9, "bold"))
    style.map("Treeview",
              background=[("selected", ACCENT_DIM)],
              foreground=[("selected", TEXT)])

    # scrollbars
    style.configure("Vertical.TScrollbar", background=PANEL_ALT,
                    troughcolor=BG, bordercolor=BG, arrowcolor=TEXT)
    style.map("Vertical.TScrollbar", background=[("active", HOVER)])
    style.configure("Horizontal.TScrollbar", background=PANEL_ALT,
                    troughcolor=BG, bordercolor=BG, arrowcolor=TEXT)
    style.map("Horizontal.TScrollbar", background=[("active", HOVER)])

    style.configure("Progressbar", background=ACCENT, troughcolor=PANEL_ALT,
                    bordercolor=PANEL_ALT, lightcolor=ACCENT, darkcolor=ACCENT)

    # separator
    style.configure("TSeparator", background=BORDER)
    style.configure("CardSep.TSeparator", background=BORDER_SOFT)