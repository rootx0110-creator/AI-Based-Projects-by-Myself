"""Reusable UI widgets and thread helpers."""

from __future__ import annotations

import queue
import threading

import customtkinter as ctk

MONO = ("Consolas", 12)


class ResultBox(ctk.CTkTextbox):
    """Read-only monospace output box with colour tag support."""

    COLORS = {
        "info": "#38bdf8",
        "ok": "#4ade80",
        "key": "#f0abfc",
        "warn": "#facc15",
        "bad": "#f87171",
        "dim": "#8b93a5",
        "text": "#d6dbe5",
    }

    def __init__(self, master, **kw):
        kw.setdefault("wrap", "none")
        kw.setdefault("font", ctk.CTkFont(family=MONO[0], size=MONO[1]))
        kw.setdefault("state", "disabled")
        super().__init__(master, **kw)
        self.configure(text_color="#d6dbe5", fg_color="#0f1117",
                       border_color="#263048", border_width=1)
        for name, color in self.COLORS.items():
            self.tag_config(name, foreground=color)

    def write(self, text: str, tag: str | None = None, end: str = "\n") -> None:
        self.configure(state="normal")
        self.insert("end", text + end, (tag,) if tag else ())
        self.configure(state="disabled")
        self.see("end")

    def write_pair(self, label: str, value: str, label_tag: str = "key") -> None:
        self.write(f"{label}: ", label_tag, end="")
        self.write(value, "text", end="\n")

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


class Worker:
    """Run heavy analysis off the UI thread, marshal results back via `done`."""

    def __init__(self, win, fn, done):
        self._q = queue.Queue()
        self._fn = fn
        self._win = win
        self._done = done
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        self._poll()

    def _run(self):
        try:
            result = self._fn()
            self._q.put(("ok", result))
        except Exception as exc:  # noqa: BLE001
            self._q.put(("err", str(exc)))

    def _poll(self):
        try:
            status, payload = self._q.get_nowait()
        except queue.Empty:
            self._win.after(60, self._poll)
            return
        if status == "err":
            self._done(None, payload)
        else:
            self._done(payload, None)


class Toolbar(ctk.CTkFrame):
    """A slim frame containing a title + optional trailing widgets."""

    def __init__(self, master, title: str, subtitle: str = ""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        title_lbl = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold"),
                                 text_color="#e7ebf3", anchor="w")
        title_lbl.grid(row=0, column=0, sticky="w")
        if subtitle:
            sub = ctk.CTkLabel(self, text=subtitle, font=ctk.CTkFont(size=12),
                               text_color="#8b93a5", anchor="w")
            sub.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.trailing = None

    def add_trailing(self, widget, column: int = 1) -> None:
        widget.grid(row=0, column=column, sticky="e", padx=(8, 0), rowspan=2)
        self.trailing = widget


def primary_button(master, text, command):
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="#0ea5a4", hover_color="#0c8f8e",
                         text_color="#04110f", font=ctk.CTkFont(weight="bold"))


def ghost_button(master, text, command):
    return ctk.CTkButton(master, text=text, command=command,
                         fg_color="transparent", hover_color="#1a2130",
                         border_color="#263048", border_width=1, text_color="#a7b6d0")