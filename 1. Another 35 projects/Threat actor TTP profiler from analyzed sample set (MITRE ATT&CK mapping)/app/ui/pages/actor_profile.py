"""Threat Actor page: TTP similarity ranking + actor detail."""

from __future__ import annotations

import customtkinter as ctk

from .. import theme
from .. import widgets as w
from ...core.tactics import heat_color


class ActorPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.selected = None
        

    def _build(self) -> None:
        self.content = ctk.CTkFrame(self.frame, fg_color=theme.BG)
        self.content.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        w.header(self.content, "Threat Actor Profile",
                 "TTP signature similarity against the tracked actor knowledge base").grid(
            row=0, column=0, sticky="ew", pady=(0, 8))

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=3)
        self.content.grid_rowconfigure(2, weight=2)

        # Full-width card for the overlap matrix: inside the narrow detail
        # panel it demanded ~1700px of horizontal scroll and inflated the
        # panel's internal column, pushing text past the window edge.
        grid_card = w.card(self.content, "Actor × Technique Overlap — top 8 actors",
                           row=2, column=0, pady=(8, 0))
        grid_card.grid_rowconfigure(0, weight=1)
        self.grid_box = ctk.CTkFrame(grid_card.body, fg_color="transparent")
        self.grid_box.grid(row=0, column=0, sticky="nsew")

        rank_card = w.card(body, "Ranked Actor Matches", row=0, column=0)
        rank_card.grid_rowconfigure(0, weight=1)
        self.list = ctk.CTkScrollableFrame(rank_card.body, fg_color="transparent")
        self.list.grid(row=0, column=0, sticky="nsew")

        detail = w.card(body, "Actor Detail", row=0, column=1)
        detail.grid_rowconfigure(1, weight=1)
        self.detail_empty = w.empty_state(detail, "No actors profiled yet.\nRun analysis to compare the "
                                                  "detected TTP set against known groups.")
        self.detail_empty.grid(row=1, column=0, padx=10, pady=10)
        # Scrollable so long descriptions, tool lists and the overlap grid all
        # stay reachable inside the panel instead of running past the window.
        self.detail_box = ctk.CTkScrollableFrame(detail, fg_color="transparent")
        self.detail_box.grid(row=1, column=0, sticky="nsew")
        self.detail_box.grid_remove()

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()
        wb = self.app.workbench
        if not wb.actors:
            self.detail_empty.grid()
            self.detail_box.grid_remove()
            self.selected = None
            self._build_overlap_grid()
            return

        for i, a in enumerate(wb.actors[:14]):
            self._add_actor_row(i, a)
        if self.selected is None:
            self.selected = wb.actors[0] if wb.actors else None
        if self.selected is not None:
            self._render_detail()
        self._build_overlap_grid()

    def _add_actor_row(self, row: int, a) -> None:
        card = ctk.CTkFrame(self.list, fg_color=theme.FRAME_2, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=4)
        card.grid_columnconfigure(1, weight=1)
        name = ctk.CTkLabel(card, text=a.name, anchor="w", font=ctk.CTkFont(theme.FONT, theme.FS_H2, "bold"),
                            text_color=theme.TEXT)
        name.grid(row=0, column=0, sticky="w", padx=(12, 6), pady=(9, 0))
        meta = "%s · %s · since %s" % (a.origin, a.motivation, a.first_seen)
        ctk.CTkLabel(card, text=meta, anchor="w", font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                     text_color=theme.TEXT_MUTED).grid(row=1, column=0, columnspan=2, sticky="w",
                                                      padx=12, pady=(0, 2))
        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(bar, text="similarity", width=76, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=0, sticky="w")
        sim = ctk.CTkProgressBar(bar, width=150, height=12, progress_color=theme.GOOD,
                                 fg_color=theme.BG_2, corner_radius=4)
        sim.grid(row=0, column=1, sticky="w", padx=2)
        sim.set(a.score)
        ctk.CTkLabel(bar, text="%.0f%%" % (a.score * 100), width=44,
                     font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.GOOD).grid(row=0, column=2)
        ctk.CTkLabel(bar, text="coverage", width=76, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=3, sticky="w")
        cov = ctk.CTkProgressBar(bar, width=110, height=12, progress_color=theme.ACCENT,
                                 fg_color=theme.BG_2, corner_radius=4)
        cov.grid(row=0, column=4, sticky="w", padx=2)
        cov.set(a.coverage / 100.0)
        ctk.CTkLabel(bar, text="%.0f%%" % a.coverage, width=44,
                     font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.ACCENT_HOVER).grid(row=0, column=5)

        def select(_e=None, act=a):
            self.selected = act
            self._render_detail()

        card.bind("<Button-1>", select)
        for child in card.winfo_children():
            child.bind("<Button-1>", select)

    def _render_detail(self) -> None:
        a = self.selected
        wb = self.app.workbench
        if a is None or self.detail_box is None:
            return
        self.detail_empty.grid_remove()
        self.detail_box.grid()
        for child in self.detail_box.winfo_children():
            child.destroy()

        title = ctk.CTkLabel(self.detail_box, text=a.name, font=ctk.CTkFont(theme.FONT, theme.FS_H1, "bold"),
                             text_color=theme.TEXT, anchor="w")
        title.grid(row=0, column=0, sticky="w", padx=4)
        meta = ctk.CTkLabel(self.detail_box,
                            text="%s%s   |   Since %s   |   %s" % (
                                ("G%s · " % a.actor_id) if a.actor_id else "",
                                a.origin, a.first_seen, a.motivation),
                            font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT_MUTED,
                            anchor="w", wraplength=380, justify="left")
        meta.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))

        if a.aliases:
            aliases = ctk.CTkLabel(self.detail_box,
                                   text="Aliases: " + ", ".join(a.aliases[:6]),
                                   font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.ACCENT_HOVER,
                                   anchor="w", wraplength=400, justify="left")
            aliases.grid(row=2, column=0, sticky="w", padx=4)

        desc = ctk.CTkLabel(self.detail_box, text=a.description, font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                            text_color=theme.TEXT, anchor="w", wraplength=380, justify="left")
        desc.grid(row=3, column=0, sticky="ew", padx=4, pady=(8, 4))

        if a.tools:
            tools = ctk.CTkFrame(self.detail_box, fg_color="transparent")
            tools.grid(row=4, column=0, sticky="ew", padx=4, pady=2)
            ctk.CTkLabel(tools, text="Observed tools: ", font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                         text_color=theme.TEXT).grid(row=0, column=0, sticky="w")
            # Flow chips 3 per row: a single wide row overflows the panel.
            for j, tool in enumerate(a.tools[:6]):
                w.chip(tools, tool).grid(row=1 + j // 3, column=j % 3, padx=2, pady=3, sticky="w")

        msec = ctk.CTkFrame(self.detail_box, fg_color="transparent")
        msec.grid(row=5, column=0, sticky="w", padx=4, pady=(10, 0))
        ctk.CTkLabel(msec, text="Statistically matched techniques (%d/%d observed → coverage %.0f%%)" % (
            len(a.matched_techniques),
            len(wb.actor_db.describe_actor(a.actor_id).get("techniques", {})) if wb.actor_db.describe_actor(
                a.actor_id) else 0,
            a.coverage), font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"), text_color=theme.TEXT,
            wraplength=320, justify="left", anchor="w").grid(
            row=0, column=0, sticky="w")
        match_row = ctk.CTkFrame(self.detail_box, fg_color="transparent")
        match_row.grid(row=6, column=0, sticky="w", padx=4)
        for j, tid in enumerate(sorted(a.matched_techniques)):
            w.chip(match_row, tid).grid(row=j // 5, column=j % 5, padx=2, pady=2)

    def _build_overlap_grid(self) -> None:
        """Full-width actor × technique matrix (top 8 actors, their shared techniques)."""
        for child in self.grid_box.winfo_children():
            child.destroy()
        wb = self.app.workbench
        actors = wb.actors[:8]
        if not actors:
            w.empty_state(self.grid_box, "No actor data yet. Load samples and run analysis.").grid(
                row=0, column=0, padx=10, pady=8)
            return
        # Only techniques matched by at least one shown actor, most-shared first.
        counts = {}
        for a in actors:
            for tid in a.matched_techniques:
                counts[tid] = counts.get(tid, 0) + 1
        techs = sorted(counts, key=lambda tid: (-counts[tid], tid))[:12]
        conf = {t.technique_id: t.confidence for t in wb.techniques.values()}

        inner = ctk.CTkFrame(self.grid_box, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nw", padx=8, pady=4)
        ctk.CTkLabel(inner, text="Actor", width=170, anchor="w",
                     font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=0, padx=4, pady=2)
        for j, tid in enumerate(techs, start=1):
            ctk.CTkLabel(inner, text=tid, width=58, anchor="w",
                         font=ctk.CTkFont(theme.FONT_MONO, theme.FS_TINY),
                         text_color=theme.TEXT_MUTED).grid(row=0, column=j, padx=1, pady=2)
        for i, a in enumerate(actors, start=1):
            ctk.CTkLabel(inner, text=a.name[:24], width=170, anchor="w",
                         font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT).grid(
                row=i, column=0, padx=4, pady=2)
            matched = set(a.matched_techniques)
            for j, tid in enumerate(techs, start=1):
                on = tid in matched
                cell = ctk.CTkLabel(inner, text="•" if on else "", width=26,
                                    fg_color=heat_color(conf.get(tid, 0)) if on else theme.BORDER,
                                    text_color=("#0b1220" if on else theme.BORDER), corner_radius=3)
                cell.grid(row=i, column=j, padx=1, pady=1)