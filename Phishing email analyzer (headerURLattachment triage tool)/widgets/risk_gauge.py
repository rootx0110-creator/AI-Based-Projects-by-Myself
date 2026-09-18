import tkinter as tk

import customtkinter as ctk

from utils.colors import ease_out_cubic, color_lerp


class RiskGauge(ctk.CTkFrame):
    """Animated radial risk gauge rendered on a Canvas."""

    def __init__(self, master, size: int = 240, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.size = size
        self._target = 0.0          # target 0..1
        self._current = 0.0         # animated current value
        self._running = False
        self._target_color = "#2ecc71"
        self._bg_hex = "#0b1220"

        self.canvas = tk.Canvas(
            self, width=size, height=size,
            bg=self._bg_hex, highlightthickness=0,
        )
        self.canvas.pack()
        self.draw(0.0)
        self._animate_loop()

    # ------------------------------------------------------------------ #
    def set_score(self, score: int, color: str):
        self._target = max(0.0, min(1.0, score / 100.0))
        self._target_color = color
        self._current = 0.0
        self._running = True

    def reset(self):
        self._running = False
        self._current = 0.0
        self._target = 0.0
        self.draw(0.0)

    # ------------------------------------------------------------------ #
    def _animate_loop(self):
        if self._running and self._current < self._target:
            self._current = min(self._target, self._current + 0.055)
            self.draw(self._current)
            if self._current >= self._target:
                self._running = False
        self.after(16, self._animate_loop)

    # ------------------------------------------------------------------ #
    def draw(self, t: float):
        t = max(0.0, min(1.0, t))
        c = self.canvas
        c.delete("all")
        size = self.size
        cx = cy = size / 2
        r = size / 2 - 18

        # track ring
        c.create_arc(cx - r, cy - r, cx + r, cy + r,
                     start=0, extent=359.999, style=tk.ARC, width=13,
                     outline=color_lerp(self._bg_hex, "#ffffff", 0.10))

        if t > 0.003:
            angle = 360 * t
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=90 - angle, extent=angle, style=tk.ARC,
                         width=13, outline=self._target_color)

        # inner disc
        inner_r = r - 11
        c.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                      fill=self._bg_hex, outline=color_lerp(self._bg_hex, "#ffffff", 0.05))

        # text
        score = int(t * 100)
        c.create_text(cx, cy - 10, text=f"{score}", fill="#f8fafc",
                      font=("Segoe UI", 34, "bold"))
        c.create_text(cx, cy + 26, text="/ 100", fill="#94a3b8",
                      font=("Segoe UI", 12))