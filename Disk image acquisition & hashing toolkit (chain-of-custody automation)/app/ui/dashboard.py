import customtkinter as ctk

from ..core.models import format_bytes
from .base import BaseView
from .theme import ACCENT, ACCENT2, GOOD, BAD, WARN, MUTED, TEXT, font, PANEL2, BORDER
from .widgets import StatCard


class DashboardView(BaseView):
    key = "dashboard"
    title = "Dashboard"
    subtitle = "Forensic case overview and integrity at a glance"

    def __init__(self, master, app):
        super().__init__(master, app)
        body = self.body
        body.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        body.grid_rowconfigure(3, weight=1)

        self.case_card = StatCard(body, "Active Cases", "0", ACCENT, "Select / create in Cases")
        self.case_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
        self.ev_card = StatCard(body, "Evidence Items", "0", ACCENT2, "Acquired images")
        self.ev_card.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.size_card = StatCard(body, "Evidence Volume", "0 B", GOOD, "Total acquired")
        self.size_card.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)
        self.chain_card = StatCard(body, "Custody Entries", "0", ACCENT2, "Append-only log")
        self.chain_card.grid(row=0, column=3, sticky="nsew", padx=8, pady=8)
        self.verif_card = StatCard(body, "Verify Status", "0/0", WARN, "Images verified")
        self.verif_card.grid(row=0, column=4, sticky="nsew", padx=(8, 0), pady=8)

        self.active_card = ctk.CTkFrame(body, fg_color=PANEL2, corner_radius=12,
                                        border_width=1, border_color=BORDER)
        self.active_card.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(0, 8), pady=8)
        self.active_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.active_card, text="Active Case", font=font(14, "bold"),
                     text_color=ACCENT, anchor="w").grid(row=0, column=0, columnspan=2,
                                                         sticky="w", padx=16, pady=(14, 4))
        self.active_acct = ctk.CTkLabel(self.active_card, text="No case selected", font=font(13),
                                        text_color=MUTED, anchor="w", justify="left")
        self.active_acct.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 14))

        self.integrity_card = ctk.CTkFrame(body, fg_color=PANEL2, corner_radius=12,
                                           border_width=1, border_color=BORDER)
        self.integrity_card.grid(row=1, column=3, columnspan=2, sticky="nsew", padx=(8, 0), pady=8)
        self.integrity_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.integrity_card, text="Chain Integrity (HMAC)", font=font(14, "bold"),
                     text_color=ACCENT, anchor="w").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.integrity_label = ctk.CTkLabel(self.integrity_card, text="—", font=font(13),
                                            text_color=GOOD, anchor="w")
        self.integrity_label.grid(row=1, column=0, sticky="w", padx=16, pady=(2, 4))
        self.integrity_detail = ctk.CTkLabel(self.integrity_card, text="",
                                             font=font(11), text_color=MUTED,
                                             anchor="w", justify="left", wraplength=420)
        self.integrity_detail.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

        recent_frame = ctk.CTkFrame(body, fg_color="transparent")
        recent_frame.grid(row=2, column=0, columnspan=5, sticky="nsew", pady=(6, 0))
        recent_frame.grid_columnconfigure(0, weight=1)
        self.recent_title = ctk.CTkLabel(recent_frame, text="Recent Chain of Custody Activity",
                                         font=font(15, "bold"), text_color=TEXT, anchor="w")
        self.recent_title.grid(row=0, column=0, sticky="w")
        self.log_text = ctk.CTkTextbox(body, fg_color="#0e141d", border_color=BORDER,
                                       border_width=1, corner_radius=10,
                                       font=font(12.5), text_color="#d7e2ee", wrap="word")
        self.log_text.grid(row=3, column=0, columnspan=5, sticky="nsew", pady=(8, 0))
        self.log_text.configure(state="disabled")

    def refresh(self):
        store = self.app.store
        total_ev = len(store.evidence)
        total_bytes = sum(e.size_bytes for e in store.evidence)
        verified = sum(1 for e in store.evidence if e.verified)
        self.case_card.update(len(store.cases),
                              extra=f"{sum(1 for c in store.cases if c.status == 'Open')} open")
        self.ev_card.update(total_ev)
        self.size_card.update(format_bytes(total_bytes))
        self.chain_card.update(len(store.custody))
        self.verif_card.update(f"{verified}/{total_ev}",
                               extra="images verified" if total_ev else "no evidence yet",
                               accent=GOOD if verified == total_ev and total_ev else WARN)

        case = store.get_case(self.app.active_case_id)
        if case:
            evs = store.get_evidence_for_case(case.id)
            self.active_acct.configure(
                text=f"{case.case_number}\n{case.title}\n"
                     f"Agency: {case.agency or '—'}  ·  Investigator: {case.investigator or '—'}  ·  "
                     f"{len(evs)} evidence item(s)", text_color=MUTED)
        else:
            self.active_acct.configure(text="No case selected — open Cases to create one.",
                                       text_color=MUTED)

        ok, problems = store.verify_chain(self.app.secret)
        self.integrity_label.configure(text="✅ Chain verified — no tampering detected" if ok
                                       else "⚠  Chain COMPROMISED — inspect Custody view",
                                       text_color=GOOD if ok else BAD)
        self.integrity_detail.configure(
            text=f"{len(store.custody)} entries chained with HMAC-SHA256."
                 + ("\n" + problems[0] if problems else ""))

        self._render_log(store.custody[-12:])

    def _render_log(self, entries):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        if not entries:
            self.log_text.insert("end", "No chain-of-custody activity recorded yet.\n")
        for e in reversed(entries):
            ts = e.timestamp.replace("T", " ")[:19]
            line = f"[#{e.seq}] {ts}  ·  {e.action}\n"
            self.log_text.insert("end", line, "ts")
            self.log_text.insert("end", f"    {e.detail or ''}  —  {e.actor or 'system'}\n")
        self.log_text.configure(state="disabled")