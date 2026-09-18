import customtkinter as ctk
import tkinter.ttk as ttk

from ..core.models import Case, format_bytes
from .base import BaseView
from .theme import (PANEL2, PANEL, BORDER, ACCENT, ACCENT2, GOOD, BAD, MUTED,
                    TEXT, font, ACCENT_BTN)
from .widgets import TreeStyler, SectionCard


class CaseDialog(ctk.CTkToplevel):
    def __init__(self, master, case=None):
        super().__init__(master)
        self.result = None
        self.case = case
        self.title("Edit Case" if case else "New Case")
        self.geometry("600x560")
        self.resizable(False, False)
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        pad = 22

        ctk.CTkLabel(self, text="Case Details", font=font(17, "bold"), text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w", padx=pad, pady=(18, 10))

        def field(row, label):
            ctk.CTkLabel(self, text=label, font=font(12), text_color=MUTED,
                         anchor="w").grid(row=row, column=0, sticky="w", padx=pad, pady=(4, 1))
            e = ctk.CTkEntry(self, fg_color=PANEL2, border_color=BORDER,
                             text_color=TEXT, font=font(13))
            e.grid(row=row + 1, column=0, sticky="ew", padx=pad, pady=(0, 6))
            return e

        self.case_no = field(1, "Case number *")
        self.title_e = field(3, "Case title *")
        self.agency = field(5, "Agency / department")
        self.inv = field(7, "Investigator")
        self.role = field(9, "Role / title")

        ctk.CTkLabel(self, text="Description", font=font(12), text_color=MUTED,
                     anchor="w").grid(row=11, column=0, sticky="w", padx=pad, pady=(4, 1))
        self.desc = ctk.CTkTextbox(self, height=64, fg_color=PANEL2, border_color=BORDER,
                                   border_width=1, text_color=TEXT, font=font(13))
        self.desc.grid(row=12, column=0, sticky="ew", padx=pad, pady=(0, 8))

        ctk.CTkLabel(self, text="Status", font=font(12), text_color=MUTED,
                     anchor="w").grid(row=13, column=0, sticky="w", padx=pad)
        self.status = ctk.CTkOptionMenu(self, values=["Open", "Closed"], fg_color=PANEL2,
                                        button_color=ACCENT_BTN, button_hover_color="#1b7180",
                                        text_color=TEXT, font=font(13), width=160)
        self.status.grid(row=14, column=0, sticky="w", padx=pad, pady=(2, 8))

        self.hint = ctk.CTkLabel(self, text="", font=font(11), text_color="#ef4444", anchor="w")
        self.hint.grid(row=15, column=0, sticky="w", padx=pad)

        if case:
            self.case_no.insert(0, case.case_number)
            self.title_e.insert(0, case.title)
            self.agency.insert(0, case.agency)
            self.inv.insert(0, case.investigator)
            self.role.insert(0, case.role)
            self.desc.insert("1.0", case.description)
            self.status.set(case.status)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=16, column=0, sticky="ew", padx=pad, pady=(8, 18))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancel", font=font(13), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=MUTED, height=36,
                      command=self.destroy).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ctk.CTkButton(btns, text="Save Case", font=font(13, "bold"), fg_color=ACCENT_BTN,
                      hover_color="#1b7180", height=36, command=self._save).grid(row=0, column=1)

    def _save(self):
        num = self.case_no.get().strip()
        ti = self.title_e.get().strip()
        if not num or not ti:
            self.hint.configure(text="Case number and title are required.")
            return
        self.result = {
            "case_number": num, "title": ti,
            "agency": self.agency.get().strip(),
            "investigator": self.inv.get().strip(),
            "role": self.role.get().strip(),
            "description": self.desc.get("1.0", "end").strip(),
            "status": self.status.get(),
        }
        self.destroy()


class CasesView(BaseView):
    key = "cases"
    title = "Cases & Evidence"
    subtitle = "Manage forensic cases and their registered evidence items"

    def __init__(self, master, app):
        super().__init__(master, app)

        self.add_btn = ctk.CTkButton(self.toolbar, text="+ New Case", font=font(13, "bold"),
                                     fg_color=ACCENT_BTN, hover_color="#1b7180", height=34,
                                     command=self._new_case)
        self.append_toolbar(self.add_btn)

        body = self.body
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Cases", font=font(15, "bold"), text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.case_tree = ttk.Treeview(left, columns=("caseno", "title", "status", "ev"),
                                      show="headings", selectmode="browse")
        self.case_tree.heading("caseno", text="Case No.")
        self.case_tree.column("caseno", width=110, anchor="w")
        self.case_tree.heading("title", text="Title")
        self.case_tree.column("title", width=160, anchor="w")
        self.case_tree.heading("status", text="Status")
        self.case_tree.column("status", width=56, anchor="center")
        self.case_tree.heading("ev", text="#")
        self.case_tree.column("ev", width=30, anchor="center")
        TreeStyler.apply(self.case_tree)
        scb = ctk.CTkScrollbar(left, command=self.case_tree.yview)
        self.case_tree.configure(yscrollcommand=scb.set)
        self.case_tree.grid(row=1, column=0, sticky="nsew")
        scb.grid(row=1, column=1, sticky="ns")
        self.case_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_case_select())

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ctk.CTkButton(btns, text="Edit", font=font(12), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=ACCENT2, height=32,
                      command=self._edit_case).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btns, text="Delete", font=font(12), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=BAD, height=32,
                      command=self._delete_case).pack(side="left")
        ctk.CTkButton(btns, text="Open Prosecutor View", font=font(12), fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=GOOD, height=32,
                      command=self._open_case).pack(side="right")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.detail_card = SectionCard(right, "Selected Case")
        self.detail_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.detail_text = ctk.CTkLabel(self.detail_card.body, text="Select a case to inspect.",
                                        font=font(12.5), text_color=MUTED, anchor="w",
                                        justify="left", wraplength=560)
        self.detail_text.grid(row=0, column=0, sticky="w")

        self.ev_header = ctk.CTkFrame(right, fg_color="transparent")
        self.ev_header.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.ev_header.grid_columnconfigure(0, weight=1)
        self.ev_label = ctk.CTkLabel(self.ev_header, text="Evidence (0)",
                                     font=font(15, "bold"), text_color=TEXT, anchor="w")
        self.ev_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(self.ev_header, text="Register evidence", font=font(12),
                      fg_color="transparent", border_width=1, border_color=BORDER,
                      text_color=ACCENT2, height=30, command=self._register_evidence
                      ).grid(row=0, column=1, sticky="e")

        self.ev_tree = ttk.Treeview(right, columns=("type", "size", "hash", "status"),
                                    show="headings", selectmode="browse")
        for col, w, anchor in (("type", 150, "w"), ("size", 90, "center"),
                               ("hash", 150, "w"), ("status", 90, "center")):
            self.ev_tree.heading(col, text=col.title() if col != "hash" else "SHA-256")
            self.ev_tree.column(col, width=w, anchor=anchor)
        TreeStyler.apply(self.ev_tree)
        ev_scb = ctk.CTkScrollbar(right, command=self.ev_tree.yview)
        self.ev_tree.configure(yscrollcommand=ev_scb.set)
        self.ev_tree.grid(row=2, column=0, sticky="nsew")
        ev_scb.grid(row=2, column=1, sticky="ns")

        self._sel_case_id = ""

    # ---------- actions ----------
    def _selected_case(self):
        sel = self.case_tree.selection()
        if not sel:
            return None
        return self.app.store.get_case(sel[0])

    def _new_case(self):
        dlg = CaseDialog(self.app.root)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        case = Case.new(**dlg.result)
        self.app.store.add_case(case)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "CASE_CREATED", f"Case {case.case_number} — {case.title}", self.app.secret)
        self.app.refresh_case_combo()
        self._refresh_cases(select=case.id)
        self.app.notify(f"Case {case.case_number} created.")

    def _edit_case(self):
        case = self._selected_case()
        if not case:
            self.app.notify("Select a case first.", BAD)
            return
        dlg = CaseDialog(self.app.root, case)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        for k, v in dlg.result.items():
            setattr(case, k, v)
        self.app.store.update_case(case)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "CASE_EDITED", f"Case {case.case_number} updated", self.app.secret)
        self.app.refresh_case_combo()
        self._refresh_cases(select=case.id)
        self.app.notify("Case updated.")

    def _delete_case(self):
        case = self._selected_case()
        if not case:
            self.app.notify("Select a case first.", BAD)
            return
        self.app.store.delete_case(case.id)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "CASE_DELETED", f"Case {case.case_number} removed from registry", self.app.secret)
        if self.app.active_case_id == case.id:
            self.app.active_case_id = ""
        self.app.refresh_case_combo()
        self._refresh_cases()
        self.app.notify("Case deleted.", ACCENT2)

    def _open_case(self):
        case = self._selected_case()
        if case:
            self.app._on_case_selected(case.display)
            self.app.notify(f"Active case set to {case.case_number}.")

    def _register_evidence(self):
        case = self._selected_case()
        if not case:
            self.app.notify("Select a case first.", BAD)
            return
        from .evidence_dialog import EvidenceDialog
        dlg = EvidenceDialog(self.app.root, case)
        self.app.root.wait_window(dlg)
        if not dlg.result:
            return
        self.app.store.add_evidence(dlg.result)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "EVIDENCE_REGISTERED",
            f"{dlg.result.item_label} ({dlg.result.source_type.replace('_', ' ')})",
            self.app.secret)
        self._refresh_cases(select=case.id)
        self.app.notify("Evidence registered.")

    # ---------- rendering ----------
    def _refresh_cases(self, select=None):
        self.case_tree.delete(*self.case_tree.get_children())
        for case in self.app.store.cases:
            evs = self.app.store.get_evidence_for_case(case.id)
            self.case_tree.insert("", "end", iid=case.id,
                                  values=(case.status, len(evs), f"{case.case_number}", case.title))
        if select:
            if self.case_tree.exists(select):
                self.case_tree.selection_set(select)
                self.case_tree.see(select)
        self._render_detail()

    def _on_case_select(self):
        self._render_detail()

    def _render_detail(self):
        case = self._selected_case()
        if not case:
            self.detail_text.configure(text="Select a case to inspect its details and evidence.")
            self.ev_label.configure(text="Evidence (0)")
            self.ev_tree.delete(*self.ev_tree.get_children())
            return
        self.detail_text.configure(
            text=f"{case.case_number}  ·  {case.status}\n{case.title}\n\n"
                 f"Agency: {case.agency or '—'}\nInvestigator: {case.investigator or '—'} ({case.role or '—'})\n"
                 f"Created: {case.created_at.replace('T', ' ')[:19]}  ·  Updated: {case.updated_at.replace('T', ' ')[:19]}\n\n"
                 f"{case.description or ''}")
        self._render_evidence(case.id)

    def _render_evidence(self, case_id):
        evs = self.app.store.get_evidence_for_case(case_id)
        self.ev_label.configure(text=f"Evidence ({len(evs)})")
        self.ev_tree.delete(*self.ev_tree.get_children())
        for e in evs:
            status = "VERIFIED" if e.verified else ("ACQUIRED" if e.hashes else "PENDING")
            h = e.hashes or {}
            self.ev_tree.insert("", "end", iid=e.id, values=(
                e.source_type.replace("_", " ").title(),
                format_bytes(e.size_bytes),
                (h.get("sha256") or "")[:24] + "…",
                status,
            ))

    def refresh(self):
        self._refresh_cases(select=self.app.active_case_id)