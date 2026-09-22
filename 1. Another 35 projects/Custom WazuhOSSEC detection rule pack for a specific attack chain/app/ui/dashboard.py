"""Dashboard: KPI cards, severity distribution, stage coverage, top alerts."""
from __future__ import annotations

import customtkinter as ctk

from ..rules_core import SEVERITY_BUCKETS, STAGES, severity_bucket
from . import theme
from .widgets import Panel, SectionHeader, StatCard, make_button


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(3, weight=1)

        # ---- KPI cards ---------------------------------------------------
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)
        self.card_rules = StatCard(cards, "Rules", "0", theme.ACCENT,
                                   "enabled in pack")
        self.card_stages = StatCard(cards, "Stages", "0", theme.GOOD,
                                    "of 11 covered")
        self.card_avg = StatCard(cards, "Avg severity", "0", theme.WARN,
                                 "across enabled rules")
        self.card_crit = StatCard(cards, "Critical", "0", theme.CRIT,
                                  "rules level 12+")
        self.card_rules.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card_stages.grid(row=0, column=1, sticky="ew", padx=(8, 4))
        self.card_avg.grid(row=0, column=2, sticky="ew", padx=(4, 8))
        self.card_crit.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        # ---- left: severity distribution ----------------------------------
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(0, 14))
        left.grid_columnconfigure(0, weight=1)
        panel = Panel(left, "Severity distribution")
        panel.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        self._bars = {}
        for r, b in enumerate(SEVERITY_BUCKETS):
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=(10, 6))
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=b["name"], width=76, anchor="w",
                         text_color=theme.MUTED,
                         font=theme.font(12)).grid(row=0, column=0, sticky="w")
            bar = ctk.CTkProgressBar(row, height=14, corner_radius=7,
                                     fg_color=theme.PANEL2,
                                     progress_color=b["color"])
            bar.grid(row=0, column=1, sticky="ew", padx=6)
            bar.set(0)
            val = ctk.CTkLabel(row, text="0", width=56, anchor="e",
                               text_color=theme.FG, font=theme.font(12, "bold"))
            val.grid(row=0, column=2)
            self._bars[b["name"]] = (bar, val)

        # ---- right: stage coverage -----------------------------------------
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", pady=(0, 14))
        right.grid_columnconfigure(0, weight=1)
        panel = Panel(right, "Kill-chain stage coverage")
        panel.grid(row=0, column=0, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        self._stage_rows = {}
        for r, st in enumerate(STAGES):
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=(6, 2))
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=st["name"], width=150, anchor="w",
                         text_color=theme.FG,
                         font=theme.font(12)).grid(row=0, column=0, sticky="w")
            bar = ctk.CTkProgressBar(row, height=10, corner_radius=5,
                                     fg_color=theme.PANEL2,
                                     progress_color=theme.ACCENT)
            bar.grid(row=0, column=1, sticky="ew", padx=6)
            val = ctk.CTkLabel(row, text="0", width=34, anchor="e",
                               text_color=theme.MUTED, font=theme.font(11))
            val.grid(row=0, column=2)
            self._stage_rows[st["key"]] = (bar, val)

        # ---- bottom: top alerts --------------------------------------------
        bottom = Panel(self, "Notable detections (highest severity first)")
        bottom.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 0))
        bottom.content.grid_rowconfigure(0, weight=1)
        bottom.content.grid_columnconfigure(0, weight=1)
        self._top = ctk.CTkScrollableFrame(bottom.content, fg_color="transparent")
        self._top.grid(row=0, column=0, sticky="nsew", padx=18, pady=12)
        self.grid_rowconfigure(2, weight=1)

    def refresh(self):
        pack = self.app.rulepack
        self.card_rules.set(pack.total)
        self.card_stages.set(pack.stages_covered)
        self.card_avg.set(pack.avg_level)
        counts = pack.count_by_severity()
        total = max(sum(counts.values()), 1)
        for name, (bar, val) in self._bars.items():
            n = counts.get(name, 0)
            bar.set(n / total)
            val.configure(text=str(n))
        stage_counts = pack.count_by_stage()
        max_s = max(stage_counts.values(), default=1)
        for key, (bar, val) in self._stage_rows.items():
            n = stage_counts.get(key, 0)
            bar.set(n / max(1, max_s))
            val.configure(text=str(n))

        for w in self._top.winfo_children():
            w.destroy()
        notable = sorted(pack.enabled(), key=lambda r: (-r.level, int(r["id"])))[:8]
        if not notable:
            ctk.CTkLabel(self._top, text="No rules in the pack yet.",
                         text_color=theme.MUTED, font=theme.font(12)).pack(anchor="w")
            return
        for r in notable:
            b = severity_bucket(r.level)
            row = ctk.CTkFrame(self._top, fg_color=theme.PANEL2,
                               corner_radius=8)
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(2, weight=1)
            ctk.CTkLabel(row, text=f"L{r.level}", width=52, anchor="w",
                         text_color=theme.severity_level_color(r.level),
                         font=theme.font(13, "bold")).grid(row=0, column=0, padx=10, pady=8)
            ctk.CTkLabel(row, text=r.rid, width=64, anchor="w",
                         text_color=theme.MUTED,
                         font=theme.font(12)).grid(row=0, column=1)
            ctk.CTkLabel(row, text=r["description"], anchor="w",
                         text_color=theme.FG,
                         font=theme.font(12)).grid(row=0, column=2, sticky="w", padx=6)
            ctk.CTkLabel(row, text=r.stage_name, width=150, anchor="e",
                         text_color=theme.ACCENT,
                         font=theme.font(12)).grid(row=0, column=3, padx=12)