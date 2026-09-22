"""Reports: generate offline HTML reports and manage the exports folder."""
from __future__ import annotations

import os
from tkinter import filedialog

import customtkinter as ctk

from ..report import (generate_matrix_report, generate_pack_report,
                      generate_severity_report, generate_single_rule_report)
from . import theme
from .widgets import Panel, make_button

REPORTS = [
    ("pack", "Full Pack Report", "Summary, severity bars, kill-chain coverage and full XML listing."),
    ("matrix", "Coverage Matrix", "Stage x rule matrix with MITRE ATT&CK mapping."),
    ("severity", "Severity Report", "All rules grouped by severity bucket."),
    ("single", "Single Rule Report", "One rule addressed in detail."),
]


class ReportsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---------- destination + actions ---------------------------------
        dest = Panel(self, "Destination & generate")
        dest.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        body = dest.content
        body.grid_columnconfigure(0, weight=1)
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=18, pady=(8, 6))
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Export folder", text_color=theme.MUTED,
                     font=theme.font(11)).grid(row=0, column=0, sticky="w")
        self.folder_var = ctk.StringVar(value=self.app.export_dir)
        self.folder_entry = ctk.CTkEntry(row, textvariable=self.folder_var,
                                         fg_color=theme.PANEL2,
                                         border_color=theme.LINE,
                                         font=theme.font(12))
        self.folder_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        make_button(row, "Browse...", self._browse, "ghost")\
            .grid(row=1, column=1, sticky="e")

        # report type cards
        cards = ctk.CTkFrame(body, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=18, pady=(6, 4))
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)
        self._cards = {}
        for i, (key, name, sub) in enumerate(REPORTS):
            card = ctk.CTkFrame(cards, corner_radius=10, border_width=1,
                                border_color=theme.LINE, fg_color=theme.PANEL)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            title = ctk.CTkLabel(card, text=name.upper(), text_color=theme.FG,
                                 font=theme.font(12, "bold"), anchor="w")
            title.pack(fill="x", padx=12, pady=(12, 4))
            ctk.CTkLabel(card, text=sub, text_color=theme.MUTED,
                         font=theme.font(11), anchor="w", justify="left",
                         wraplength=220).pack(fill="x", padx=12)
            btn = make_button(card, "Generate HTML",
                              lambda k=key: self._gen_report(k), "ghost")
            btn.pack(fill="x", padx=12, pady=(10, 12))
            self._cards[key] = card

        # single-rule picker row
        pick = ctk.CTkFrame(body, fg_color="transparent")
        pick.grid(row=2, column=0, sticky="ew", padx=18, pady=(2, 12))
        ctk.CTkLabel(pick, text="Single rule:", text_color=theme.MUTED,
                     font=theme.font(11)).pack(side="left")
        self.rule_menu = ctk.CTkOptionMenu(
            pick, values=self._rule_values(), fg_color=theme.PANEL2,
            button_color=theme.PANEL3, button_hover_color=theme.ACCENT,
            text_color=theme.FG, dropdown_fg_color=theme.PANEL2,
            dropdown_hover_color=theme.ACCENT, font=theme.font(12),
            height=30, corner_radius=8, width=220)
        self.rule_menu.pack(side="left", padx=(8, 0))

        # ---------- exports list -------------------------------------------
        panel = Panel(self, "Generated reports")
        panel.grid(row=1, column=0, sticky="nsew")
        body = panel.content
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.list_frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, sticky="nsew",
                             padx=18, pady=(0, 14))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(1, weight=1)

    def _rule_values(self) -> list[str]:
        memo = {}
        for r in self.app.rulepack.enabled():
            memo[r.rid] = f"{r.rid}  \u2022  {r['description'][:44]}"
        return [memo[k] for k in sorted(memo, reverse=True)]

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.folder_var.get())
        if d:
            self.folder_var.set(d)

    def _gen_report(self, key: str):
        def _go():
            dest = self.folder_var.get()
            try:
                os.makedirs(dest, exist_ok=True)
            except OSError as exc:
                self.app.set_status(f"Bad folder: {exc}")
                return
            rid = None
            if key == "single":
                rid = int(self.rule_menu.get().split()[0])
            try:
                html = {
                    "pack": lambda: generate_pack_report(self.app.rulepack),
                    "matrix": lambda: generate_matrix_report(self.app.rulepack),
                    "severity": lambda: generate_severity_report(self.app.rulepack),
                    "single": lambda: generate_single_rule_report(self.app.rulepack, rid),
                }[key]()
                stem = {"pack": "rulepack_full", "matrix": "coverage_matrix",
                        "severity": "severity_report",
                        "single": f"rule_{rid:06d}"}[key]
                path = os.path.join(dest, f"{stem}.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
                self.app.open_report_in_browser(path)
                self.app.set_status(f"Report written: {path}")
                self._load_exports(dest)
            except Exception as exc:  # noqa: BLE001
                self.app.set_status(f"Generation failed: {exc}")
        _go()

    def _load_exports(self, folder: str | None = None):
        folder = folder or self.folder_var.get()
        for w in self.list_frame.winfo_children():
            w.destroy()
        try:
            files = sorted((f for f in os.listdir(folder)
                            if f.lower().endswith(".html")), reverse=True)
        except OSError:
            files = []
        if not files:
            ctk.CTkLabel(self.list_frame, text="No HTML reports yet.",
                         text_color=theme.MUTED,
                         font=theme.font(12)).grid(row=0, column=0, sticky="w")
            return
        for i, name in enumerate(files[:50]):
            path = os.path.join(folder, name)
            size = os.path.getsize(path)
            row = ctk.CTkFrame(self.list_frame, fg_color=theme.PANEL2,
                               corner_radius=8)
            row.grid(row=i, column=0, columnspan=2, sticky="ew", pady=2)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=name, text_color=theme.FG,
                         font=theme.font(12), anchor="w").grid(
                row=0, column=0, sticky="w", padx=12, pady=6)
            ctk.CTkLabel(row, text=f"{size/1024:.1f} KB",
                         text_color=theme.MUTED, font=theme.font(11)).grid(
                row=0, column=1, padx=6)
            make_button(row, "Open", lambda p=path: self.app.open_report_in_browser(p),
                        "ghost").grid(row=0, column=2, padx=6)

    def refresh(self):
        self.rule_menu.configure(values=self._rule_values())
        self._load_exports()