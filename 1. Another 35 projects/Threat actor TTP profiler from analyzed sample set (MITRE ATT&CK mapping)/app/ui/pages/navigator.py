"""ATT&CK Navigator page: tactic x technique heatmap grid."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme
from .. import widgets as w
from ...core.tactics import TACTIC_LABELS, TACTIC_ORDER, heat_color


class _Tooltip(ctk.CTkToplevel):
    def __init__(self, anchor, text: str) -> None:
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=theme.BG_2)
        lbl = ctk.CTkLabel(self, text=text, text_color=theme.TEXT, corner_radius=6,
                           fg_color=theme.FRAME_2, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                           wraplength=340, justify="left")
        lbl.grid(padx=6, pady=6)
        self.update_idletasks()
        x = anchor.winfo_pointerx() + 12
        y = anchor.winfo_pointery() + 12
        self.geometry("+%d+%d" % (x, y))


class NavigatorPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.tooltip = None
        

    def _build(self) -> None:
        self.content = ctk.CTkFrame(self.frame, fg_color=theme.BG)
        self.content.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(2, weight=1)

        w.header(self.content, "ATT&CK Navigator",
                 "Coverage heatmap by tactic (colors reflect detection confidence)").grid(
            row=0, column=0, sticky="ew", pady=(0, 8))

        legend = ctk.CTkFrame(self.content, fg_color=theme.FRAME, corner_radius=8)
        legend.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(legend, text="Confidence:", font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=0, padx=(12, 4))
        legend.grid_columnconfigure(7, weight=1)
        ctk.CTkLabel(legend, text="hover a technique chip for evidence",
                     font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.TEXT_MUTED).grid(
            row=0, column=8, padx=8)
        for i, val in enumerate(["0", "20", "40", "60", "80", "100"]):
            c = heat_color(int(val))
            ctk.CTkLabel(legend, text="  ", width=30, fg_color=c, corner_radius=3,
                         text_color=c).grid(row=0, column=i + 1, padx=2, pady=4)
            ctk.CTkLabel(legend, text=val, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                         text_color=theme.TEXT_MUTED).grid(row=1, column=i + 1, padx=2)

        self.scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew")

    def on_show(self) -> None:
        self.refresh()

    def _hide_tooltip(self):
        if self.tooltip is not None:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None

    def _show_tooltip(self, anchor, text: str):
        self._hide_tooltip()
        self.tooltip = _Tooltip(anchor, text)

    def refresh(self) -> None:
        self._hide_tooltip()
        for child in self.scroll.winfo_children():
            child.destroy()
        wb = self.app.workbench

        by_tactic: dict = {}
        for t in wb.techniques.values():
            for tac in (t.tactics or ["unknown"]):
                by_tactic.setdefault(tac, []).append(t)

        order = [t for t in TACTIC_ORDER if t in by_tactic] + sorted(
            t for t in by_tactic if t not in TACTIC_ORDER)

        if not order:
            lbl = w.empty_state(self.scroll,
                                "No techniques to display.\nLoad samples and run analysis to populate "
                                "the ATT&CK Navigator matrix.")
            lbl.grid(row=0, column=0, padx=10, pady=30)
            return

        for i, tac in enumerate(order):
            label = TACTIC_LABELS.get(tac, tac)
            box = ctk.CTkFrame(self.scroll, fg_color=theme.FRAME_2, corner_radius=8)
            box.grid(row=i, column=0, sticky="ew", padx=2, pady=4)
            box.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(box, text="%s  ·  %d technique(s)" % (label, len(by_tactic[tac])),
                         font=ctk.CTkFont(theme.FONT, theme.FS_H2, "bold"),
                         text_color=theme.TEXT, anchor="w").grid(
                row=0, column=0, sticky="w", padx=12, pady=(10, 2))
            chips = ctk.CTkFrame(box, fg_color="transparent")
            chips.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
            col = count = 0
            for t in sorted(by_tactic[tac], key=lambda x: -x.confidence):
                c = heat_color(t.confidence)
                chip = ctk.CTkLabel(chips, text="  %s  %.0f%%  " % (t.technique_id, t.confidence),
                                    fg_color=c, text_color="#0b1220", corner_radius=5,
                                    font=ctk.CTkFont(theme.FONT_MONO, theme.FS_SMALL, "bold"))
                chip.grid(row=col, column=count % 3, padx=4, pady=4, sticky="w")
                tip = "%s\n%s%% confidence\n\n%s" % (
                    t.name, t.confidence, "\n".join(t.evidence[:5]))
                chip.bind("<Enter>", lambda _e, a=chip, tx=tip: self._show_tooltip(a, tx))
                chip.bind("<Leave>", lambda _e: self._hide_tooltip())
                count += 1
                if count % 3 == 0:
                    col += 1