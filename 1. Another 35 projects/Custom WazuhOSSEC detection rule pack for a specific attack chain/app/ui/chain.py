"""Attack Chain view: 11-stage kill chain with per-stage rule coverage."""
from __future__ import annotations

import customtkinter as ctk

from ..rules_core import STAGES
from . import theme
from .table import attach_scrollbar, make_tree
from .widgets import Panel

SELECTED = theme.ACCENT
BG_SEL = "#24406e"


class ChainView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self._selected = STAGES[0]["key"]
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        summary = Panel(self, "Kill-chain map")
        summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.summary_label = ctk.CTkLabel(
            summary, text="", text_color=theme.MUTED, font=theme.font(12),
            anchor="w", wraplength=1080)
        self.summary_label.pack(fill="x", padx=18, pady=(6, 12))

        # stage list
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        self._stage_cards = {}
        holder = ctk.CTkScrollableFrame(box, fg_color="transparent")
        holder.grid(row=0, column=0, sticky="nsew")
        for st in STAGES:
            card = ctk.CTkFrame(holder, corner_radius=10, border_width=1,
                                border_color=theme.LINE, fg_color=theme.PANEL,
                                height=52)
            card.pack(fill="x", pady=3)
            card.grid_propagate(False)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(card, text=st["name"], text_color=theme.FG,
                         font=theme.font(13, "bold"), anchor="w")\
                .grid(row=0, column=0, sticky="w", padx=(12, 6), pady=8)
            ctk.CTkLabel(card, text=st["tactic"], text_color=theme.ACCENT,
                         font=theme.font(11))\
                .grid(row=0, column=1, sticky="e", padx=6)
            val = ctk.CTkLabel(card, text="0", text_color=theme.MUTED,
                               font=theme.font(13, "bold"), width=30)
            val.grid(row=0, column=2, sticky="e", padx=12)
            card.bind("<Button-1>", lambda _e, k=st["key"]: self._pick(k))
            for child in card.winfo_children():
                child.bind("<Button-1>",
                           lambda _e, k=st["key"]: self._pick(k))
            self._stage_cards[st["key"]] = (card, val)

        # rule table for selected stage
        panel = Panel(self, "Rules in this stage")
        panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        body = panel.content
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.stage_title = ctk.CTkLabel(
            body, text="", text_color=theme.FG, font=theme.font(14, "bold"),
            anchor="w")
        self.stage_title.grid(row=0, column=0, sticky="ew", padx=18, pady=(10, 0))
        box2 = ctk.CTkFrame(body, fg_color="transparent")
        box2.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        box2.grid_rowconfigure(0, weight=1)
        box2.grid_columnconfigure(0, weight=1)
        self.tree = make_tree(box2, [
            ("id", "Rule ID", 86),
            ("level", "Lvl", 52),
            ("mitre", "MITRE", 78),
            ("source", "Source", 110),
            ("desc", "Description", 340),
        ])
        self.tree.grid(row=0, column=0, sticky="nsew")
        attach_scrollbar(box2, self.tree)

    def _pick(self, key: str):
        self._selected = key
        for k, (card, _val) in self._stage_cards.items():
            selected = k == key
            card.configure(
                fg_color=theme.ACCENT if selected else theme.PANEL,
                border_color=theme.ACCENT if selected else theme.LINE)
            for child in card.winfo_children():
                fg = "#0b0f19" if selected else theme.FG
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=fg)
        self._render_stage()

    def refresh(self):
        stage_counts = self.app.rulepack.count_by_stage()
        covered = sum(1 for v in stage_counts.values() if v)
        total = self.app.rulepack.total
        route = " -> ".join(s["name"] for s in STAGES)
        self.summary_label.configure(
            text=f"{self.app.rulepack.name}  \u2022  {total} rules \u2022  "
                 f"{covered}/{len(STAGES)} stages covered\n{route}")
        for k, (card, val) in self._stage_cards.items():
            n = stage_counts.get(k, 0)
            val.configure(text=str(n))
            fg = "#0b0f19" if k == self._selected else theme.MUTED
            val.configure(text_color=fg)
        self._render_stage()

    def _render_stage(self):
        st = next((s for s in STAGES if s["key"] == self._selected), STAGES[0])
        self.stage_title.configure(
            text=f"{st['name']}  ({st['tactic']})  \u2014  {st['desc']}")
        self.tree.delete(*self.tree.get_children())
        rules = [r for r in self.app.rulepack.enabled()
                 if r["stage"] == self._selected]
        for idx, r in enumerate(sorted(rules, key=lambda x: int(x["id"]))):
            tag = "occ" if idx % 2 == 0 else "alt"
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r.rid, r.level, r["mitre"],
                                     r["log_source"], r["description"]),
                             tags=(tag,))