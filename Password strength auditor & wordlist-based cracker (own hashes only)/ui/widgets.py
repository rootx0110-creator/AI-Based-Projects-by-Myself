"""Custom eye-catching UI widgets for VaultGuard."""
from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from core.strength import RULE_COLORS

C = {
    "bg": "#0b0e14",
    "card": "#12161f",
    "card2": "#161b28",
    "border": "#202939",
    "text": "#e8ecf4",
    "muted": "#8a93a7",
    "accent": "#7c5cff",
    "accent2": "#22d3ee",
    "ok": "#2ecc71",
    "warn": "#ffd93d",
    "bad": "#ff5c5c",
}


def gradient_color(start: str, end: str, frac: float) -> str:
    """Interpolate between two hex colors."""
    frac = max(0.0, min(1.0, frac))
    sc = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    ec = [int(end[i : i + 2], 16) for i in (1, 3, 5)]
    rgb = [round(s + (e - s) * frac) for s, e in zip(sc, ec)]
    return "#{:02x}{:02x}{:02x}".format(*rgb)


class Header(ctk.CTkFrame):
    """Gradient header canvas with title text."""

    def __init__(self, master, title: str, subtitle: str, badge: str = "", height: int = 84, **kw):
        super().__init__(master, fg_color="transparent", corner_radius=0, height=height, **kw)
        self._height = height
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        def redraw(event=None):
            w = event.width if event else self.canvas.winfo_width()
            h = self._height
            self.canvas.delete("grad")
            for x in range(0, w, 2):
                frac = x / max(w, 1)
                color = gradient_color("#1c2340", "#0e1220", frac)
                self.canvas.create_rectangle(x, 0, x + 2, h, fill=color, outline="", tags="grad")
            self.canvas.tag_lower("grad")
            self.canvas.delete("text")
            self.canvas.create_text(
                24, h * 0.42, anchor="w", text=title, font=("Segoe UI", 22, "bold"),
                fill="#ffffff", tags="text",
            )
            self.canvas.create_text(
                26, h * 0.76, anchor="w", text=subtitle, font=("Segoe UI", 11),
                fill="#a9b3c6", tags="text",
            )
            if badge:
                self.canvas.create_rectangle(w - 150, 22, w - 24, 58, fill="#241b40",
                                             outline="#7c5cff", width=1, tags="text")
                self.canvas.create_text(
                    w - 87, 40, text=badge, font=("Segoe UI", 12, "bold"),
                    fill="#b7a6ff", tags="text",
                )

        self.canvas.bind("<Configure>", redraw)
        self.canvas.after(20, redraw)


class SectionTitle(ctk.CTkFrame):
    def __init__(self, master, text: str, accent: bool = True, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.pack = self.pack  # silence linters
        bar = ctk.CTkFrame(self, width=4, height=18, corner_radius=2,
                           fg_color=C["accent2"] if accent else C["accent"])
        bar.pack(side="left", padx=(0, 8))
        self.label = ctk.CTkLabel(self, text=text, font=("Segoe UI", 15, "bold"),
                                  text_color=C["text"])
        self.label.pack(side="left")


class StrengthGauge(ctk.CTkFrame):
    """Circular arc gauge showing a password score 0-100."""

    def __init__(self, master, size: int = 230, **kw):
        super().__init__(master, fg_color="transparent", width=size, height=size, **kw)
        self.size = size
        self.score = 0
        self.rating = ""
        self.rating_color = C["muted"]
        self.canvas = tk.Canvas(self, width=size, height=size, bg=C["card"],
                                highlightthickness=0, bd=0)
        self.canvas.pack()

    def _center(self):
        return self.size / 2

    def set(self, score: float, rating: str, color: str):
        self.score = max(0.0, min(100.0, score))
        self.rating = rating
        self.rating_color = color
        self.canvas.delete("all")
        cx = cy = self._center()
        r = self.size / 2 - 16
        track_width = 14

        self.canvas.create_oval(cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                                outline="#1c2334", width=1)

        SEGMENTS = 40
        sweep = 270.0
        start_angle = 135.0
        filled = self.score / 100.0 * sweep
        gap = 1.2
        for i in range(SEGMENTS):
            seg_start = start_angle + sweep * i / SEGMENTS
            seg_extent = sweep / SEGMENTS - gap
            seg_mid = seg_start + seg_extent / 2
            if seg_mid > start_angle + sweep:
                continue
            if seg_start > start_angle + filled:
                color = "#20283a"
            else:
                frac = (seg_mid - start_angle) / sweep
                seg_end_fill = seg_start + seg_extent
                if seg_start <= start_angle + filled:
                    color = gradient_color("#ff4d4d", "#00d2a0", frac)
                else:
                    color = "#20283a"
                if seg_end_fill > start_angle + filled and self.score > 1:
                    color = "#20283a"
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=seg_start, extent=seg_extent, style=tk.ARC,
                width=track_width - 2, outline=color,
            )

        self.canvas.create_text(
            cx, cy - 16, text=f"{self.score:.0f}", font=("Segoe UI", 44, "bold"),
            fill="#ffffff",
        )
        self.canvas.create_text(
            cx, cy + 34, text=self.rating, font=("Segoe UI", 15, "bold"),
            fill=self.rating_color,
        )
        self.canvas.create_text(
            cx, cy + 60, text="STRENGTH SCORE", font=("Segoe UI", 9),
            fill=C["muted"],
        )


class StatCard(ctk.CTkFrame):
    def __init__(self, master, label: str, value: str = "—", sub: str = "", accent: str = C["accent2"], **kw):
        super().__init__(master, fg_color=C["card"], corner_radius=12,
                         border_width=1, border_color=C["border"], **kw)
        self.value_label = ctk.CTkLabel(
            self, text=value, font=("Segoe UI", 20, "bold"), text_color=C["text"],
        )
        self.value_label.pack(pady=(12, 0), padx=14, anchor="w")
        ctk.CTkLabel(
            self, text=label, font=("Segoe UI", 10), text_color=C["muted"],
        ).pack(padx=14, anchor="w")
        if sub:
            ctk.CTkLabel(
                self, text=sub, font=("Segoe UI", 10), text_color=accent,
            ).pack(padx=14, pady=(0, 10), anchor="w")

    def set_value(self, value: str, sub: str = "", accent: str = ""):
        self.value_label.configure(text=value)
        if sub:
            self._sub_configure(sub, accent)

    def _sub_configure(self, sub: str, accent: str):
        pass


class CheckRow(ctk.CTkFrame):
    def __init__(self, master, status: str, text: str, **kw):
        super().__init__(master, fg_color=C["card2"], corner_radius=8, **kw)
        dot_color = RULE_COLORS.get(status, C["muted"])
        self.dot = tk.Canvas(self, width=16, height=16, bg=C["card2"],
                             highlightthickness=0, bd=0)
        self.dot.pack(side="left", padx=(12, 8), pady=8)
        self.dot.create_oval(2, 2, 14, 14, fill=dot_color, outline="")
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}.get(status, "•")
        self.dot.create_text(8, 8, text=mark, fill="#0b0e14", font=("Segoe UI", 8, "bold"))
        self.label = ctk.CTkLabel(
            self, text=text, font=("Segoe UI", 12), text_color=C["text"], anchor="w",
        )
        self.label.pack(side="left", padx=(0, 12), pady=8, fill="x", expand=True)


class StatusDot(ctk.CTkFrame):
    def __init__(self, master, size: int = 10, color: str = C["muted"], **kw):
        super().__init__(master, width=size, height=size, corner_radius=size,
                         fg_color=color, **kw)
        self.pack_propagate(False)

    def set_color(self, color: str):
        self.configure(fg_color=color)


class TimerBar(ctk.CTkProgressBar):
    pass