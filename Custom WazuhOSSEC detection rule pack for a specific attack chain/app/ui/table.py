"""Dark-styled ttk.Treeview helper used by the library and chain views."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from . import theme


_STYLED = False


def style_tree() -> None:
    global _STYLED
    if _STYLED:
        return
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("rp.Treeview",
                    background=theme.PANEL,
                    fieldbackground=theme.PANEL,
                    foreground=theme.FG,
                    bordercolor=theme.LINE,
                    borderwidth=0,
                    rowheight=30,
                    font=("Segoe UI", 12))
    style.configure("rp.Treeview.Heading",
                    background=theme.PANEL2,
                    foreground=theme.MUTED,
                    bordercolor=theme.LINE,
                    relief="flat",
                    font=("Segoe UI", 11, "bold"))
    style.map("rp.Treeview",
              background=[("selected", theme.ACCENT)],
              foreground=[("selected", "#ffffff")])
    style.map("rp.Treeview.Heading",
              background=[("active", theme.PANEL3)])
    _STYLED = True


def make_tree(master, columns: list[tuple[str, str, int]],
              selectmode: str = "browse") -> ttk.Treeview:
    style_tree()
    tree = ttk.Treeview(master, columns=[c[0] for c in columns],
                        show="headings", selectmode=selectmode,
                        style="rp.Treeview")
    for key, heading, width in columns:
        tree.heading(key, text=heading)
        tree.column(key, width=width, stretch=True,
                    minwidth=max(40, width // 2))
    tree.tag_configure("occ", background=theme.PANEL)
    tree.tag_configure("alt", background=theme.PANEL2)
    return tree


def attach_scrollbar(master, tree, side: str = "right") -> ctk.CTkScrollbar:
    sb = ctk.CTkScrollbar(master, command=tree.yview)
    sb.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=sb.set)
    return sb