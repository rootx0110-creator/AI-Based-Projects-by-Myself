"""MITRE ATT&CK page: detected techniques grouped by tactic."""

from __future__ import annotations

import customtkinter as ctk

from .. import theme
from .. import widgets as w
from ...core.tactics import TACTIC_LABELS, TACTIC_ORDER


class AttackPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.selected = None
        

    def _build(self) -> None:
        self.content = ctk.CTkFrame(self.frame, fg_color=theme.BG)
        self.content.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        w.header(top, "MITRE ATT&CK Techniques", "Detected techniques with evidence and confidence").grid(
            row=0, column=0, sticky="w")
        self.kpi_frame = ctk.CTkFrame(top, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=1, sticky="e")

        controls = ctk.CTkFrame(self.content, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", pady=(6, 6))
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(controls, text="Min confidence to display:", font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.min_conf = ctk.CTkOptionMenu(controls, values=["0", "20", "35", "50", "65", "80"],
                                          width=84, height=30, corner_radius=6,
                                          font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), fg_color=theme.FRAME_2,
                                          button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER)
        self.min_conf.set("0")
        self.min_conf.grid(row=0, column=1, sticky="w")
        self.min_conf.configure(command=lambda _v: self.refresh())

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        list_card = w.card(body, "Techniques by Tactic", row=0, column=0)
        list_card.grid_rowconfigure(0, weight=1)
        self.list = ctk.CTkScrollableFrame(list_card.body, fg_color="transparent")
        self.list.grid(row=0, column=0, sticky="nsew")

        detail = w.card(body, "Technique Detail", row=0, column=1)
        detail.grid_rowconfigure(1, weight=1)
        self.detail_empty = w.empty_state(detail, "Select a technique to view evidence.")
        self.detail_empty.grid(row=1, column=0, padx=10, pady=10)
        self.detail_box = ctk.CTkFrame(detail, fg_color="transparent")
        self.detail_box.grid(row=1, column=0, sticky="nsew")
        self.detail_box.grid_remove()

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        for child in self.kpi_frame.winfo_children():
            child.destroy()
        wb = self.app.workbench
        n = len(wb.techniques)
        tactics = set()
        for t in wb.techniques.values():
            tactics.update(t.tactics)
        k = w.kpi(self.kpi_frame, str(n), "Techniques", theme.ACCENT)
        k.grid(row=0, column=0, padx=4)
        k = w.kpi(self.kpi_frame, str(len(tactics)), "Tactics", theme.GOOD)
        k.grid(row=0, column=1, padx=4)

        self._rebuild_list()
        self._render_detail()

    # ------------------------------------------------------------------
    def _rebuild_list(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()
        wb = self.app.workbench
        try:
            min_conf = float(self.min_conf.get())
        except ValueError:
            min_conf = 0

        by_tactic: dict = {}
        for t in wb.techniques.values():
            if t.confidence < min_conf:
                continue
            for tac in (t.tactics or ["unknown"]):
                by_tactic.setdefault(tac, []).append(t)

        order = [t for t in TACTIC_ORDER if t in by_tactic] + sorted(
            t for t in by_tactic if t not in TACTIC_ORDER)

        if not order:
            lbl = w.empty_state(self.list,
                                "No techniques to display.\nLoad samples and run analysis first.")
            lbl.grid(row=0, column=0, padx=10, pady=10)
            return

        row = 0
        for tac in order:
            label = TACTIC_LABELS.get(tac, tac)
            head = ctk.CTkLabel(self.list, text="%s  (%d)" % (label, len(by_tactic[tac])),
                                font=ctk.CTkFont(theme.FONT, theme.FS_H2, "bold"),
                                text_color=theme.ACCENT_HOVER, anchor="w")
            head.grid(row=row, column=0, sticky="ew", padx=6, pady=(10, 3))
            row += 1
            for t in sorted(by_tactic[tac], key=lambda x: -x.confidence):
                self._add_technique_row(row, t)
                row += 1

    def _add_technique_row(self, row: int, t) -> None:
        card = ctk.CTkFrame(self.list, fg_color=theme.FRAME_2, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=3)
        card.grid_columnconfigure(2, weight=1)
        tid = ctk.CTkLabel(card, text=t.technique_id, width=92,
                           font=ctk.CTkFont(theme.FONT_MONO, theme.FS_BODY, "bold"), text_color=theme.ACCENT_HOVER)
        tid.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="n")
        name = ctk.CTkLabel(card, text=t.name, anchor="w", font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                            text_color=theme.TEXT, justify="left")
        name.grid(row=0, column=1, sticky="ew")
        bar, lbl = w.conf_bar(card, t.confidence, height=14, width=120)
        bar.grid(row=0, column=3, padx=8, sticky="e")
        lbl.grid(row=0, column=4, padx=(0, 10))
        n_ev = ctk.CTkLabel(card, text="%d evidence item(s)" % len(t.evidence),
                            font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.TEXT_MUTED)
        n_ev.grid(row=1, column=1, sticky="w", padx=6, pady=(0, 8))

        def select(_e=None, tt=t):
            self.selected = tt
            self._render_detail()

        card.bind("<Button-1>", select)
        for ch in (tid, name, bar, lbl, n_ev):
            ch.bind("<Button-1>", select)

    # ------------------------------------------------------------------
    def _render_detail(self) -> None:
        t = self.selected
        if t is None:
            return
        self.detail_empty.grid_remove()
        self.detail_box.grid()
        for child in self.detail_box.winfo_children():
            child.destroy()

        rows = [
            ("ID", t.technique_id),
            ("Name", t.name),
            ("Tactics", ", ".join(TACTIC_LABELS.get(x, x) for x in t.tactics)),
            ("Confidence", "%.1f%%" % t.confidence),
            ("Weight", "%.2f" % t.weight),
        ]
        for i, (k, v) in enumerate(rows):
            ctk.CTkLabel(self.detail_box, text=k + ":", width=110, anchor="w",
                         font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                         text_color=theme.TEXT).grid(row=i, column=0, sticky="nw", padx=(4, 10), pady=2)
            ctk.CTkLabel(self.detail_box, text=v, anchor="w", justify="left",
                         wraplength=380, font=ctk.CTkFont(theme.FONT_MONO, theme.FS_MONO_SM),
                         text_color=theme.TEXT).grid(row=i, column=1, sticky="w", pady=2)

        sep = ctk.CTkFrame(self.detail_box, height=1, fg_color=theme.BORDER)
        sep.grid(row=len(rows), column=0, columnspan=2, sticky="ew", pady=8)

        ev_title = ctk.CTkLabel(self.detail_box, text="Supporting evidence",
                                font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                                text_color=theme.TEXT, anchor="w")
        ev_title.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", padx=4)
        ev_box = ctk.CTkScrollableFrame(self.detail_box, fg_color=theme.BG_2, height=180,
                                        corner_radius=8)
        ev_box.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="nsew", pady=(4, 0))
        for i, e in enumerate(t.evidence, start=1):
            ctk.CTkLabel(ev_box, text="%02d  %s" % (i, e), anchor="w", justify="left",
                         wraplength=360, font=ctk.CTkFont(theme.FONT_MONO, theme.FS_MONO_SM),
                         text_color=theme.TEXT).grid(row=i, column=0, sticky="w", padx=6, pady=3)