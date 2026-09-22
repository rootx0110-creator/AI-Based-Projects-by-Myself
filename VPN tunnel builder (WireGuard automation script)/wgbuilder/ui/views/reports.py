"""Reports & Logs: HTML report download + activity trail + preview notes."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Card, SectionTitle


class ReportsView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store

    def build(self):
        body = ttk.Frame(self.container, style="TFrame")
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        top = Card(body, title="HTML report")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(top.body, text="A single self-contained HTML file with embedded CSS "
                 "and inline QR images - easy to e-mail, archive or attach to a "
                 "findings document.", bg=theme.PANEL, fg=theme.MUTED, justify="left",
                 wraplength=720).pack(anchor="w", pady=(0, 6))

        self.opt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top.body, text="Open the report in the browser after saving",
                        variable=self.opt_var).pack(anchor="w")
        bar = ttk.Frame(top.body, style="Card.TFrame")
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text="\u2693  Download HTML report\u2026",
                   style="Accent.TButton", command=self._download).pack(side="left")
        ttk.Button(bar, text="Open last report", style="Ghost.TButton",
                   command=self._open_last).pack(side="left", padx=8)
        self.last_var = tk.StringVar(value="No report saved this session")
        tk.Label(bar, textvariable=self.last_var, bg=theme.PANEL, fg=theme.MUTED,
                 font=("Segoe UI", 9)).pack(side="left", padx=10)

        info = Card(body, title="What goes into the document", accent=theme.ACCENT_ALT)
        info.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        rows = [
            "Summary cards: readiness, keys, port, subnet, endpoint",
            "Server detail incl. public key and MTU/DNS policy",
            "Peer inventory table with addresses and public keys",
            "Full wg0.conf (server) rendered verbatim",
            "Every client config with its scannable QR code",
            "Export history and the full activity log",
        ]
        for r in rows:
            tk.Label(info.body, text="\u2022  " + r, bg=theme.PANEL, fg=theme.TEXT,
                     anchor="w").pack(anchor="w", pady=1)

        SectionTitle(body, "Activity log").grid(row=2, column=0, sticky="w", pady=(4, 8))
        self.tree = ttk.Treeview(body, columns=("at", "level", "msg"), show="headings")
        self.tree.heading("at", text="When")
        self.tree.heading("level", text="Level")
        self.tree.heading("msg", text="Event")
        self.tree.column("at", width=170, stretch=False)
        self.tree.column("level", width=70, anchor="center", stretch=False)
        self.tree.column("msg", width=700)
        self.tree.grid(row=3, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        vsb.grid(row=3, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.refresh()

    def refresh(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        for e in reversed(self.store.events):
            self.tree.insert("", "end", values=(
                str(e.get("at", ""))[:19].replace("T", " "),
                (e.get("level") or "info").upper(), e.get("message", "")))

    def _download(self):
        path = self.app.generate_report(auto_open=self.opt_var.get())
        if path:
            self.last_var.set(path)

    def _open_last(self):
        p = self.last_var.get()
        if os.path.exists(p):
            os.startfile(p)
        else:
            messagebox.showinfo("Reports", "No report saved this session yet.")