import os
import shutil
import subprocess
import time

import customtkinter as ctk

from ..core import report as repmod
from .base import BaseView
from .theme import (PANEL, PANEL2, BORDER, ACCENT, ACCENT2, GOOD, MUTED, TEXT,
                    font, ACCENT_BTN)


class ReportsView(BaseView):
    key = "reports"
    title = "Reports"
    subtitle = "Generate a professional HTML chain-of-custody evidence report"

    def __init__(self, master, app):
        super().__init__(master, app)
        body = self.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                            border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Case", font=font(13, "bold"), text_color=ACCENT).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        self.case_combo = ctk.CTkOptionMenu(card, values=["—"], width=380,
                                            fg_color=PANEL2, button_color=ACCENT_BTN,
                                            button_hover_color="#1b7180", text_color=TEXT,
                                            font=font(12))
        self.case_combo.grid(row=0, column=1, sticky="w")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 4))
        self.inc_cust = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Include full chain-of-custody log", variable=self.inc_cust,
                         font=font(12), text_color=TEXT, fg_color=ACCENT_BTN,
                         hover_color="#1b7180", border_color=BORDER).pack(side="left", padx=(0, 24))
        self.inc_hashes = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Include per-item hash block", variable=self.inc_hashes,
                         font=font(12), text_color=TEXT, fg_color=ACCENT_BTN,
                         hover_color="#1b7180", border_color=BORDER).pack(side="left")

        act = ctk.CTkFrame(card, fg_color="transparent")
        act.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))
        act.grid_columnconfigure(0, weight=1)
        self.gen_btn = ctk.CTkButton(act, text="⬇  Generate HTML Report", font=font(14, "bold"),
                                     fg_color=ACCENT_BTN, hover_color="#1b7180", height=40,
                                     width=220, command=self._generate)
        self.gen_btn.grid(row=0, column=0, sticky="w")
        self.open_btn = ctk.CTkButton(act, text="Open in browser", font=font(12),
                                      fg_color="transparent", border_width=1,
                                      border_color=BORDER, text_color=ACCENT2, height=32,
                                      state="disabled", command=self._open_last)
        self.open_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.folder_btn = ctk.CTkButton(act, text="Open reports folder", font=font(12),
                                        fg_color="transparent", border_width=1,
                                        border_color=BORDER, text_color=ACCENT2, height=32,
                                        command=self._open_folder)
        self.folder_btn.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.status = ctk.CTkLabel(body, text="", font=font(12.5), text_color=GOOD, anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        recent_card = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=12, border_width=1,
                                   border_color=BORDER)
        recent_card.grid(row=2, column=0, sticky="nsew")
        recent_card.grid_columnconfigure(0, weight=1)
        recent_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(recent_card, text="Previously generated reports", font=font(14, "bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="w",
                     padx=16, pady=(14, 6))
        self.file_text = ctk.CTkTextbox(recent_card, fg_color="#0e141d", border_color=BORDER,
                                        border_width=1, corner_radius=8, font=font(12),
                                        text_color=MUTED, wrap="none")
        self.file_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.file_text.configure(state="disabled")
        self._last_path = None

    def refresh(self):
        values = [c.display for c in self.app.store.cases]
        if not values:
            values = ["—"]
        self.case_combo.configure(values=values)
        cur = self.case_combo.get()
        if cur not in values:
            self.case_combo.set(values[0])
        self._refresh_list()

    def _selected_case(self):
        val = self.case_combo.get()
        for c in self.app.store.cases:
            if c.display == val:
                return c
        return None

    def _generate(self):
        case = self._selected_case()
        if not case:
            self.app.notify("Select a case to report.", "#f59e0b")
            return
        evs = self.app.store.get_evidence_for_case(case.id)
        if not evs:
            self.app.notify("No evidence on this case to report yet.", "#f59e0b")
            return
        custody = self.app.store.custody if self.inc_cust.get() else []
        html = repmod.generate_html_report(
            case, evs, custody,
            f"{self.app.store.settings.operator} ({self.app.store.settings.role})",
            include_custody=self.inc_cust.get())
        path = repmod.save_report(case, html, self.app.store.reports_dir)
        self._last_path = path
        self.open_btn.configure(state="normal")
        self.status.configure(text=f"Report saved: {path}", text_color=GOOD)
        self._refresh_list()
        repmod.open_report(path)
        self.app.store.append_custody(
            self.app.store.settings.operator, self.app.store.settings.role,
            "REPORT_GENERATED",
            f"{case.case_number} — {os.path.basename(path)} ({len(evs)} evidence items)",
            self.app.secret)
        self.app.notify("HTML report generated and opened in your browser.", GOOD)

    def _open_last(self):
        if self._last_path and os.path.exists(self._last_path):
            repmod.open_report(self._last_path)

    def _open_folder(self):
        if os.path.isdir(self.app.store.reports_dir):
            subprocess.Popen(["explorer", os.path.normpath(self.app.store.reports_dir)])

    def _refresh_list(self):
        dirp = self.app.store.reports_dir
        try:
            files = sorted((f for f in os.listdir(dirp) if f.endswith(".html")),
                           key=lambda f: os.path.getmtime(os.path.join(dirp, f)), reverse=True)
        except OSError:
            files = []
        self.file_text.configure(state="normal")
        self.file_text.delete("1.0", "end")
        for f in files[:12]:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(os.path.join(dirp, f))))
            self.file_text.insert("end", f"{ts}   {f}\n")
        self.file_text.configure(state="disabled")