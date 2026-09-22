"""Reusable styled widgets built on ttk + theme tokens.

Provides:
    setup_style(root)
    Panel / Card  — flat white panels with soft border
    SectionTitle
    Metric        — key/value pair used in result grids
    ResultTable   — striped read-only tree with monospace cells
    primary / ghost button factories
Exports classes so pages stay declarative.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as T

ACCENT = {"bg": T.PANEL, "activebackground": T.PANEL,
          "relief": "flat", "borderwidth": 0}

# ── Style bootstrap on the root -------------------------------------------------

def setup_style(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")
    fg, bg = T.INK, T.BG
    style.configure(".", font=T.FONT, background=bg, foreground=fg)

    style.configure("TFrame", background=bg)
    style.configure("Panel.TFrame", background=T.PANEL)
    style.configure("Header.TFrame", background=T.HEADER_BG)

    # root option: Header labels
    style.configure("HeaderTitle.TLabel", background=T.HEADER_BG,
                    foreground=T.HEADER_FG, font=T.FONT_TITLE)
    style.configure("HeaderSub.TLabel", background=T.HEADER_BG,
                    foreground="#C7D2E0", font=T.FONT_SMALL)

    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Panel.TLabel", background=T.PANEL, foreground=fg)
    style.configure("Muted.TLabel", background=T.PANEL, foreground=T.MUTED)
    style.configure("OnBgMuted.TLabel", background=bg, foreground=T.MUTED)
    style.configure("CardTitle.TLabel", background=T.PANEL, foreground=fg,
                    font=T.FONT_HDR)
    style.configure("MetricKey.TLabel", background=T.PANEL, foreground=T.MUTED,
                    font=T.FONT_SMALL)
    style.configure("MetricValue.TLabel", background=T.PANEL, foreground=T.INK,
                    font=T.FONT_MONO_B)
    style.configure("Section.TLabel", background=bg, foreground=fg,
                    font=T.FONT_HDR)
    style.configure("SectionOnPanel.TLabel", background=T.PANEL, foreground=fg,
                    font=T.FONT_HDR)

    style.configure("TEntry", fieldbackground=T.PANEL, background=T.PANEL,
                    foreground=fg, insertcolor=T.ACCENT, bordercolor=T.GRID,
                    lightcolor=T.GRID, darkcolor=T.GRID)
    style.map("TEntry", bordercolor=[("focus", T.ACCENT)])

    style.configure("TCheckbutton", background=bg, foreground=fg)

    style.configure("TRadiobutton", background=bg, foreground=fg)
    style.configure("Panel.TRadiobutton", background=T.PANEL, foreground=fg)

    style.configure("TCombobox", fieldbackground=T.PANEL, background=T.PANEL,
                    foreground=fg, arrowcolor=T.MUTED, bordercolor=T.GRID,
                    lightcolor=T.GRID, darkcolor=T.GRID)
    style.map("TCombobox", bordercolor=[("focus", T.ACCENT)],
              fieldbackground=[("readonly", T.PANEL)])

    style.configure("TSpinbox", fieldbackground=T.PANEL, background=T.PANEL,
                    foreground=fg, arrowcolor=T.MUTED, bordercolor=T.GRID,
                    lightcolor=T.GRID, darkcolor=T.GRID,
                    buttonsize=20)
    style.map("TSpinbox", bordercolor=[("focus", T.ACCENT)],
              arrowcolor=[("active", T.ACCENT)])
    style.configure("TButton", padding=(14, 7), relief="flat",
                    background=T.ACCENT, foreground="#fff", font=T.FONT_B,
                    bordercolor=T.ACCENT, focuscolor=T.ACCENT)
    style.map("TButton",
              background=[("active", T.ACCENT_HVR), ("pressed", T.ACCENT_HVR),
                          ("disabled", "#B6C2D1")],
              foreground=[("disabled", "#EAF0F6")])

    style.configure("Ghost.TButton", background=T.PANEL, foreground=T.ACCENT,
                    bordercolor=T.GRID)
    style.map("Ghost.TButton",
              background=[("active", "#E7EEF8"), ("pressed", "#DCE6F4")],
              foreground=[("disabled", T.MUTED)],
              bordercolor=[("disabled", T.GRID)])

    style.configure("Danger.TButton", background=T.ER, foreground="#fff",
                    bordercolor=T.ER)
    style.map("Danger.TButton",
              background=[("active", "#7F1D1D"), ("pressed", "#7F1D1D")])

    # Notebook
    style.configure("TNotebook", background=bg, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(22, 10), background="#DDE6F0",
                    foreground=T.MUTED, font=T.FONT_B, borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", T.PANEL)],
              foreground=[("selected", T.INK)],
              expand=[("selected", [1, 1, 1, 0])])

    # Labelframe
    style.configure("TLabelframe", background=bg, bordercolor=T.GRID,
                    lightcolor=T.GRID, darkcolor=T.GRID)
    style.configure("TLabelframe.Label", background=bg, foreground=T.MUTED,
                    font=T.FONT_SMALL)

    # Treeview
    style.configure("Treeview",
                    background=T.PANEL, fieldbackground=T.PANEL,
                    foreground=T.INK, rowheight=28, borderwidth=0,
                    font=T.FONT)
    style.configure("Treeview.Heading",
                    background="#EEF4FB", foreground="#334155",
                    font=T.FONT_B, relief="flat", padding=(8, 7))
    style.map("Treeview", background=[("selected", T.SELECT_BG)],
              foreground=[("selected", T.INK)])
    style.layout("Treeview", [("Treeview.treearea",
                               {"sticky": "nswe"})])

    style.configure("Vertical.TScrollbar", background="#C7D2E0",
                    troughcolor=bg, bordercolor=bg, arrowcolor=T.MUTED,
                    relief="flat")
    style.map("Vertical.TScrollbar",
              background=[("active", T.ACCENT), ("pressed", T.ACCENT)])
    style.configure("Horizontal.TScrollbar", background="#C7D2E0",
                    troughcolor=bg, bordercolor=bg, arrowcolor=T.MUTED,
                    relief="flat")
    style.map("Horizontal.TScrollbar",
              background=[("active", T.ACCENT), ("pressed", T.ACCENT)])

    style.configure("Status.TLabel", background="#E2E9F2", foreground=T.MUTED,
                    font=T.FONT_SMALL)
    return style


# ── Components -------------------------------------------------------------------

class Panel(tk.Frame):
    """Flat white rounded-feel panel for cards."""

    def __init__(self, master, padding=16, **kw):
        super().__init__(master, bg=T.PANEL, highlightthickness=1,
                         highlightbackground=T.GRID, highlightcolor=T.GRID, **kw)
        if padding:
            self.configure(padx=padding, pady=padding)


class Card(Panel):
    """A titled card. `title` None renders only the body."""

    def __init__(self, master, title=None, padding=16, **kw):
        super().__init__(master, padding=padding, **kw)
        if title:
            self.title_label = ttk.Label(self, text=title, style="CardTitle.TLabel")
        else:
            self.title_label = None
        self.body = tk.Frame(self, bg=T.PANEL)
        if self.title_label is not None:
            self.title_label.pack(fill="x", pady=(0, 10), padx=0)
        self.body.pack(fill="both", expand=True)

    def set_title(self, text: str):
        if self.title_label is not None:
            self.title_label.configure(text=text)


class SectionTitle(ttk.Label):
    def __init__(self, master, text):
        super().__init__(master, text=text, style="Section.TLabel")


class Metric(tk.Frame):
    """Key/value datum displayed inside a card."""

    def __init__(self, master, key, value="–"):
        super().__init__(master, bg=T.PANEL)
        self.key_label = ttk.Label(self, text=key, style="MetricKey.TLabel")
        self.value_label = ttk.Label(self, text=value, style="MetricValue.TLabel")
        self.key_label.pack(anchor="w")
        self.value_label.pack(anchor="w", pady=(2, 0))
        self.set = self.value_label.configure

    def set_text(self, text: str):
        self.value_label.configure(text=text)


def primary_button(master, text, command=None) -> ttk.Button:
    return ttk.Button(master, text=text, command=command, style="TButton")


def ghost_button(master, text, command=None) -> ttk.Button:
    return ttk.Button(master, text=text, command=command, style="Ghost.TButton")


def danger_button(master, text, command=None) -> ttk.Button:
    return ttk.Button(master, text=text, command=command, style="Danger.TButton")


class ResultTable(tk.Frame):
    """Striped read-only treeview with scrollbars and optional mono cells."""

    def __init__(self, master, columns, mono_columns=(), height=12, selectable=True):
        super().__init__(master, bg=T.PANEL)
        self.columns = columns
        self.mono_cols = set(mono_columns)

        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                 height=height, selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col)
            anchor = "e" if col in self.mono_cols else "w"
            self.tree.column(col, width=100, minwidth=64, anchor=anchor,
                             stretch=True)

        self.tree.tag_configure("even", background=T.PANEL)
        self.tree.tag_configure("odd", background=T.ZEBRA)
        mono_fg = {"foreground": T.INK}
        self.tree.tag_configure("mono", font=T.FONT_MONO)
        self.tree.tag_configure("warn", foreground=T.WARN, font=T.FONT_B)

        vs = ttk.Scrollbar(self, orient="vertical", style="Vertical.TScrollbar",
                           command=self.tree.yview)
        hs = ttk.Scrollbar(self, orient="horizontal", style="Horizontal.TScrollbar",
                           command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def populate(self, rows, keys, mono=(), warn_rows=()):
        """`rows`: sequence of dicts; `keys`: ordering; `mono`: column keys
        that should render monospace; same length as columns."""
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            tag = ("odd",) if i % 2 else ("even",)
            values = [row.get(k, "") for k in keys] if isinstance(row, dict) else row
            self.tree.insert("", "end", values=[str(v) for v in values],
                             tags=tag, iid=str(i))

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def selected_iids(self):
        return list(self.tree.selection())