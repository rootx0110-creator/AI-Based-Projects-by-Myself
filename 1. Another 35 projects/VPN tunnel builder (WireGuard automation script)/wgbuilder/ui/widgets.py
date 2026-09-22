"""Reusable UI building blocks: cards, headers, buttons, scroll containers."""

import tkinter as tk
from tkinter import ttk

from wgbuilder.ui import theme


def lighter(hexcolor: str, amount: int = 0):
    """Return a slightly lighter or darker variant of a hex colour."""
    hexcolor = hexcolor.lstrip("#")
    vals = [int(hexcolor[i:i + 2], 16) for i in (0, 2, 4)]
    vals = [min(255, max(0, v + amount)) for v in vals]
    return "#%02x%02x%02x" % tuple(vals)


class Card(ttk.Frame):
    """Themed panel used across all views."""

    def __init__(self, master, title: str = "", accent: str | None = None, **kw):
        super().__init__(master, style="Card.TFrame", **kw)
        self.columnconfigure(0, weight=1)
        if title:
            head = ttk.Frame(self, style="Card.TFrame")
            head.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 2))
            head.columnconfigure(1, weight=1)
            bar = tk.Frame(head, width=3, height=16, bg=accent or theme.ACCENT)
            bar.grid(row=0, column=0, sticky="ns", padx=(0, 8))
            lbl = ttk.Label(head, text=title, style="H2.TLabel")
            lbl.grid(row=0, column=1, sticky="w")
            self.title_label = lbl
        self.body = ttk.Frame(self, style="Card.TFrame")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(6, 16))
        self.body.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)


class SectionTitle(ttk.Label):
    def __init__(self, master, text: str, bg: str = theme.BG):
        super().__init__(master, text=text.upper(), style="Section.TLabel")
        if bg != theme.BG:
            self.configure(background=bg)


class StatCard(ttk.Frame):
    """KPI card with a big value, caption and an accent strip."""

    def __init__(self, master, value="", caption="", accent=theme.ACCENT, big="", **kw):
        super().__init__(master, style="Card.TFrame", **kw)
        self.value = tk.StringVar(value=value)
        self.big = tk.StringVar(value=big)
        self.caption = tk.StringVar(value=caption)
        strip = tk.Frame(self, width=4, bg=accent)
        strip.pack(side="left", fill="y")
        inner = ttk.Frame(self, style="Card.TFrame")
        inner.pack(side="left", fill="both", expand=True, padx=(14, 14), pady=12)
        ttk.Label(inner, textvariable=self.value, background=theme.PANEL,
                  foreground=accent, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(inner, textvariable=self.caption, style="CardMuted.TLabel",
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))


class KeyField(ttk.Frame):
    """A wrapped, monospace read-only field with a copy button."""

    def __init__(self, master, label: str, value="", mono_font: str | None = None,
                 bg=theme.PANEL, on_copy=None):
        super().__init__(master, style="Card.TFrame")
        self.columnconfigure(0, weight=1)
        tk.Label(self, text=label, bg=bg, fg=theme.MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        row = ttk.Frame(self, style="Card.TFrame")
        row.grid(row=1, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)
        self.var = tk.StringVar(value=value)
        box = tk.Text(row, height=3, wrap="char", relief="flat",
                      bg=theme.PANEL_ALT, fg=theme.TEXT, insertbackground=theme.TEXT,
                      font=mono_font or theme.FONT_MONO, padx=10, pady=8)
        box.insert("1.0", value)
        box.configure(state="disabled")
        box.grid(row=0, column=0, sticky="ew")
        self.box = box
        btn = ttk.Button(row, text="Copy", style="Ghost.TButton", width=7,
                         command=lambda: self._copy(on_copy))
        btn.grid(row=0, column=1, padx=(8, 0), sticky="ns")
        self._mono_font = mono_font or theme.FONT_MONO

    def _copy(self, on_copy=None):
        self.clipboard_clear()
        self.clipboard_append(self.var.get())
        if on_copy:
            on_copy(self.var.get())

    def set(self, value: str):
        self.var.set(value)
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("1.0", value)
        self.box.configure(state="disabled")


class ScrollPage(ttk.Frame):
    """Scrollable container for long-form views (reports/settings)."""

    def __init__(self, master, bg=theme.BG):
        super().__init__(master, style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        vbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        vbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=vbar.set)
        inner = ttk.Frame(canvas, style="TFrame")
        self.inner = inner
        self._win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(
            self._win, width=e.width))
        self.canvas = canvas
        canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event):
        if self.winfo_ismapped() and self.canvas.winfo_ismapped():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")


class Footer(ttk.Frame):
    """Status/notification bar across the bottom of the window."""

    def __init__(self, master):
        super().__init__(master, style="Panel.TFrame")
        self.columnconfigure(0, weight=1)
        self._msg = tk.StringVar(value="Ready")
        self._color = theme.MUTED
        lbl = tk.Label(self, textvariable=self._msg, anchor="w", padx=16, pady=6,
                       bg=theme.PANEL, fg=theme.MUTED, font=("Segoe UI", 9))
        lbl.grid(row=0, column=0, sticky="ew")
        self._lbl = lbl
        meta = tk.StringVar(value="")
        self._meta = tk.Label(self, textvariable=meta, padx=16, pady=6,
                              bg=theme.PANEL, fg=theme.MUTED, font=("Segoe UI", 9))
        self._meta.grid(row=0, column=1, sticky="e")
        self.meta_var = meta
        self._timer = None

    def notify(self, message: str, level: str = "info", timeout_ms: int = 6000):
        color = {"info": theme.MUTED, "good": theme.GOOD,
                 "warn": theme.WARN, "error": theme.DANGER}.get(level, theme.MUTED)
        self._msg.set(message)
        self._lbl.configure(fg=color)
        if self._timer:
            self.after_cancel(self._timer)
        self._timer = self.after(timeout_ms, self._reset)

    def _reset(self):
        self._msg.set("Ready")
        self._lbl.configure(fg=theme.MUTED)