"""Reusable UI building blocks (cards, bars, chips, badges)."""

from __future__ import annotations

import customtkinter as ctk

from . import theme


def header(parent, text: str, sub: str = "") -> ctk.CTkFrame:
    box = ctk.CTkFrame(parent, fg_color="transparent")
    t = ctk.CTkLabel(box, text=text, font=ctk.CTkFont(theme.FONT, theme.FS_H1, "bold"), text_color=theme.TEXT, anchor="w")
    t.grid(row=0, column=0, padx=4, pady=(2, 0), sticky="w")
    if sub:
        s = ctk.CTkLabel(box, text=sub, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT_MUTED, anchor="w")
        s.grid(row=1, column=0, padx=4, pady=(0, 8), sticky="w")
    box.grid_columnconfigure(0, weight=1)
    return box


def card(parent, title: str = "", height: int | None = None, **grid):
    frame = ctk.CTkFrame(parent, fg_color=theme.FRAME, border_width=1, border_color=theme.BORDER,
                         corner_radius=12)
    frame.grid_columnconfigure(0, weight=1)
    if title:
        lbl = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(theme.FONT, theme.FS_H2, "bold"),
                           text_color=theme.TEXT, anchor="w")
        lbl.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
    body.grid_columnconfigure(0, weight=1)
    frame.configure(height=height) if height else None
    frame.grid(**grid, sticky="nsew")
    frame.body = body
    return frame


def kpi(parent, value: str, label: str, color: str = theme.ACCENT):
    box = ctk.CTkFrame(parent, fg_color=theme.FRAME_2, corner_radius=10)
    v = ctk.CTkLabel(box, text=value, font=ctk.CTkFont(theme.FONT, theme.FS_KPI, "bold"), text_color=color)
    v.grid(row=0, column=0, padx=16, pady=(16, 0))
    l = ctk.CTkLabel(box, text=label, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT_MUTED)
    l.grid(row=1, column=0, padx=16, pady=(0, 14))
    return box


def progress_bar(parent, value: float, width: int = 130, height: int = 12,
                 color: str = theme.ACCENT, max_value: float = 100) -> ctk.CTkProgressBar:
    bar = ctk.CTkProgressBar(parent, width=width, height=height, progress_color=color,
                             fg_color=theme.BG_2, corner_radius=4)
    bar.set(max(0.0, min(1.0, value / max_value if max_value else 0)))
    return bar



def chip(parent, text: str, active: bool = True, bg=None):
    c = bg or (theme.ACCENT if active else theme.FRAME_2)
    fg = "#ffffff" if active else theme.TEXT_MUTED
    lbl = ctk.CTkLabel(parent, text=text, fg_color=c, text_color=fg, corner_radius=6,
                       font=ctk.CTkFont(theme.FONT_MONO if text.startswith("T") else theme.FONT,
                                        theme.FS_MONO_SM if text.startswith("T") else theme.FS_SMALL))
    return lbl


def conf_bar(parent, conf: float, label: str = "", height: int = 14, width: int = 120):
    color = theme.GOOD if conf >= 70 else (theme.WARN if conf >= 40 else theme.BAD)
    bar = ctk.CTkProgressBar(parent, width=width, height=height, progress_color=color,
                             fg_color=theme.BG_2, corner_radius=4)
    bar.set(conf / 100.0)
    lbl = ctk.CTkLabel(parent, text=label or "%.0f%%" % conf,
                       font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT_MUTED)
    return bar, lbl


def empty_state(parent, text: str) -> ctk.CTkLabel:
    lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                       text_color=theme.TEXT_MUTED, wraplength=520, justify="center")
    return lbl


def section_title(parent, text: str) -> ctk.CTkLabel:
    lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(theme.FONT, theme.FS_H2, "bold"),
                       text_color=theme.TEXT)
    return lbl