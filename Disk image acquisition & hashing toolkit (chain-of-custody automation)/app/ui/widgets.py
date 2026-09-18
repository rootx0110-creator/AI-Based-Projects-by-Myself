import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk

from .theme import PANEL, PANEL2, BORDER, ACCENT, MUTED, TEXT, font


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=PANEL, corner_radius=12,
                         border_width=1, border_color=BORDER, **kw)


class StatCard(Card):
    def __init__(self, master, label, value="0", accent=ACCENT, extra=""):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self._accent = ctk.CTkFrame(self, width=4, height=74, fg_color=accent,
                                    corner_radius=2)
        self._accent.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="ns")
        self._accent.grid_propagate(False)
        self._label = ctk.CTkLabel(self, text=label, font=font(12), text_color=MUTED, anchor="w")
        self._label.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        self._value = ctk.CTkLabel(self, text=str(value), font=font(24, "bold"), text_color=TEXT, anchor="w")
        self._value.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self._extra = ctk.CTkLabel(self, text=extra, font=font(11), text_color=MUTED, anchor="w")
        self._extra.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))

    def update(self, value=None, extra=None, accent=None):
        if value is not None:
            self._value.configure(text=str(value))
        if extra is not None:
            self._extra.configure(text=extra)
        if accent is not None:
            self._accent.configure(fg_color=accent)


class SectionCard(Card):
    def __init__(self, master, heading, **kw):
        super().__init__(master, **kw)
        self.grid_columnconfigure(0, weight=1)
        self._heading = ctk.CTkLabel(self, text=heading, font=font(14, "bold"),
                                     text_color=ACCENT, anchor="w")
        self._heading.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self._body.grid_columnconfigure(0, weight=1)

    @property
    def body(self):
        return self._body


class TreeStyler:
    """Apply a dark theme to a ttk.Treeview."""

    @staticmethod
    def apply(tree: ttk.Treeview):
        style = ttk.Style(tree)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview",
                        background=PANEL2, fieldbackground=PANEL2,
                        foreground=TEXT, borderwidth=0, rowheight=30,
                        font=font(12))
        style.configure("Treeview.Heading",
                        background=PANEL, foreground=MUTED, borderwidth=0,
                        font=font(11, "bold"))
        style.map("Treeview", background=[("selected", ACCENT)],
                  foreground=[("selected", "#04121a")])
        style.map("Treeview.Heading", background=[("active", PANEL2)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


class DarkScrollbar(ctk.CTkScrollbar):
    pass


def shade_hex(h, factor):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"