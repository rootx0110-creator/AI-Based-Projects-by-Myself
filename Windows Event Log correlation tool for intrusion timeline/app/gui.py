"""Dark, modern tkinter user interface for the correlation tool."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from .correlator import Correlator
from .models import Alert, AnalysisResult, EventRecord, IncidentChain, Phase, Severity
from .parser import (LIVE_CHANNELS, TIME_CHOICES, ParseCanceled,
                     events_from_wevtutil)
from .report import build_report

# --------------------------------------------------------------------------- #
# Palette (light, friendly theme)
# --------------------------------------------------------------------------- #
BG = "#eef2f8"
PANEL = "#ffffff"
PANEL2 = "#e8edf5"
SIDE = "#e4ebf7"
LINE = "#d3dcea"
TXT = "#182334"
MUT = "#5c6b82"
ACC = "#2563eb"
CYAN = "#0891b2"
GREEN = "#16a34a"
AMBER = "#b45309"
ORANGE = "#ea580c"
RED = "#dc2626"
PINK = "#db2777"
INDIGO = "#6366f1"
HDR = "#1d4ed8"
TXT_ON_HDR = "#ffffff"
MUT_ON_HDR = "#c9d6ff"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_BIG = ("Segoe UI", 15, "bold")


def _sev_tkfg(sev: Severity) -> str:
    return {Severity.INFO: MUT, Severity.LOW: GREEN, Severity.MEDIUM: AMBER,
            Severity.HIGH: ORANGE, Severity.CRITICAL: RED}[sev]


def _fmt(dt: datetime) -> str:
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_t(dt: datetime) -> str:
    return dt.astimezone().strftime("%H:%M:%S")


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windows Event Log Correlation Tool — Intrusion Timeline")
        self.geometry("1320x860")
        self.minsize(1080, 700)
        self.configure(bg=BG)

        self.current_events: List[EventRecord] = []
        self.result: Optional[AnalysisResult] = None
        self.sources: List[str] = []
        self._worker: Optional[threading.Thread] = None
        self._cancel = False
        self._busy = False
        self._msgq: "queue.Queue" = queue.Queue()

        self._build_style()
        self._build_layout()
        self.set_status("Ready. Load events to begin.")
        self.after(100, self._poll_msgq)

    # ------------------------------------------------------------------ #
    # styling
    # ------------------------------------------------------------------ #
    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TXT, font=FONT,
                        fieldbackground=PANEL)
        style.configure("TFrame", background=BG)
        style.configure("View.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TXT, font=FONT)
        style.configure("Muted.TLabel", background=BG, foreground=MUT, font=FONT_SMALL)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("CardHead.TLabel", background=PANEL, foreground=MUT,
                        font=FONT_SMALL)
        style.configure("CardVal.TLabel", background=PANEL, foreground=TXT,
                        font=FONT_BIG)
        style.map("CardVal.TLabel", foreground=[])

        style.configure("Side.TFrame",
                         background=SIDE)
        style.configure("Side.TLabel",
                         background=SIDE, foreground=MUT,
                         font=FONT_SMALL)

        style.configure("Accent.TButton",
                        background=ACC, foreground=TXT_ON_HDR, font=FONT_BOLD,
                        borderwidth=0, focusthickness=0, padding=(12, 8))
        style.map("Accent.TButton",
                  background=[("active", "#3b82f6"), ("pressed", "#1d4ed8")],
                  foreground=[("disabled", "#a9b8d4")])
        style.configure("Side.TButton",
                        background=PANEL2, foreground=TXT, font=FONT,
                        borderwidth=1, relief="flat", padding=(10, 7))
        style.map("Side.TButton",
                  background=[("active", "#e0eaff"), ("pressed", "#cfddfa")])
        style.configure("Danger.TButton",
                        background="#fde6e6", foreground="#9f1239", font=FONT,
                        borderwidth=1, relief="flat", padding=(10, 7))
        style.map("Danger.TButton",
                  background=[("active", "#fbcaca"), ("pressed", "#f7b3b3")])

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL2, foreground=MUT,
                        font=FONT, padding=(14, 7), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL)],
                  foreground=[("selected", TXT)])

        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TXT, borderwidth=0, rowheight=26, font=FONT)
        style.configure("Treeview.Heading", background=PANEL2, foreground=MUT,
                        font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#dbeafe")],
                  foreground=[("selected", TXT)])

        style.configure("TProgressbar", troughcolor=PANEL2,
                        background=CYAN, bordercolor=BG, lightcolor=CYAN,
                        darkcolor=CYAN)

        self._tree_style(style)

    def _tree_style(self, style: ttk.Style) -> None:
        # Tags used in Treeview inserts are severity names lowercased
        # ("critical", "high", "medium", "low", "info").
        for label, color in (("critical", RED), ("high", ORANGE),
                             ("medium", AMBER), ("low", GREEN), ("info", MUT)):
            style.configure(label + ".Treeview", foreground=color)

    # ------------------------------------------------------------------ #
    # layout
    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        self._banner()
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.body.columnconfigure(1, weight=1)
        self.body.rowconfigure(0, weight=1)
        self._sidebar()
        self._content()
        self._statsbar()

    def _banner(self) -> None:
        bar = tk.Frame(self, bg=HDR, height=64)
        bar.pack(fill="x", side="top")
        tk.Label(bar, text="Windows Event Log Correlation Tool",
                 font=FONT_TITLE, fg=TXT_ON_HDR, bg=HDR).pack(side="left", padx=16, pady=10)
        tk.Label(bar, text="Intrusion Timeline  ·  MITRE ATT&CK",
                 font=FONT_SMALL, fg=MUT_ON_HDR, bg=HDR).pack(side="left", pady=13)
        self.pill_events = tk.Label(bar, text="events: 0", font=FONT_BOLD, fg=ACC,
                                    bg="#ffffff", padx=12, pady=4)
        self.pill_alerts = tk.Label(bar, text="alerts: 0", font=FONT_BOLD, fg=RED,
                                    bg="#ffffff", padx=12, pady=4)
        self.pill_phase = tk.Label(bar, text="phases: -", font=FONT_BOLD, fg=GREEN,
                                   bg="#ffffff", padx=12, pady=4)
        for w in (self.pill_events, self.pill_alerts, self.pill_phase):
            w.pack(side="right", padx=4, pady=16)

    def _sidebar(self) -> None:
        side = ttk.Frame(self.body, style="Side.TFrame", padding=(10, 10))
        side.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        ttk.Label(side, text="ANALYSIS", style="Side.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Button(side, text="◆ Load Live Logs", style="Accent.TButton",
                   command=self._ask_live).pack(fill="x", pady=(0, 6))
        ttk.Button(side, text="▼ Load EVTX Files", style="Accent.TButton",
                   command=self._ask_evtx).pack(fill="x", pady=(0, 6))

        ttk.Label(side, text=" ",
                  style="Side.TLabel").pack(pady=2)
        ttk.Button(side, text="▶ Analyze (correlate)", style="Side.TButton",
                   command=self.start_analysis).pack(fill="x", pady=4)
        ttk.Button(side, text="↧ Download HTML Report", style="Side.TButton",
                   command=self.export_report).pack(fill="x", pady=4)
        ttk.Button(side, text="✕ Clear All", style="Danger.TButton",
                   command=self.clear_all).pack(fill="x", pady=4)

        ttk.Label(side, text="DATA", style="Side.TLabel").pack(anchor="w", pady=(14, 6))
        self.side_info = tk.Label(side, justify="left", text="No data loaded.",
                                  font=FONT_SMALL, fg=MUT, bg=PANEL, wraplength=170)
        self.side_info.pack(anchor="w", pady=(0, 4))

        ttk.Label(side, text="TIP: load System + Security logs for\n"
                             "richest coverage. Sysmon adds process\n"
                             "and network visibility.",
                  style="Side.TLabel", justify="left").pack(anchor="w", pady=(16, 0))

    def _content(self) -> None:
        wrap = tk.Frame(self.body, bg=BG)
        wrap.grid(row=0, column=1, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.nb = ttk.Notebook(wrap)
        self.nb.grid(row=0, column=0, sticky="nsew")

        self.tab_dash = ttk.Frame(self.nb)
        self.tab_tl = ttk.Frame(self.nb)
        self.tab_alerts = ttk.Frame(self.nb)
        self.tab_events = ttk.Frame(self.nb)
        for tab, label in ((self.tab_dash, "  Dashboard  "),
                           (self.tab_tl, "  Intrusion Timeline  "),
                           (self.tab_alerts, "  Alerts  "),
                           (self.tab_events, "  Raw Events  ")):
            self.nb.add(tab, text=label)

        self._build_dashboard()
        self._build_timeline()
        self._build_alerts()
        self._build_events()

    def _statsbar(self) -> None:
        bar = tk.Frame(self, bg=PANEL2)
        bar.pack(fill="x", side="bottom", padx=14, pady=(0, 8))
        self.progress = ttk.Progressbar(bar, mode="determinate",
                                        maximum=100, length=260)
        self.progress.pack(side="left", padx=(10, 10), pady=6)
        self.status = tk.Label(bar, text="Ready.", fg=MUT, bg=PANEL2,
                               font=FONT_SMALL, anchor="w")
        self.status.pack(side="left", fill="x", expand=True, pady=6)
        self.btn_cancel = ttk.Button(bar, text="Cancel", style="Danger.TButton",
                                     command=self._request_cancel, state="disabled")
        self.btn_cancel.pack(side="right", padx=8, pady=4)

    # ------------------------------------------------------------------ #
    # dashboard
    # ------------------------------------------------------------------ #
    def _build_dashboard(self) -> None:
        self.cards_row = tk.Frame(self.tab_dash, bg=BG)
        self.cards_row.pack(fill="x", pady=(14, 6))
        self.cards_sev = tk.Frame(self.cards_row, bg=BG)
        self.cards_sev.pack(side="left", fill="x", expand=True)

        split = tk.Frame(self.tab_dash, bg=BG)
        split.pack(fill="both", expand=True, pady=(4, 12))
        split.columnconfigure(0, weight=3)
        split.columnconfigure(1, weight=2)
        split.rowconfigure(0, weight=1)

        left = tk.Frame(split, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(left, text="TACTIC COVERAGE", font=FONT_BOLD, fg=CYAN, bg=BG).pack(anchor="w")
        self.tactic_box = tk.Frame(left, bg=PANEL)
        self.tactic_box.pack(fill="both", expand=True, pady=(6, 0))

        right = tk.Frame(split, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(right, text="TOP HOSTS / USERS", font=FONT_BOLD, fg=CYAN, bg=BG).pack(anchor="w")
        self.host_tree = ttk.Treeview(right, columns=("k", "n"), height=6, show="headings")
        self.host_tree.heading("k", text="Entity")
        self.host_tree.heading("n", text="Events")
        self.host_tree.column("k", width=200)
        self.host_tree.column("n", width=80, anchor="e")
        self.host_tree.pack(fill="x", pady=(6, 8))

    def _make_card(self, parent, label: str, value: str, color: str) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        card.pack(side="left", padx=4, fill="y", expand=True)
        tk.Label(card, text=label, font=FONT_SMALL, fg=MUT, bg=PANEL).pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(card, text=value, font=FONT_BIG, fg=color, bg=PANEL).pack(anchor="w", padx=10, pady=(0, 8))
        return card

    def _refresh_dashboard(self) -> None:
        for w in self.cards_sev.winfo_children():
            w.destroy()
        for w in self.tactic_box.winfo_children():
            w.destroy()
        for i in self.host_tree.get_children():
            self.host_tree.delete(i)
        if not self.result:
            self._make_card(self.cards_sev, "Events", "0", TXT)
            self._make_card(self.cards_sev, "Alerts", "0", TXT)
            self._make_card(self.cards_sev, "Hosts", "0", TXT)
            return
        r = self.result
        self._make_card(self.cards_sev, "Events", f"{len(r.events):,}", TXT)
        self._make_card(self.cards_sev, "Critical", f"{r.by_severity(Severity.CRITICAL)}", RED)
        self._make_card(self.cards_sev, "High", f"{r.by_severity(Severity.HIGH)}", ORANGE)
        self._make_card(self.cards_sev, "Medium", f"{r.by_severity(Severity.MEDIUM)}", AMBER)
        self._make_card(self.cards_sev, "Low", f"{r.by_severity(Severity.LOW)}", GREEN)
        self._make_card(self.cards_sev, "Chains", f"{len(r.chains)}", CYAN)
        self._make_card(self.cards_sev, "Span", self._span_txt(r), MUT)

        from collections import Counter
        tc = Counter(a.tactic for a in r.alerts)
        mx = max(tc.values(), default=1)
        for tactic, cnt in tc.most_common(8):
            row = tk.Frame(self.tactic_box, bg=PANEL)
            row.pack(fill="x", padx=8, pady=4)
            tk.Label(row, text=f"{tactic}", font=FONT_SMALL, fg=TXT, bg=PANEL,
                     width=22, anchor="w").pack(side="left")
            tr = tk.Frame(row, bg=PANEL2, height=12, width=160)
            tr.pack(side="left", pady=2)
            tr.pack_propagate(False)
            fill = tk.Frame(tr, bg=ACC, width=int(160 * cnt / mx))
            fill.pack(side="left", fill="y")
            tk.Label(row, text=str(cnt), font=FONT_SMALL, fg=MUT, bg=PANEL,
                     width=4).pack(side="left")
        if not tc:
            tk.Label(self.tactic_box, text="No detections.", font=FONT_SMALL,
                     fg=MUT, bg=PANEL).pack(pady=16)

        from collections import Counter as _C
        counts = _C(e.subject_user or e.target_user or "?" for e in r.events
                    if e.subject_user or e.target_user)
        for name, n in counts.most_common(8):
            self.host_tree.insert("", "end", values=(name, n))

    def _span_txt(self, r: AnalysisResult) -> str:
        if not r.events:
            return "0s"
        span = r.chrono[-1].timestamp - r.chrono[0].timestamp
        s = int(span.total_seconds())
        d, rem = divmod(s, 86400)
        h, rem = divmod(rem, 3600)
        return f"{d}d {h}h" if d else f"{h}h {int(rem/60)}m"

    # ------------------------------------------------------------------ #
    # timeline tab
    # ------------------------------------------------------------------ #
    def _build_timeline(self) -> None:
        top = tk.Frame(self.tab_tl, bg=BG)
        top.pack(fill="x", pady=(12, 6))
        tk.Label(top, text="Phase filter: ", font=FONT_SMALL, fg=MUT, bg=BG).pack(side="left")
        cb = ttk.Combobox(top, state="readonly", width=26)
        cb["values"] = ["All phases"] + [p.value for p in Phase]
        cb.current(0)
        cb.pack(side="left", padx=(0, 16))
        tk.Label(top, text="Severity: ", font=FONT_SMALL, fg=MUT, bg=BG).pack(side="left")
        cs = ttk.Combobox(top, state="readonly", width=14)
        cs["values"] = ["All", "Critical", "High", "Medium", "Low"]
        cs.current(0)
        cs.pack(side="left")
        self.tl_filter = (cb, cs)
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_timeline())
        cs.bind("<<ComboboxSelected>>", lambda e: self._refresh_timeline())

        wrap = tk.Frame(self.tab_tl, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(4, 10))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        scr = ttk.Scrollbar(wrap, orient="vertical")
        scr.grid(row=0, column=1, sticky="ns")
        self.tl_tree = ttk.Treeview(wrap, columns=("t", "sev", "ph", "id", "desc"),
                                    show="headings", yscrollcommand=scr.set)
        for c, t, wd in (("t", "Time (local)", 150), ("sev", "Severity", 90),
                         ("ph", "Phase", 130), ("id", "Event", 70),
                         ("desc", "Detail", 620)):
            self.tl_tree.heading(c, text=t)
            self.tl_tree.column(c, width=wd, anchor="w", stretch=(c == "desc"))
        self.tl_tree.grid(row=0, column=0, sticky="nsew")
        scr.config(command=self.tl_tree.yview)
        self.tl_tree.tag_configure("phasebar", background="#f1f5fb")

    def _refresh_timeline(self) -> None:
        for i in self.tl_tree.get_children():
            self.tl_tree.delete(i)
        if not self.result:
            return
        f_phase = self.tl_filter[0].get()
        f_sev = self.tl_filter[1].get()
        sev_map = {"Critical": Severity.CRITICAL, "High": Severity.HIGH,
                   "Medium": Severity.MEDIUM, "Low": Severity.LOW}
        for e in self.result.chrono[:4000]:
            if f_phase != "All phases" and e.phase.value != f_phase:
                continue
            top = _max_sev(e, self.result.alerts)
            if f_sev != "All" and top < sev_map[f_sev]:
                continue
            self.tl_tree.insert("", "end",
                                tags=("phasebar", top.name.lower()),
                                values=(_fmt(e.time_local()),
                                        top.label if top > Severity.INFO else "-",
                                        e.phase.value, e.event_id,
                                        e.summary()[:140]))

    # ------------------------------------------------------------------ #
    # alerts tab
    # ------------------------------------------------------------------ #
    def _build_alerts(self) -> None:
        top = tk.Frame(self.tab_alerts, bg=BG)
        top.pack(fill="x", pady=(12, 6))
        ttk.Button(top, text="View selected events", style="Side.TButton",
                   command=self._view_alert_events).pack(side="left")
        ttk.Button(top, text="Export alerts as report", style="Side.TButton",
                   command=self.export_report).pack(side="left", padx=8)
        wrap = tk.Frame(self.tab_alerts, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(4, 10))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        scr = ttk.Scrollbar(wrap, orient="vertical")
        scr.grid(row=0, column=1, sticky="ns")
        self.alert_tree = ttk.Treeview(wrap,
                                       columns=("sev", "rule", "name", "tactic",
                                                "key", "n", "when"),
                                       show="headings", yscrollcommand=scr.set)
        for c, t, wd in (("sev", "Sev", 90), ("rule", "Rule", 110),
                         ("name", "Detection", 260), ("tactic", "Tactic", 150),
                         ("key", "Key", 160), ("n", "#Ev", 50), ("when", "First seen", 150)):
            self.alert_tree.heading(c, text=t)
            self.alert_tree.column(c, width=wd, anchor="w", stretch=(c == "name"))
        self.alert_tree.grid(row=0, column=0, sticky="nsew")
        scr.config(command=self.alert_tree.yview)

    def _refresh_alerts(self) -> None:
        for i in self.alert_tree.get_children():
            self.alert_tree.delete(i)
        if not self.result:
            return
        for a in self.result.alerts:
            k = ""
            if a.events:
                k = a.events[0].source_ip or a.events[0].subject_user or "-"
            self.alert_tree.insert(
                "", "end", tags=(a.severity.name.lower(),),
                values=(a.severity.label, a.rule_id, a.name, a.tactic, k,
                        len(a.events), _fmt_t(a.start) if a.start else "-"))

    def _view_alert_events(self) -> None:
        if not self.result:
            return
        sel = self.alert_tree.selection()
        if not sel:
            messagebox.showinfo("Select an alert", "Select an alert row first.",
                                parent=self)
            return
        idx = self.alert_tree.index(sel[0])
        alert = self.result.alerts[idx]
        win = tk.Toplevel(self)
        win.title(f"Alert {alert.rule_id} — {alert.name}")
        win.configure(bg=BG)
        win.geometry("820x420")
        wrap = tk.Frame(win, bg=BG)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        wrap.rowconfigure(1, weight=1)
        wrap.columnconfigure(0, weight=1)
        tk.Label(wrap, text=f"{alert.description}", font=FONT_SMALL, fg=MUT,
                 bg=BG, justify="left").grid(row=0, column=0, sticky="w", pady=(0, 6))
        scr = ttk.Scrollbar(wrap, orient="both")
        scr.grid(row=1, column=1, sticky="nsew")
        tv = ttk.Treeview(wrap, columns=("t", "id", "ch", "detail"), show="headings",
                          yscrollcommand=scr.set)
        scr.config(command=tv.yview)
        tv.heading("t", text="Time")
        tv.heading("id", text="ID")
        tv.heading("ch", text="Channel")
        tv.heading("detail", text="Summary")
        tv.column("t", width=150)
        tv.column("id", width=60)
        tv.column("ch", width=80, stretch=False)
        tv.column("detail", width=420)
        tv.grid(row=1, column=0, sticky="nsew")
        for e in alert.events:
            tv.insert("", "end", values=(_fmt(e.time_local()), e.event_id,
                                         e.channel, e.summary()[:220]))

    # ------------------------------------------------------------------ #
    # events tab
    # ------------------------------------------------------------------ #
    def _build_events(self) -> None:
        top = tk.Frame(self.tab_events, bg=BG)
        top.pack(fill="x", pady=(12, 6))
        tk.Label(top, text="Filter (EventID / keyword): ", font=FONT_SMALL,
                 fg=MUT, bg=BG).pack(side="left")
        self.filter_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.filter_var, width=30)
        ent.pack(side="left", padx=(0, 10))
        ent.bind("<Return>", lambda e: self._refresh_events())
        ttk.Button(top, text="Apply", style="Side.TButton",
                   command=self._refresh_events).pack(side="left")

        wrap = tk.Frame(self.tab_events, bg=BG)
        wrap.pack(fill="both", expand=True, pady=(4, 10))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        scrv = ttk.Scrollbar(wrap, orient="vertical")
        scrh = ttk.Scrollbar(wrap, orient="horizontal")
        scrv.grid(row=0, column=1, sticky="ns")
        scrh.grid(row=1, column=0, sticky="ew")
        self.event_tree = ttk.Treeview(wrap,
                                       columns=("t", "id", "ch", "user",
                                                "src", "detail"),
                                       show="headings",
                                       yscrollcommand=scrv.set,
                                       xscrollcommand=scrh.set)
        for c, t, wd in (("t", "Time", 150), ("id", "ID", 60), ("ch", "Channel", 90),
                         ("user", "User", 120), ("src", "Source", 120),
                         ("detail", "Detail", 560)):
            self.event_tree.heading(c, text=t)
            self.event_tree.column(c, width=wd, anchor="w", stretch=(c == "detail"))
        self.event_tree.grid(row=0, column=0, sticky="nsew")
        scrv.config(command=self.event_tree.yview)
        scrh.config(command=self.event_tree.xview)

    def _refresh_events(self) -> None:
        for i in self.event_tree.get_children():
            self.event_tree.delete(i)
        if not self.current_events:
            return
        pool = self.result.chrono if (self.result and self.result.chrono) \
            else sorted(self.current_events, key=lambda e: e.timestamp)
        f = self.filter_var.get().strip().lower()
        for e in pool[:12000]:
            sev = _max_sev(e, self.result.alerts) if self.result else Severity.INFO
            if f:
                if f.isdigit():
                    if str(e.event_id) != f:
                        continue
                elif not (f in e.channel.lower() or f in (e.subject_user or "").lower()
                          or f in e.summary().lower()):
                    continue
            tag = sev.name.lower() if sev > Severity.INFO else "info"
            self.event_tree.insert("", "end", tags=(tag,),
                                   values=(_fmt(e.time_local()), e.event_id,
                                           e.channel, e.subject_user or "-",
                                           e.source_ip or "-", e.summary()[:150]))

    # ------------------------------------------------------------------ #
    # ingest
    # ------------------------------------------------------------------ #
    def _ask_live(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Load Live Windows Event Logs")
        dialog.configure(bg=BG)
        dialog.grab_set()
        dialog.transient(self)
        dialog.geometry("560x520")

        tk.Label(dialog, text="Channels", font=FONT_BOLD, fg=CYAN, bg=BG).pack(anchor="w", padx=16, pady=(14, 4))
        ch_frame = tk.Frame(dialog, bg=BG)
        ch_frame.pack(fill="x", padx=16)
        vars_ = {}
        for i, ch in enumerate(LIVE_CHANNELS[:7]):
            var = tk.BooleanVar(value=(ch in ("Security", "System", "Application")))
            vars_[ch] = var
            cb = tk.Checkbutton(ch_frame, text=ch, variable=var, bg=BG, fg=TXT,
                                selectcolor=PANEL2, activebackground=BG,
                                activeforeground=TXT, anchor="w", font=FONT_SMALL)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=2)
        tk.Label(dialog, text="Custom channel (optional):", font=FONT_SMALL, fg=MUT,
                 bg=BG).pack(anchor="w", padx=16, pady=(8, 0))
        custom = tk.Entry(dialog, bg=PANEL, fg=TXT, insertbackground=TXT, width=50)
        custom.pack(anchor="w", padx=16, pady=2)

        tk.Label(dialog, text="Time window", font=FONT_BOLD, fg=CYAN, bg=BG).pack(anchor="w", padx=16, pady=(16, 4))
        win_var = tk.StringVar(value="86400")
        for label, secs in TIME_CHOICES:
            tk.Radiobutton(dialog, text=label, value=str(secs), variable=win_var,
                           bg=BG, fg=TXT, selectcolor=PANEL2, activebackground=BG,
                           activeforeground=TXT, font=FONT_SMALL).pack(anchor="w", padx=24)

        tk.Label(dialog, text="Max events per channel:", font=FONT_SMALL, fg=MUT,
                 bg=BG).pack(anchor="w", padx=16, pady=(14, 0))
        maxvar = tk.StringVar(value="200000")
        tk.Entry(dialog, textvariable=maxvar, bg=PANEL, fg=TXT, insertbackground=TXT, width=14).pack(anchor="w", padx=16)

        bar = tk.Frame(dialog, bg=BG)
        bar.pack(fill="x", side="bottom", padx=16, pady=14)

        def ok():
            channels = [ch for ch, v in vars_.items() if v.get()]
            cch = custom.get().strip()
            if cch:
                channels.append(cch)
            if not channels:
                messagebox.showwarning("No channels", "Select at least one channel.",
                                       parent=dialog)
                return
            secs = int(win_var.get()) if win_var.get() not in ("None", "none") else None
            try:
                mx = int(maxvar.get() or 200000)
            except ValueError:
                mx = 200000
            dialog.destroy()
            self._load_live(channels, secs, mx)

        ttk.Button(bar, text="Start", style="Accent.TButton", command=ok).pack(side="right")
        ttk.Button(bar, text="Cancel", style="Danger.TButton",
                   command=dialog.destroy).pack(side="right", padx=8)

    def _ask_evtx(self) -> None:
        files = filedialog.askopenfilenames(
            parent=self, title="Select .evtx event log files",
            filetypes=[("Windows Event Log", "*.evtx"), ("All files", "*.*")])
        if files:
            self._load_evtx(list(files))

    def _load_live(self, channels: List[str], secs: Optional[int], max_events: int) -> None:
        end = None
        start = datetime.now() - timedelta(seconds=secs) if secs else None
        self._run_ingest(channels, start, end, max_events)

    def _load_evtx(self, files: List[str]) -> None:
        self._run_ingest(files, None, None, 1000000)

    def _run_ingest(self, targets: List[str], start, end, max_events) -> None:
        if self._busy:
            messagebox.showinfo("Busy", "Wait for the current operation to finish.",
                                parent=self)
            return
        self._busy = True
        self._cancel = False
        self.btn_cancel.config(state="normal")
        self.set_status(f"Ingesting {len(targets)} log source(s)…")
        self.set_progress(0, mode="indeterminate")
        self.progress.start(8)

        def work():
            all_events = []
            errors = []
            try:
                for i, tgt in enumerate(targets):
                    if self._cancel:
                        raise ParseCanceled("Canceled by user")
                    def prog(done, total):
                        self.update_progress(done, max(1, total),
                                             f"parsing {os.path.basename(str(tgt))}")
                    try:
                        evs, err = events_from_wevtutil(
                            tgt, max_events=max_events, start=start, end=end,
                            progress=prog, cancel_check=lambda: self._cancel)
                    except ParseCanceled:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{tgt}: {exc}")
                        continue
                    if err:
                        errors.append(f"{tgt}: {err}")
                        continue
                    all_events.extend(evs)
                    self.update_progress(i + 1, max(1, len(targets)),
                                         f"{len(evs):,} events from {os.path.basename(str(tgt))}")
                all_events.sort(key=lambda e: e.timestamp)
            except ParseCanceled:
                all_events = self.current_events
            except Exception as exc:  # noqa: BLE001
                errors.append(f"internal: {exc}")
            self.current_events = all_events
            self.result = None
            self.sources = [str(t) for t in targets]
            self._push(lambda: self._ingest_done(self.current_events, errors))

        self._spawn(work)

    def _ingest_done(self, events, errors) -> None:
        self.progress.stop()
        self._busy = False
        self.btn_cancel.config(state="disabled")
        self.set_progress(0)
        self.current_events = events
        self.sources = list(self.sources)
        self.pill_events.config(text=f"events: {len(events):,}")
        self.side_info.config(text=f"Loaded:\n{len(events):,} events\n"
                                   f"from {len(self.sources)} source(s)\n"
                                   f"\nRun Analyze to correlate.")
        self._refresh_events()
        if self.result:
            self._populate_result(self.result)
        if errors:
            msg = "\n".join(errors[:5])
            messagebox.showwarning("Partial load", f"Some sources produced warnings:\n{msg}",
                                   parent=self)
        if not events:
            self.set_status("No events parsed.")
            messagebox.showinfo("No events",
                                "No events were parsed. Verify channels/paths and permissions.",
                                parent=self)
            return
        self.set_status(f"Loaded {len(events):,} events. Press Analyze to correlate.")

    # ------------------------------------------------------------------ #
    # analysis
    # ------------------------------------------------------------------ #
    def start_analysis(self) -> None:
        if self._busy:
            return
        if not self.current_events:
            messagebox.showwarning("No data", "Load event logs first (live or EVTX).",
                                   parent=self)
            return
        self._busy = True
        self._cancel = False
        self.btn_cancel.config(state="normal")
        self.set_status(f"Running {len(self.current_events):,} events through rules…")
        self.set_progress(0)

        def work():
            corr = Correlator(self.current_events)
            def prog(done, total):
                pct = int(done / total * 100)
                self._push(lambda: self.set_progress(pct, "determinate"))
                self._push(lambda: self.set_status(f"rule {done}/{total}"))
            try:
                result = corr.run(progress=prog, cancel_check=lambda: self._cancel)
            except ParseCanceled:
                result = None
            except Exception:  # noqa: BLE001
                result = None
            self._push(lambda: self._analysis_done(result))

        self._spawn(work)

    def _analysis_done(self, result: Optional[AnalysisResult]) -> None:
        self._busy = False
        self.btn_cancel.config(state="disabled")
        if result is None:
            self.set_status("Analysis canceled.")
            return
        self.result = result
        self.pill_alerts.config(text=f"alerts: {len(result.alerts)}")
        self.pill_phase.config(text=f"phases: {len({e.phase for e in result.events})}")
        self._populate_result(result)
        self.set_status(
            f"Analysis complete: {len(result.alerts)} alerts, "
            f"{len(result.chains)} incident chains.")
        self.set_progress(0)

    def _populate_result(self, r: AnalysisResult) -> None:
        self._refresh_dashboard()
        self._refresh_timeline()
        self._refresh_alerts()
        self._refresh_events()
        self.side_info.config(text=f"Analyzed {len(r.events):,} events\n"
                                   f"{len(r.alerts)} alerts · {len(r.chains)} chains")

    # ------------------------------------------------------------------ #
    # export
    # ------------------------------------------------------------------ #
    def export_report(self) -> None:
        if not self.current_events:
            messagebox.showwarning("No data", "Load events before exporting.", parent=self)
            return
        if self.result is None:
            yes = messagebox.askyesno("Analyze first?",
                                      "No analysis yet. Run the correlation engine "
                                      "before exporting (recommended). Export anyway?",
                                      parent=self)
            if not yes:
                return
            r = AnalysisResult(self.current_events, [], [], sorted(self.current_events,
                                                                   key=lambda e: e.timestamp))
        else:
            r = self.result
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".html",
            filetypes=[("HTML report", "*.html")],
            initialfile="intrusion_timeline_report.html")
        if not path:
            return
        try:
            html = build_report(r, sources=self.sources, title="Intrusion Timeline — Analysis Report")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export failed", str(exc), parent=self)
            return
        self.set_status(f"Report saved: {path}")
        if messagebox.askyesno("Report saved", f"Saved to:\n{path}\n\nOpen it now?",
                               parent=self):
            os.startfile(path)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def clear_all(self) -> None:
        if self._busy:
            return
        self.current_events = []
        self.result = None
        self.sources = []
        for tree in (self.event_tree, self.tl_tree, self.alert_tree):
            for i in tree.get_children():
                tree.delete(i)
        for w in self.cards_sev.winfo_children():
            w.destroy()
        for w in self.tactic_box.winfo_children():
            w.destroy()
        for i in self.host_tree.get_children():
            self.host_tree.delete(i)
        self.pill_events.config(text="events: 0")
        self.pill_alerts.config(text="alerts: 0")
        self.pill_phase.config(text="phases: -")
        self.side_info.config(text="No data loaded.")
        self.set_status("Cleared.")

    def _request_cancel(self) -> None:
        self._cancel = True
        self.set_status("Canceling…")
        if self.progress.cget("mode") == "indeterminate":
            self.progress.stop()

    # ------------------------------------------------------------------ #
    # thread-safe UI updates (workers post callables to a queue)
    # ------------------------------------------------------------------ #
    def _push(self, fn) -> None:
        """Called from any thread; runs fn on the main thread."""
        try:
            self._msgq.put_nowait(fn)
        except queue.Full:
            pass

    def _poll_msgq(self) -> None:
        try:
            while True:
                fn = self._msgq.get_nowait()
                try:
                    fn()
                except Exception:  # noqa: BLE001
                    pass
        except queue.Empty:
            pass
        self.after(100, self._poll_msgq)

    def _spawn(self, fn) -> None:
        self._worker = threading.Thread(target=fn, daemon=True)
        self._worker.start()

    def set_status(self, text: str) -> None:
        self.status.config(text=text)

    def set_progress(self, value: int, mode: str = "determinate") -> None:
        self.progress.config(mode=mode)
        if mode == "determinate":
            self.progress["value"] = value

    def update_progress(self, done: int, total: int, note: str) -> None:
        if total > 0:
            pct = int(done / total * 100)
            self._push(lambda: self.set_progress(pct, "determinate"))
        self._push(lambda: self.set_status(note))


def _max_sev(e: EventRecord, alerts: List[Alert]) -> Severity:
    top = Severity.INFO
    for a in alerts:
        if e in a.events and a.severity > top:
            top = a.severity
    return top


def launch() -> None:
    app = App()
    app.mainloop()