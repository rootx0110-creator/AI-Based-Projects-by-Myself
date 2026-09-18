"""Phishing Email Analyzer - main GUI application."""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

import customtkinter as ctk

from engine.email_parser import EmlMail
from analysis import run_analysis
from utils.report_generator import ReportGenerator
from utils.state import StateManager, ensure_dirs
from utils.colors import color_lerp
from widgets.risk_gauge import RiskGauge

# --------------------------------------------------------------------------- #
#  Theme & palette
# --------------------------------------------------------------------------- #
PALETTE = {
    "bg": "#0b1220",
    "surface": "#111a2e",
    "surface2": "#16223a",
    "border": "#22304d",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "accent": "#38bdf8",
}

VERDICT_COLORS = {
    "SAFE": "#2ecc71",
    "LOW RISK": "#f1c40f",
    "MODERATE": "#f59e0b",
    "HIGH RISK": "#ef4444",
    "CRITICAL": "#a855f7",
}

TIPMAP = {
    "critical": "#a855f7",
    "high": "#ef4444",
    "medium": "#f59e0b",
    "low": "#f1c40f",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

TABS = ("Dashboard", "Headers", "URLs", "Attachments")

SAMPLE_EMAIL = """From: "Microsoft Account Team" <account-alert@microsoft-secure-alerts.info>
To: victim@example.com
Subject: [Action Required] Your Microsoft account sign-in attempt
Date: Mon, 15 Sep 2026 09:14:00 +0000
Reply-To: claims-monitor-8471@gmail.com
Message-ID: <8f22@mailer.win-alert-server.net>
Content-Type: multipart/alternative; boundary="b_alt"

--b_alt
Content-Type: text/plain; charset="utf-8"

We detected an unusual sign-in attempt to your account.
Sign in to verify: http://microsoft-secure-alerts.info/secure/verify-account?ref=0X88F

--b_alt
Content-Type: text/html; charset="utf-8"

<html><body><a href="http://microsoft-secure-alerts.info/secure/verify-account?ref=0X88F">Verify your account now</a></body></html>

--b_alt--
"""


class App(ctk.CTk):
    def __init__(self, store: StateManager):
        super().__init__(fg_color=PALETTE["bg"])
        self.store = store
        self.analysis_result = None
        self.current_source_name = ""
        self._result_queue: queue.Queue = queue.Queue()

        self.title("Phishing Email Analyzer — Header / URL / Attachment Triage")
        self.geometry("1200x800")
        self.minsize(1000, 660)

        self.tab_switch = {}
        self._configure_grid()
        self._build_header()
        self._build_body()
        self._build_footer()

        self.refresh_gauge(0, "SAFE", animate=False)
        self._select_tab("Dashboard")
        self._poll_results()

    # ------------------------------------------------------------------ #
    def _configure_grid(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ #
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=PALETTE["surface"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        pad = 18

        top_l = ctk.CTkFrame(header, fg_color="transparent")
        top_l.pack(side="left", fill="y", padx=pad, pady=10)
        ctk.CTkLabel(top_l, text="Phishing Email Analyzer",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color="#f8fafc").pack(anchor="w")
        ctk.CTkLabel(top_l,
                     text="Header \u00b7 URL \u00b7 Attachment forensic triage",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=PALETTE["muted"]).pack(anchor="w")

        self.input_panel = ctk.CTkFrame(header, fg_color="transparent")
        self.input_panel.pack(side="left", fill="x", expand=True, padx=pad, pady=10)

        self.paste_entry = ctk.CTkEntry(
            self.input_panel,
            placeholder_text="Paste raw email source here, or load a file / sample below \u2026",
            fg_color=PALETTE["surface2"], border_color=PALETTE["border"],
            corner_radius=8, height=36, font=ctk.CTkFont(size=12))
        self.paste_entry.pack(side="top", fill="x", pady=(0, 6))

        btn_row = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(0, 0))

        self.load_btn = ctk.CTkButton(
            btn_row, text="\U0001F4C2  Load Email", width=130, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=PALETTE["surface2"], hover_color="#1d2c4d",
            border_color=PALETTE["border"], border_width=1,
            command=self.choose_email_file)
        self.load_btn.pack(side="left", padx=(0, 6))

        self.sample_btn = ctk.CTkButton(
            btn_row, text="\U0001F4C1  Sample", width=90, height=32,
            font=ctk.CTkFont(size=12),
            fg_color=PALETTE["surface2"], hover_color="#1d2c4d",
            border_color=PALETTE["border"], border_width=1,
            command=self._load_sample)
        self.sample_btn.pack(side="left", padx=(0, 6))

        self.analyze_btn = ctk.CTkButton(
            btn_row, text="\u25B6  Analyze", width=110, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1d4ed8", hover_color="#2563eb",
            command=self._analyze_clicked)
        self.analyze_btn.pack(side="left", padx=(0, 6))

        self.export_btn = ctk.CTkButton(
            btn_row, text="\u2B73  Export HTML", width=140, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0e7490", hover_color="#0891b2",
            command=self._export_report)
        self.export_btn.pack(side="left")
        self.export_btn.configure(state="disabled")

    # ------------------------------------------------------------------ #
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(12, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self._build_tabs(body)
        self._build_content(body)

    def _build_tabs(self, parent):
        tabs = ctk.CTkFrame(parent, fg_color=PALETTE["surface"], corner_radius=12)
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        bar = ctk.CTkFrame(tabs, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)

        self.tab_switch = {}
        for i, name in enumerate(TABS):
            btn = ctk.CTkButton(
                bar, text=name, width=140, height=34, corner_radius=8,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=PALETTE["surface2"], hover_color="#254b8f",
                text_color=PALETTE["muted"],
                border_color=PALETTE["border"], border_width=1,
                command=lambda n=name: self._select_tab(n))
            btn.grid(row=0, column=i, padx=4)
            self.tab_switch[name] = btn
        bar.grid_columnconfigure(len(TABS), weight=1)

    def _build_content(self, parent):
        self.content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.tab_views = {}
        self._build_dashboard()
        self._build_headers_view()
        self._build_urls_view()
        self._build_attachments_view()

    # ----------------------------- Dashboard ----------------------------- #
    def _build_dashboard(self):
        dash = ctk.CTkFrame(self.content_frame, fg_color=PALETTE["surface"],
                            corner_radius=14)
        dash.grid(row=0, column=0, sticky="nsew")
        dash.grid_columnconfigure(0, weight=3)
        dash.grid_columnconfigure(1, weight=4)
        dash.grid_rowconfigure(0, weight=1)
        self.tab_views["Dashboard"] = dash

        left = ctk.CTkFrame(dash, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(24, 8), pady=24)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        self.gauge = RiskGauge(left, size=230)
        self.gauge.grid(row=0, column=0)

        self.verdict_badge = ctk.CTkLabel(
            left, text="—", height=40, width=210,
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#f8fafc", corner_radius=16,
            fg_color=color_lerp(PALETTE["bg"], "#2ecc71", 0.20))
        self.verdict_badge.grid(row=1, column=0, pady=(10, 4))

        self.score_caption = ctk.CTkLabel(
            left, text="Load an email and analyze",
            font=ctk.CTkFont(size=12), text_color=PALETTE["muted"])
        self.score_caption.grid(row=2, column=0, pady=(4, 0))

        right = ctk.CTkFrame(dash, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 24), pady=24)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self.evidence_scroll = ctk.CTkScrollableFrame(
            right, fg_color=PALETTE["surface2"], corner_radius=12)
        self.evidence_scroll.grid(row=0, column=0, sticky="nsew")

        self.placeholder = ctk.CTkLabel(
            self.evidence_scroll,
            text="\U0001F50D  No analysis performed yet.\n\n"
                 "Load an email file or paste raw email source,\n"
                 "then click Analyze.",
            font=ctk.CTkFont(size=14), text_color=PALETTE["muted"], justify="center")
        self.placeholder.pack(padx=20, pady=60)

        stats = ctk.CTkFrame(right, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for i in range(3):
            stats.grid_columnconfigure(i, weight=1)

        self.card_urls = self._make_stat_card(stats, 0, "URLs")
        self.card_atts = self._make_stat_card(stats, 1, "Attachments")
        self.card_time = self._make_stat_card(stats, 2, "Analysis")

    @staticmethod
    def _make_stat_card(parent, col, title):
        frame = ctk.CTkFrame(parent, fg_color=PALETTE["surface2"], corner_radius=10)
        frame.grid(row=0, column=col, sticky="ew", padx=4)
        ctk.CTkLabel(frame, text=title.upper(),
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PALETTE["muted"]).pack(pady=(10, 0))
        val = ctk.CTkLabel(frame, text="—",
                           font=ctk.CTkFont(size=22, weight="bold"),
                           text_color=PALETTE["text"])
        val.pack(pady=(2, 10))
        frame._val_lbl = val
        return frame

    # ----------------------------- Headers ------------------------------ #
    def _build_headers_view(self):
        view = ctk.CTkFrame(self.content_frame, fg_color=PALETTE["surface"],
                            corner_radius=14)
        view.grid(row=0, column=0, sticky="nsew")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(2, weight=1)
        self.tab_views["Headers"] = view

        meta_panel = ctk.CTkFrame(view, fg_color="transparent")
        meta_panel.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))

        meta_box = ctk.CTkFrame(meta_panel, fg_color=PALETTE["surface2"],
                                corner_radius=10)
        meta_box.pack(fill="x")
        self.headers_meta = ctk.CTkLabel(
            meta_box, text="No headers parsed yet.",
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=PALETTE["text"], justify="left", anchor="nw")
        self.headers_meta.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(view, text="RAW HEADERS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=PALETTE["muted"]).grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 6))

        self.raw_headers_text = ctk.CTkTextbox(
            view, fg_color="#0d1526", border_color=PALETTE["border"],
            border_width=1, corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#a5b4fc", wrap="word")
        self.raw_headers_text.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))

    # ------------------------------ URLs -------------------------------- #
    def _build_urls_view(self):
        view = ctk.CTkFrame(self.content_frame, fg_color=PALETTE["surface"],
                            corner_radius=14)
        view.grid(row=0, column=0, sticky="nsew")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        self.tab_views["URLs"] = view

        top = ctk.CTkFrame(view, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        self.urls_count_lbl = ctk.CTkLabel(
            top, text="0 URLs detected", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PALETTE["text"])
        self.urls_count_lbl.pack(side="left")

        self.urls_tree_frame = ctk.CTkFrame(view, fg_color=PALETTE["surface2"],
                                            corner_radius=10)
        self.urls_tree_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.urls_tree_frame.grid_columnconfigure(0, weight=1)
        self.urls_tree_frame.grid_rowconfigure(0, weight=1)

        self.urls_tree = ttk.Treeview(
            self.urls_tree_frame, columns=("URL", "Class", "Threats"),
            show="headings")
        self.urls_tree.heading("URL", text="URL")
        self.urls_tree.heading("Class", text="Classification")
        self.urls_tree.heading("Threats", text="Threat Indicators")
        self.urls_tree.column("URL", width=400, anchor="w")
        self.urls_tree.column("Class", width=130, anchor="center")
        self.urls_tree.column("Threats", width=390, anchor="w")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=PALETTE["surface2"],
                        fieldbackground=PALETTE["surface2"],
                        foreground=PALETTE["text"],
                        borderwidth=0, rowheight=26,
                        font=("Segoe UI", 11))
        style.configure("Treeview.Heading",
                        background="#1d2c4d", foreground=PALETTE["muted"],
                        relief="flat", font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#1d4ed8")])

        ysb = ttk.Scrollbar(self.urls_tree_frame, orient="vertical",
                            command=self.urls_tree.yview)
        self.urls_tree.configure(yscrollcommand=ysb.set)
        self.urls_tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        ysb.grid(row=0, column=1, sticky="ns", pady=8)

    # --------------------------- Attachments ---------------------------- #
    def _build_attachments_view(self):
        view = ctk.CTkFrame(self.content_frame, fg_color=PALETTE["surface"],
                            corner_radius=14)
        view.grid(row=0, column=0, sticky="nsew")
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        self.tab_views["Attachments"] = view

        top = ctk.CTkFrame(view, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        self.atts_count_lbl = ctk.CTkLabel(
            top, text="0 attachments detected", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PALETTE["text"])
        self.atts_count_lbl.pack(side="left")

        self.atts_scroll = ctk.CTkScrollableFrame(
            view, fg_color=PALETTE["surface2"], corner_radius=10)
        self.atts_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.atts_scroll.grid_columnconfigure(0, weight=1)

    # ----------------------------- Footer ------------------------------- #
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=PALETTE["surface"], corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")

        self.status_lbl = ctk.CTkLabel(
            footer, text="Ready \u2014 load an email file, paste source, or use the sample",
            font=ctk.CTkFont(size=12), text_color=PALETTE["muted"],
            anchor="w")
        self.status_lbl.pack(side="left", padx=16, pady=8)

        self.progress = ctk.CTkProgressBar(footer, width=220, height=10,
                                           progress_color=PALETTE["accent"])
        self.progress.pack(side="right", padx=16, pady=8)
        self.progress.set(0)

    # ------------------------------------------------------------------ #
    def _select_tab(self, name: str):
        for key, view in self.tab_views.items():
            if key == name:
                view.grid()
                view.tkraise()
            else:
                view.grid_remove()
        for tab_name, btn in self.tab_switch.items():
            if tab_name == name:
                btn.configure(fg_color="#254b8f", text_color="#f8fafc",
                              border_color="#3b82f6")
            else:
                btn.configure(fg_color=PALETTE["surface2"],
                              text_color=PALETTE["muted"],
                              border_color=PALETTE["border"])

    # ------------------------------------------------------------------ #
    def _load_sample(self):
        self.paste_entry.delete(0, "end")
        self.paste_entry.configure(placeholder_text="Sample phishing email loaded \u2014 click Analyze")
        self._source_buffer = SAMPLE_EMAIL
        self.current_source_name = "sample_phishing.eml"
        self.status_lbl.configure(text="Sample phishing email loaded \u2014 click Analyze")

    def choose_email_file(self):
        path = filedialog.askopenfilename(
            title="Select an email file",
            filetypes=[("Email files", "*.eml *.msg *.txt"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            if os.path.getsize(path) > 20 * 1024 * 1024:
                if not messagebox.askyesno("Large file",
                                           "This file is over 20 MB and may parse slowly. Continue?"):
                    return
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception as exc:
            messagebox.showerror("Read error", f"Could not read file:\n{exc}")
            return
        self._source_buffer = source
        self.current_source_name = os.path.basename(path)
        self.paste_entry.delete(0, "end")
        self.paste_entry.configure(placeholder_text=f"Loaded {os.path.basename(path)} \u2014 click Analyze")
        self.status_lbl.configure(text=f"Loaded {os.path.basename(path)} \u2014 click Analyze")

    def _analyze_clicked(self):
        source = getattr(self, "_source_buffer", "") or self.paste_entry.get().strip()
        if not source:
            messagebox.showinfo("No email",
                                "Load an email file, paste raw source, or load the sample first.")
            return
        self._set_email_source(source, getattr(self, "current_source_name", "pasted-source"))

    # ------------------------------------------------------------------ #
    def _poll_results(self):
        """Drain the result queue from worker threads (safe for all platforms)."""
        try:
            while True:
                result_type, payload = self._result_queue.get_nowait()
                if result_type == "result":
                    self._render_result(payload)
                elif result_type == "error":
                    self._render_error(payload)
        except queue.Empty:
            pass
        self.after(60, self._poll_results)

    def _set_email_source(self, source: str, source_name: str):
        self.current_source_name = source_name
        self.analysis_result = None
        self.export_btn.configure(state="disabled")
        self.progress.set(0.15)
        self.status_lbl.configure(text=f"Analyzing {source_name} \u2026")
        threading.Thread(target=self._analyze_worker, args=(source,),
                         daemon=True).start()

    def _analyze_worker(self, source: str):
        try:
            email_obj = EmlMail(source, self.current_source_name)
            result = run_analysis(email_obj)
            self._result_queue.put(("result", result))
        except Exception as exc:
            self._result_queue.put(("error", str(exc)))

    def _render_error(self, msg: str):
        self.status_lbl.configure(text="Analysis failed")
        self.progress.set(0)
        messagebox.showerror("Analysis failed", msg)

    def _render_result(self, result: dict):
        self.analysis_result = result
        s = result["summary"]
        verdict, color = s["verdict"], s["color"]

        self.refresh_gauge(s["score"], verdict, animate=True)
        self.score_caption.configure(
            text=f"{result['meta']['source']}  \u00b7  {s['evidence_count']} signal(s)")
        self._render_evidence(result.get("evidence", []))
        self._render_urls(result.get("urls", {}))
        self._render_attachments(result.get("attachments", {}))
        self._render_headers(result)

        self.card_time._val_lbl.configure(text=f"{result['meta']['elapsed_ms']} ms")
        self.card_urls._val_lbl.configure(text=str(result["meta"]["url_count"]))
        self.card_atts._val_lbl.configure(text=str(result["meta"]["att_count"]))

        self.export_btn.configure(state="normal")
        self.progress.set(1.0)
        self.status_lbl.configure(
            text=f"{self.current_source_name}  \u00b7  score {s['score']} ({verdict.lower()})"
                 f"  \u00b7  {result['meta']['elapsed_ms']} ms")

        self.store.add_history({
            "subject": result["meta"]["subject"],
            "sender": result["meta"]["from"],
            "score": s["score"],
            "verdict": verdict,
            "url_count": result["meta"]["url_count"],
            "attachment_count": result["meta"]["att_count"],
        })
        self._select_tab("Dashboard")

    def refresh_gauge(self, score: int, verdict: str, animate: bool = True):
        color = VERDICT_COLORS.get(verdict, PALETTE["accent"])
        if animate:
            self.gauge.set_score(score, color)
        else:
            self.gauge.reset()
        self.verdict_badge.configure(text=verdict.upper(),
                                     fg_color=color_lerp(PALETTE["bg"], color, 0.25))

    # ------------------------------------------------------------------ #
    def _render_evidence(self, evidence: list):
        for w in self.evidence_scroll.winfo_children():
            w.destroy()
        if not evidence:
            ctk.CTkLabel(self.evidence_scroll,
                         text="No risk signals detected \u2014 email appears benign.",
                         font=ctk.CTkFont(size=14),
                         text_color=PALETTE["muted"]).pack(padx=20, pady=40)
            return
        for e in evidence:
            sev = e.get("severity", "medium")
            sev_color = TIPMAP.get(sev, PALETTE["muted"])

            card = ctk.CTkFrame(self.evidence_scroll,
                                fg_color=PALETTE["surface"], corner_radius=8,
                                border_width=1, border_color=PALETTE["border"])
            card.pack(fill="x", padx=4, pady=4)

            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=(8, 2))

            ctk.CTkLabel(head, text="\u25CF", text_color=sev_color,
                         font=ctk.CTkFont(size=12)).pack(side="left", pady=(6, 0))
            ctk.CTkLabel(head, text=e.get("label", "Finding"),
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=PALETTE["text"], anchor="w").pack(
                side="left", padx=6, pady=(2, 0))

            ctk.CTkLabel(head, text=f"+{e.get('weight', 0)}", width=44, height=24,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         fg_color=color_lerp(sev_color, PALETTE["surface2"], 0.25),
                         text_color=PALETTE["text"],
                         corner_radius=8).pack(side="right")

            ctk.CTkLabel(card, text=e.get("detail", ""),
                         font=ctk.CTkFont(size=12), text_color=PALETTE["muted"],
                         wraplength=540, justify="left", anchor="w").pack(
                fill="x", padx=24, pady=(0, 8))

    # ------------------------------------------------------------------ #
    def _render_urls(self, urls: dict):
        for item in self.urls_tree.get_children():
            self.urls_tree.delete(item)
        results = urls.get("results", [])
        self.urls_count_lbl.configure(text=f"{len(results)} URLs detected")
        for r in results:
            self.urls_tree.insert("", "end", values=(
                r["url"], r.get("classification", "benign").upper(),
                "; ".join(r.get("threats", [])) or "—"))

    def _render_attachments(self, attachments: dict):
        for w in self.atts_scroll.winfo_children():
            w.destroy()
        results = attachments.get("results", [])
        self.atts_count_lbl.configure(text=f"{len(results)} attachments detected")
        if not results:
            ctk.CTkLabel(self.atts_scroll,
                         text="No attachments in this email.",
                         font=ctk.CTkFont(size=13),
                         text_color=PALETTE["muted"]).pack(pady=30)
            return
        for r in results:
            cls = r.get("classification", "benign")
            cls_color = {"malicious": "#ef4444", "suspicious": "#f59e0b",
                         "benign": "#2ecc71"}.get(cls, PALETTE["muted"])

            card = ctk.CTkFrame(self.atts_scroll, fg_color=PALETTE["surface"],
                                corner_radius=10, border_width=1,
                                border_color=PALETTE["border"])
            card.pack(fill="x", pady=5, padx=2)
            card.grid_columnconfigure(0, weight=1)

            line = ctk.CTkFrame(card, fg_color="transparent")
            line.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
            ctk.CTkLabel(line, text=r["filename"],
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=PALETTE["text"], anchor="w").pack(side="left")

            pill_text = cls.upper() if cls != "benign" else "OK"
            ctk.CTkLabel(line, text=pill_text, width=84, height=22,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         fg_color=color_lerp(cls_color, PALETTE["surface"], 0.4),
                         text_color=PALETTE["text"],
                         corner_radius=8).pack(side="right")

            ctk.CTkLabel(card,
                         text=f"{r.get('content_type', '')}  \u00b7  "
                              f"{self._human_size(r.get('size', 0))}  \u00b7  "
                              f"ext: {r.get('extension', '(none)')}",
                         font=ctk.CTkFont(size=12), text_color=PALETTE["muted"],
                         anchor="w").grid(row=1, column=0, sticky="ew",
                                          padx=12, pady=(0, 2))

            ctk.CTkLabel(card,
                         text=f"SHA-256  {r.get('sha256', '-')}\n"
                              f"MD5      {r.get('md5', '-')}",
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color="#a5b4fc", justify="left", anchor="w").grid(
                row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

            if r.get("threats"):
                ctk.CTkLabel(card,
                             text=" \u26A0  " + "  \u00b7  ".join(r["threats"]),
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=cls_color, anchor="w", justify="left").grid(
                    row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _render_headers(self, result: dict):
        meta = result["meta"]
        hmeta = result["headers"].get("metadata", {})
        lines = (
            f"From       : {meta['from']}\n"
            f"To         : {hmeta.get('to', '') or '(empty)'}\n"
            f"Cc         : {hmeta.get('cc', '') or '(empty)'}\n"
            f"Reply-To   : {hmeta.get('reply_to', '') or '(none)'}\n"
            f"Subject    : {meta['subject']}\n"
            f"Date       : {meta['date']}\n"
            f"Message-ID : {hmeta.get('message_id', '') or '(none)'}\n"
            f"Return-Path: {hmeta.get('return_path', '') or '(none)'}\n"
            f"SPF        : {hmeta.get('spf', '') or '(no result)'}\n"
            f"DKIM       : {hmeta.get('dkim', '') or '(no result)'}\n"
            f"DMARC      : {hmeta.get('dmarc', '') or '(no result)'}"
        )
        self.headers_meta.configure(text=lines)
        self.raw_headers_text.delete("1.0", "end")
        self.raw_headers_text.insert("1.0", result.get("raw_headers", ""))

    # ------------------------------------------------------------------ #
    def _export_report(self):
        if not self.analysis_result:
            messagebox.showinfo("Nothing to export", "Analyze an email first.")
            return
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        default = os.path.join(
            reports_dir, f"phish_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        path = filedialog.asksaveasfilename(
            title="Save HTML report", initialdir=reports_dir,
            initialfile=os.path.basename(default),
            defaultextension=".html",
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")])
        if not path:
            return
        try:
            html = ReportGenerator().generate(self.analysis_result)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.status_lbl.configure(text=f"Report exported \u2192 {path}")
            messagebox.showinfo("Report exported", f"Report saved to:\n{path}",
                                parent=self)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)

    @staticmethod
    def _human_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"


def main():
    ensure_dirs()
    state = StateManager()
    app = App(state)
    app.mainloop()