import customtkinter as ctk
import tkinter.ttk as ttk

from .base import BaseView
from .theme import (PANEL, PANEL2, BORDER, ACCENT, ACCENT2, GOOD, BAD, MUTED,
                    TEXT, font, ACCENT_BTN, WARN)
from .widgets import TreeStyler, SectionCard


class NoteDialog(ctk.CTkToplevel):
    def __init__(self, master, actor, role):
        super().__init__(master)
        self.result = None
        self.title("Append Examiner Note")
        self.geometry("560x360")
        self.resizable(False, False)
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Examiner note (append-only, chained)", font=font(16, "bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="w",
                     padx=22, pady=(20, 4))
        ctk.CTkLabel(self, text=f"Signing as {actor} · {role}", font=font(12),
                     text_color=MUTED, anchor="w").grid(row=1, column=0, sticky="w",
                     padx=22, pady=(0, 10))
        self.text = ctk.CTkTextbox(self, height=140, fg_color=PANEL2, border_color=BORDER,
                                   border_width=1, text_color=TEXT, font=font(13), wrap="word")
        self.text.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 12))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 20))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancel", font=font(13), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=MUTED, height=34,
                      command=self.destroy).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ctk.CTkButton(btns, text="Sign & Append", font=font(13, "bold"), fg_color=ACCENT_BTN,
                      hover_color="#1b7180", height=34, command=self._save).grid(row=0, column=1)

    def _save(self):
        body = self.text.get("1.0", "end").strip()
        if not body:
            return
        self.result = body
        self.destroy()


class CustodyView(BaseView):
    key = "custody"
    title = "Chain of Custody"
    subtitle = "Append-only, tamper-evident evidence handling log (HMAC-chained)"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.add_btn = ctk.CTkButton(self.toolbar, text="✎  Add Note", font=font(13, "bold"),
                                     fg_color=ACCENT_BTN, hover_color="#1b7180", height=34,
                                     command=self._add_note)
        self.append_toolbar(self.add_btn)

        body = self.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        status = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                              border_color=BORDER)
        status.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        status.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(status, text="—", font=font(13, "bold"),
                                         text_color=GOOD, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        self.verify_btn = ctk.CTkButton(status, text="Re-verify Chain Integrity", font=font(12),
                                        fg_color="transparent", border_width=1,
                                        border_color=BORDER, text_color=ACCENT2, height=30,
                                        command=self._verify_chain)
        self.verify_btn.grid(row=0, column=1, sticky="e", padx=16)

        table_card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                                  border_color=BORDER)
        table_card.grid(row=1, column=0, sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_card, columns=("seq", "when", "actor", "action", "hmac"),
                                 show="headings")
        for col, w, anchor in (("seq", 44, "center"), ("when", 158, "w"), ("actor", 140, "w"),
                               ("action", 175, "w"), ("hmac", 150, "w")):
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=w, anchor=anchor)
        TreeStyler.apply(self.tree)
        scb = ctk.CTkScrollbar(table_card, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        scb.grid(row=0, column=1, sticky="ns", pady=4)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_detail())

        detail = ctk.CTkFrame(table_card, fg_color="transparent")
        detail.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 8))
        detail.grid_columnconfigure(1, weight=1)
        self.detail = ctk.CTkLabel(detail, text="Select an entry to inspect its payload and chain link.",
                                   font=font(11.5), text_color=MUTED, anchor="w", justify="left",
                                   wraplength=980)
        self.detail.grid(row=0, column=0, sticky="w", padx=6)

    def refresh(self):
        entries = self.app.store.custody
        self.tree.delete(*self.tree.get_children())
        for e in entries:
            when = e.timestamp.replace("T", " ")
            self.tree.insert("", "end", iid=str(e.seq), values=(e.seq, when, e.actor, e.action, e.hmac[:16] + "…"))
        ok, problems = self.app.store.verify_chain(self.app.secret)
        if not entries:
            self.status_label.configure(text="The chain is empty — activity is signed automatically.",
                                        text_color=MUTED)
        elif ok:
            self.status_label.configure(
                text=f"✓  Chain integrity VERIFIED — all {len(entries)} entries cryptographically intact.",
                text_color=GOOD)
        else:
            self.status_label.configure(
                text=f"⚠  Chain integrity FAILED on {len(problems)} entry(ies) — review immediately.",
                text_color=BAD)

    def _add_note(self):
        s = self.app.store.settings
        dlg = NoteDialog(self.app.root, s.operator, s.role)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        self.app.store.append_custody(s.operator, s.role, "EXAMINER_NOTE", dlg.result,
                                      self.app.secret)
        self.refresh()
        self.app.notify("Note appended and chained to the custody log.", ACCENT)

    def _verify_chain(self):
        ok, problems = self.app.store.verify_chain(self.app.secret)
        self.refresh()
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "CHAIN_VERIFY",
            "Integrity check " + ("passed for all entries" if ok else "FAILED: " + "; ".join(problems[:3])),
            self.app.secret)
        if ok:
            self.app.notify("Chain integrity verified.", GOOD)
        else:
            self.app.notify("Chain integrity check FAILED.", BAD)

    def _show_detail(self):
        sel = self.tree.selection()
        if not sel:
            return
        seq = int(sel[0])
        e = self.app.store.custody[seq - 1] if self.app.store.custody else None
        if not e:
            return
        self.detail.configure(
            text=f"{e.timestamp}  ·  {e.actor} ({e.role})\n"
                 f"ACTION: {e.action}\nQUOTE: {e.detail}\n\n"
                 f"Previous HMAC: {e.prev_hmac}\nThis entry HMAC: {e.hmac}")