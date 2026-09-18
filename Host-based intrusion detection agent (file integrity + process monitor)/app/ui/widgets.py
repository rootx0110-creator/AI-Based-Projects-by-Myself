from tkinter import ttk

import customtkinter as ctk

from .theme import (ACCENT, ACCENT_DARK, ACCENT_TEXT, BG, BORDER, CARD, CARD_HOVER,
                    CRIT, hx, FONT_FAMILY, INFO, MUTED, PANEL, SEV_COLORS, TEXT, WARN)


def _style_tree(base="Treeview"):
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure(
        base,
        background=PANEL,
        fieldbackground=PANEL,
        foreground=TEXT,
        borderwidth=0,
        relief="flat",
        rowheight=26,
        font=(FONT_FAMILY, 11),
    )
    s.configure(
        base + ".Heading",
        background=CARD,
        foreground=MUTED,
        borderwidth=0,
        relief="flat",
        padding=(6, 6),
        font=(FONT_FAMILY, 10, "bold"),
    )
    s.map(
        base,
        background=[("selected", ACCENT_DARK)],
        foreground=[("selected", "#ffffff")],
    )
    return s


def make_tree(parent, columns, widths, height=8, show="headings"):
    _style_tree("Treeview")
    tree = ttk.Treeview(parent, columns=columns, show=show, height=height, selectmode="extended")
    for col, w in zip(columns, widths):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=w, anchor="w", stretch=False)
    tree.tag_configure("sev_1", foreground=INFO)
    tree.tag_configure("sev_2", foreground=WARN)
    tree.tag_configure("sev_3", foreground=CRIT)
    tree.tag_configure("muted", foreground=MUTED)
    tree.tag_configure("ok", foreground="#3fb950")
    tree.tag_configure("hl", foreground=ACCENT_TEXT)
    return tree


def make_scrollbar(parent, tree, side="right", padx=2):
    sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    sb.pack(side=side, fill="y", padx=(0, padx))
    tree.configure(yscrollcommand=sb.set)


def clear_tree(tree):
    for item in tree.get_children():
        tree.delete(item)


def card(parent, title=None, accent=None):
    f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
    if title:
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(10, 2))
        dot = ctk.CTkFrame(bar, width=8, height=8, corner_radius=4,
                           fg_color=accent or ACCENT)
        dot.pack(side="left", padx=(0, 8), pady=6)
        ctk.CTkLabel(bar, text=title, font=(FONT_FAMILY, 13, "bold"),
                     text_color=TEXT).pack(side="left")
    return f


def stat_card(parent, label, value, sub="", accent=ACCENT):
    f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
    f.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(f, text="", width=4, fg_color=accent, corner_radius=2).grid(
        row=0, column=0, rowspan=2, sticky="ns", padx=8, pady=10)
    ctk.CTkLabel(f, text=label, font=(FONT_FAMILY, 11), text_color=MUTED,
                 anchor="w").grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 0))
    ctk.CTkLabel(f, text=str(value), font=(FONT_FAMILY, 24, "bold"),
                 text_color=TEXT, anchor="w").grid(row=1, column=1, sticky="ew",
                                                   padx=(0, 12), pady=(0, 2))
    if sub:
        ctk.CTkLabel(f, text=sub, font=(FONT_FAMILY, 10), text_color=MUTED,
                     anchor="w").grid(row=2, column=1, columnspan=2, sticky="ew",
                                      padx=(0, 12), pady=(0, 10))
    return f


def build_btn(parent, text, command, primary=False, width=None):
    kw = dict(
        text=text,
        command=command,
        corner_radius=8,
        height=30,
        font=(FONT_FAMILY, 12, "bold" if primary else "normal"),
        fg_color=ACCENT if primary else CARD,
        hover_color=ACCENT_DARK if primary else CARD_HOVER,
        border_width=1 if not primary else 0,
        border_color=BORDER,
        text_color="#ffffff" if primary else TEXT,
    )
    if width:
        kw["width"] = width
    return ctk.CTkButton(parent, **kw)


def build_label(parent, text, size=12, weight="normal", color=TEXT, **kw):
    return ctk.CTkLabel(parent, text=text, font=(FONT_FAMILY, size, weight),
                        text_color=color, **kw)


def build_switch(parent, text, variable, command=None):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(row, text=text, font=(FONT_FAMILY, 12), text_color=TEXT).pack(side="left")
    sw = ctk.CTkSwitch(row, text="", variable=variable, command=command,
                       progress_color=ACCENT, fg_color=PANEL, border_color=BORDER)
    sw.pack(side="right")
    return row, sw


def entry(parent, initial="", placeholder=""):
    e = ctk.CTkEntry(parent, width=220, height=30, corner_radius=8,
                     fg_color=PANEL, border_color=BORDER, text_color=TEXT,
                     placeholder_text=placeholder,
                     font=(FONT_FAMILY, 12))
    e.insert(0, initial)
    return e