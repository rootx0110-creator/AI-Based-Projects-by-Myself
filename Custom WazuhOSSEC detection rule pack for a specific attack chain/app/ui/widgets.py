"""Reusable composite widgets for the studio GUI."""
from __future__ import annotations

import customtkinter as ctk

from . import theme


class Panel(ctk.CTkFrame):
    """A rounded panel used to group content across all views.

    The optional title bar is pack-managed; grid content must be placed in
    ``panel.content`` (a transparent full-size sub-frame) to avoid mixing
    geometry managers.
    """

    def __init__(self, master, title: str | None = None, **kwargs):
        kwargs.setdefault("fg_color", theme.PANEL)
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.LINE)
        super().__init__(master, **kwargs)
        self.heading = None
        if title:
            self.heading = ctk.CTkLabel(
                self, text=title.upper(), text_color=theme.MUTED,
                font=theme.font(11, "bold"), anchor="w")
            self.heading.pack(fill="x", padx=18, pady=(14, 2))
        self.content = ctk.CTkFrame(self, fg_color="transparent",
                                    corner_radius=0)
        self.content.pack(fill="both", expand=True)


class StatCard(Panel):
    """KPI card with big number and label."""

    def __init__(self, master, label: str, value="0",
                 accent: str = theme.ACCENT, sub: str = ""):
        super().__init__(master, corner_radius=14)
        self._label = ctk.CTkLabel(
            self, text=label.upper(), text_color=theme.MUTED,
            font=theme.font(11, "bold"), anchor="w")
        self._label.pack(fill="x", padx=16, pady=(12, 0))
        self._value = ctk.CTkLabel(
            self, text=str(value), text_color=accent,
            font=theme.font(30, "bold"), anchor="w")
        self._value.pack(fill="x", padx=16, pady=(0, 0))
        self._sub = ctk.CTkLabel(
            self, text=sub, text_color=theme.MUTED, font=theme.font(12),
            anchor="w")
        self._sub.pack(fill="x", padx=16, pady=(0, 12))

    def set(self, value, sub: str | None = None) -> None:
        self._value.configure(text=str(value))
        if sub is not None:
            self._sub.configure(text=sub)


class SectionHeader(ctk.CTkLabel):
    def __init__(self, master, text: str):
        super().__init__(master, text=text.upper(), text_color=theme.ACCENT,
                         font=theme.font(12, "bold"), anchor="w")


def make_button(master, text, command, variant: str = "accent", **kw):
    cfg = dict(height=34, corner_radius=8, font=theme.font(12, "bold"),
               border_width=0)
    if variant == "accent":
        cfg.update(fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                   text_color="#ffffff")
    elif variant == "ghost":
        cfg.update(fg_color=theme.PANEL2, hover_color=theme.PANEL3,
                   text_color=theme.FG, border_width=1,
                   border_color=theme.LINE)
    elif variant == "danger":
        cfg.update(fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
                   text_color="#ffffff")
    cfg.update(kw)
    return ctk.CTkButton(master, text=text, command=command, **cfg)