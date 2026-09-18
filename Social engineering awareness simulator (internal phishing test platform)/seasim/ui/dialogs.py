"""Reusable modal dialogs for SeaSim."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional

from seasim import constants as C
from seasim.engine.models import (
    DEPARTMENTS, LOCATIONS, EmailTemplate,
    CATEGORY_AI, CATEGORY_CLASSIC, DIFFICULTY_LEVELS, TECHNIQUES,
)
from seasim.ui import theme as T


class DialogBase(tk.Toplevel):
    """Modal dialog scaffold with header + footer buttons."""

    def __init__(self, master, title: str, w: int, h: int) -> None:
        super().__init__(master)
        self.title(title)
        self.configure(bg=T.BG)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2)}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.header = tk.Frame(self, bg=T.INK)
        self.header.pack(fill="x")
        tk.Label(self.header, text=title, fg="white", bg=T.INK,
                 font=(T.FONT, 13, "bold")).pack(anchor="w", padx=20,
                                                 pady=14)
        self.body = tk.Frame(self, bg=T.BG)
        self.body.pack(fill="both", expand=True)
        self.footer = tk.Frame(self, bg=T.BG)
        self.footer.pack(fill="x", side="bottom", pady=14, padx=20)

    def add_footer_button(self, text: str, cmd: Callable[[], None],
                          style: str = "TButton", side: str = "right") -> None:
        ttk.Button(self.footer, text=text, command=cmd,
                   style=style).pack(side=side, padx=(0, 8) if side == "right"
                                     else (8, 0))


def info(master, title: str, msg: str) -> None:
    messagebox.showinfo(title, msg, parent=master)


def warn(master, title: str, msg: str) -> None:
    messagebox.showwarning(title, msg, parent=master)


def error(master, title: str, msg: str) -> None:
    messagebox.showerror(title, msg, parent=master)


def confirm(master, title: str, msg: str) -> bool:
    return messagebox.askyesno(title, msg, parent=master)


def confirm_cancel(master, title: str, msg: str) -> bool:
    return messagebox.askyesnocancel(title, msg, parent=master)


def show_text(master, title: str, text: str, mono: bool = False) -> None:
    """Scrollable read-only text viewer dialog."""
    dlg = DialogBase(master, title, 720, 560)
    txt = tk.Text(dlg.body, wrap="word" if not mono else "none",
                  font=(T.MONO, 10) if mono else (T.FONT, 10),
                  bg=T.CARD, fg=T.INK, relief="flat", padx=16, pady=14)
    txt.insert("1.0", text)
    txt.configure(state="disabled")
    txt.pack(fill="both", expand=True)
    sb = ttk.Scrollbar(dlg.body, orient="vertical", command=txt.yview)
    txt.configure(yscrollcommand=sb.set)
    sb.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
    dlg.add_footer_button("Close", dlg.destroy)
    dlg.wait_window()


def prompt_string(master, title: str, label: str, initial: str = "") \
        -> Optional[str]:
    dlg = DialogBase(master, title, 460, 190)
    tk.Label(dlg.body, text=label, bg=T.BG, fg=T.INK,
             font=(T.FONT, 10)).pack(anchor="w", padx=20, pady=(16, 6))
    ent = tk.Entry(dlg.body, font=(T.FONT, 11), bg="white")
    ent.pack(fill="x", padx=20)
    if initial:
        ent.insert(0, initial)
    result: List[Optional[str]] = [None]

    def ok() -> None:
        result[0] = ent.get().strip()
        dlg.destroy()

    ent.bind("<Return>", lambda e: ok())
    dlg.add_footer_button("OK", ok, "Accent.TButton")
    dlg.add_footer_button("Cancel", dlg.destroy, side="left")
    ent.focus_set()
    dlg.wait_window()
    return result[0]


class ParticipantDialog(DialogBase):
    """Add / edit a participant."""

    def __init__(self, master, on_save: Callable[[dict], None],
                 participant=None) -> None:
        super().__init__(master, "Edit participant" if participant
                         else "Add participant", 500, 430)
        self.on_save = on_save
        p = participant
        form = tk.Frame(self.body, bg=T.BG)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        def row(r: int, label: str) -> tk.Entry:
            tk.Label(form, text=label, bg=T.BG, fg=T.INK,
                     font=(T.FONT, 10, "bold")).grid(row=r, column=0,
                                                     sticky="w", pady=6)
            e = tk.Entry(form, font=(T.FONT, 11), bg="white", width=32)
            e.grid(row=r, column=1, sticky="ew", pady=6, padx=(10, 0))
            return e

        form.columnconfigure(1, weight=1)
        self.e_name = row(0, "Full name")
        self.e_email = row(1, "Email (internal)")
        self.e_note = row(4, "Note (optional)")

        tk.Label(form, text="Department", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 10, "bold")).grid(row=2, column=0, sticky="w",
                                                 pady=6)
        self.cb_dept = ttk.Combobox(form, values=DEPARTMENTS,
                                    state="readonly", font=(T.FONT, 10))
        self.cb_dept.grid(row=2, column=1, sticky="ew", pady=6, padx=(10, 0))
        self.cb_dept.set(DEPARTMENTS[4])

        tk.Label(form, text="Location", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 10, "bold")).grid(row=3, column=0, sticky="w",
                                                 pady=6)
        self.cb_loc = ttk.Combobox(form, values=LOCATIONS, state="readonly",
                                   font=(T.FONT, 10))
        self.cb_loc.grid(row=3, column=1, sticky="ew", pady=6, padx=(10, 0))
        self.cb_loc.set(LOCATIONS[0])

        self.v_active = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Active (eligible for campaigns)",
                        variable=self.v_active).grid(row=5, column=0,
                                                     columnspan=2, sticky="w",
                                                     pady=(10, 0))

        if p is not None:
            self.e_name.insert(0, p.name)
            self.e_email.insert(0, p.email)
            self.e_note.insert(0, p.note)
            self.cb_dept.set(p.department)
            self.cb_loc.set(p.location)
            self.v_active.set(p.active)

        self.add_footer_button("Save", self._save, "Accent.TButton")
        self.add_footer_button("Cancel", self.destroy, side="left")
        self.wait_window()

    def _save(self) -> None:
        name = self.e_name.get().strip()
        email = self.e_email.get().strip().lower()
        if not name:
            warn(self, "SeaSim", "Name is required.")
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            warn(self, "SeaSim", "Enter a valid internal email address.")
            return
        self.on_save({
            "name": name, "email": email,
            "department": self.cb_dept.get(), "location": self.cb_loc.get(),
            "note": self.e_note.get().strip(),
            "active": self.v_active.get(),
        })
        self.destroy()


class TemplateEditorDialog(DialogBase):
    """Create / edit a custom awareness template."""

    def __init__(self, master, on_save: Callable[[EmailTemplate], None],
                 template: Optional[EmailTemplate] = None) -> None:
        super().__init__(master, "Edit template" if template
                         else "New template", 760, 640)
        self.on_save = on_save
        t = template

        top = tk.Frame(self.body, bg=T.BG)
        top.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(top, text="Name", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 10, "bold")).pack(anchor="w")
        self.e_name = tk.Entry(top, font=(T.FONT, 11), bg="white")
        self.e_name.pack(fill="x", pady=(2, 8))

        grid = tk.Frame(self.body, bg=T.BG)
        grid.pack(fill="x", padx=20)
        tk.Label(grid, text="Category", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 9, "bold")).grid(row=0, column=0, sticky="w")
        self.cb_cat = ttk.Combobox(grid, values=[CATEGORY_CLASSIC, CATEGORY_AI,
                                                 "Custom"], state="readonly",
                                   font=(T.FONT, 10), width=16)
        self.cb_cat.current(0)
        self.cb_cat.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        tk.Label(grid, text="Difficulty", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 9, "bold")).grid(row=0, column=1, sticky="w")
        self.cb_diff = ttk.Combobox(grid, values=DIFFICULTY_LEVELS,
                                    state="readonly", font=(T.FONT, 10),
                                    width=16)
        self.cb_diff.current(1)
        self.cb_diff.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        tk.Label(grid, text="Link label", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 9, "bold")).grid(row=0, column=2, sticky="w")
        self.e_link = tk.Entry(grid, font=(T.FONT, 10), width=16, bg="white")
        self.e_link.insert(0, "Open")
        self.e_link.grid(row=1, column=2, sticky="ew")
        grid.columnconfigure((0, 1, 2), weight=1)

        tk.Label(self.body, text="Techniques (comma separated)",
                 bg=T.BG, fg=T.INK, font=(T.FONT, 9, "bold")).pack(
            anchor="w", padx=20, pady=(10, 2))
        self.e_tech = tk.Entry(self.body, font=(T.FONT, 10), bg="white")
        self.e_tech.insert(0, ", ".join(TECHNIQUES[:2]))
        self.e_tech.pack(fill="x", padx=20)

        tk.Label(self.body, text="Subject", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 9, "bold")).pack(anchor="w", padx=20,
                                                pady=(10, 2))
        self.e_subject = tk.Entry(self.body, font=(T.FONT, 10), bg="white")
        self.e_subject.pack(fill="x", padx=20)

        mid = tk.Frame(self.body, bg=T.BG)
        mid.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(1, weight=1)

        tk.Label(mid, text="Body ({first_name}, {org}, {link} placeholders)",
                 bg=T.BG, fg=T.INK, font=(T.FONT, 9, "bold")).grid(
            row=0, column=0, sticky="w")
        self.txt_body = tk.Text(mid, height=10, font=(T.FONT, 10), bg="white",
                                relief="flat", padx=10, pady=8)
        self.txt_body.grid(row=1, column=0, sticky="nsew", pady=(2, 0),
                           padx=(0, 6))

        tk.Label(mid, text="Phishing indicators (one per line)",
                 bg=T.BG, fg=T.INK, font=(T.FONT, 9, "bold")).grid(
            row=0, column=1, sticky="w")
        self.txt_ind = tk.Text(mid, height=10, font=(T.FONT, 10), bg="white",
                               relief="flat", padx=10, pady=8)
        self.txt_ind.grid(row=1, column=1, sticky="nsew", pady=(2, 0),
                          padx=(6, 0))

        if t is not None:
            self.e_name.insert(0, t.name)
            self.cb_cat.set(t.category)
            self.cb_diff.set(t.difficulty)
            self.e_link.delete(0, "end")
            self.e_link.insert(0, t.link_label)
            self.e_tech.delete(0, "end")
            self.e_tech.insert(0, ", ".join(t.techniques))
            self.e_subject.insert(0, t.subject)
            self.txt_body.insert("1.0", t.body)
            self.txt_ind.insert("1.0", "\n".join(t.phishing_indicators))

        self.add_footer_button("Save template", self._save, "Accent.TButton")
        self.add_footer_button("Cancel", self.destroy, side="left")
        self.wait_window()

    def _save(self) -> None:
        name = self.e_name.get().strip()
        subject = self.e_subject.get().strip()
        body = self.txt_body.get("1.0", "end").strip()
        if not name or not subject or "{link}" not in body:
            warn(self, "SeaSim",
                 "Name, subject and a body containing {link} are required.")
            return
        tpl = EmailTemplate.create(
            name=name,
            category=self.cb_cat.get(),
            difficulty=self.cb_diff.get(),
            techniques=[s.strip() for s in self.e_tech.get().split(",")
                        if s.strip()],
            subject=subject, body=body,
            link_label=self.e_link.get().strip() or "Open",
            indicators=[ln.strip() for ln in
                        self.txt_ind.get("1.0", "end").splitlines()
                        if ln.strip()],
        )
        self.on_save(tpl)
        self.destroy()
