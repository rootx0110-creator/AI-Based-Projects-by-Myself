import time

import customtkinter as ctk

from .theme import ACCENT, BG, CRIT, MUTED, OK, PANEL, TEXT, WARN, INFO, FONT_FAMILY
from .widgets import build_btn, build_label, card, clear_tree, make_scrollbar, make_tree, stat_card


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self._build()
        self._refresh_tick()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 6))
        build_label(header, "Dashboard", size=22, weight="bold").pack(side="left")
        self.status_pill = ctk.CTkLabel(
            header, text="", corner_radius=12, fg_color="#1f6feb",
            text_color="#ffffff", font=(FONT_FAMILY, 11, "bold"), padx=10, pady=3)
        self.status_pill.pack(side="right", pady=8)

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=20, pady=6)
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1)
        self.dirs_card = stat_card(stats, "Watched Directories", "-")
        self.dirs_card.grid(row=0, column=0, sticky="nsew", padx=4)
        self.files_card = stat_card(stats, "Files Under Monitor", "-")
        self.files_card.grid(row=0, column=1, sticky="nsew", padx=4)
        self.procs_card = stat_card(stats, "Running Processes", "-")
        self.procs_card.grid(row=0, column=2, sticky="nsew", padx=4)
        self.alert_card = stat_card(stats, "Open Alerts", "-", accent=CRIT)
        self.alert_card.grid(row=0, column=3, sticky="nsew", padx=4)

        # severity chips
        chips = ctk.CTkFrame(self, fg_color="transparent")
        chips.pack(fill="x", padx=20, pady=(0, 4))
        self.chips_frame = chips
        labels = [(INFO, "Info"), (WARN, "Warning"), (CRIT, "Critical")]
        for i, (color, name) in enumerate(labels):
            pill = ctk.CTkLabel(chips, text=f"{name}: 0 open", corner_radius=10,
                                fg_color="#161b22", border_width=1, border_color=color,
                                text_color=color, font=(FONT_FAMILY, 11, "bold"),
                                padx=12, pady=3)
            pill.grid(row=0, column=i, padx=(0, 8) if i < 2 else 0, pady=2, sticky="w")

        right = ctk.CTkFrame(self, fg_color=BG)
        right.pack(fill="both", expand=True, padx=16, pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)
        right.grid_rowconfigure(0, weight=4)
        right.grid_rowconfigure(1, weight=0)

        # left column
        self.activity = card(right, title="Recent Alerts", accent=CRIT)
        self.activity.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.alert_tree = make_tree(self.activity, ["time", "severity", "source", "title"],
                                    [80, 80, 90, 560], height=14)
        make_scrollbar(self.activity, self.alert_tree)
        self.alert_tree.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        # right column
        scanner = card(right, title="Scanner Activity")
        scanner.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.scan_state = build_label(scanner, "Idle", size=13)
        self.scan_state.pack(anchor="w", padx=14, pady=(6, 2))
        self.progress = ctk.CTkProgressBar(scanner, width=320, height=8, corner_radius=4,
                                           progress_color=OK, fg_color=PANEL)
        self.progress.set(0)
        self.progress.pack(anchor="w", padx=14, pady=(4, 2))
        self.scan_detail = build_label(scanner, "", size=11, color=MUTED)
        self.scan_detail.pack(anchor="w", padx=14, pady=(0, 4))

        timers = card(right, title="Last Activity")
        timers.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        self.fim_time = build_label(timers, "Last FIM scan: -")
        self.fim_time.pack(anchor="w", padx=14, pady=(4, 0))
        self.proc_time = build_label(timers, "Last process snapshot: -")
        self.proc_time.pack(anchor="w", padx=14, pady=(2, 0))

        actions = card(right, title="Quick Actions")
        actions.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)
        build_btn(row, "Scan Files Now", self.agent.request_fim_scan, primary=True).pack(
            side="left", padx=(0, 6))
        build_btn(row, "Snapshot Processes", self.agent.request_proc_snapshot).pack(side="left",
                                                                                    padx=6)
        self.pause_btn = build_btn(row, "Pause Monitoring", self._toggle_pause)
        self.pause_btn.pack(side="left", padx=6)
        build_btn(row, "Open Reports", self._open_reports).pack(side="right")

    # ---------------- actions ----------------
    def _toggle_pause(self):
        self.agent.toggle_pause()
        self._set_pause_ui(self.agent.paused)
        self.status_pill.configure(
            text="  PAUSED  ", fg_color="#6e7681" if self.agent.paused else "")
        self._refresh_tick()

    def _set_pause_ui(self, paused):
        self.pause_btn.configure(text="Resume Monitoring" if paused else "Pause Monitoring",
                                 fg_color="#d29922" if paused else "#1c2330",
                                 hover_color="#b38a1e" if paused else "#232d40")

    def _open_reports(self):
        root = self.winfo_toplevel()
        from .app import HIDSUI
        if isinstance(root, HIDSUI):
            root._show("ReportsView")

    # ---------------- ui helpers ----------------
    def _set_card(self, frame, value, sub):
        labels = [c for c in frame.winfo_children() if isinstance(c, ctk.CTkLabel)]
        if len(labels) >= 3:
            labels[1].configure(text=str(value))
            labels[2].configure(text=sub)

    def _refresh_tick(self):
        agent = self.agent

        watch = agent.watch_dirs()
        files = 0
        for d in watch:
            try:
                files += agent.storage.baseline_file_count(d)
            except Exception:
                pass
        snap = agent.last_snapshot["count"]
        counts = agent.storage.alert_counts()
        open_alerts = sum(c["open"] for c in counts.values())

        self._set_card(self.dirs_card, len(watch), "protected paths")
        self._set_card(self.files_card, files, "baseline manifest")
        self._set_card(self.procs_card, snap, "process snapshot")
        self._set_card(self.alert_card, open_alerts,
                       f"{sum(c['n'] for c in counts.values())} total")

        self._update_chips(counts)

        # status pill
        on = (agent.config.get("fim_enabled", True) or agent.config.get("process_enabled", True))
        if agent.paused:
            self.status_pill.configure(text="  PAUSED  ", fg_color="#6e7681")
        elif on:
            self.status_pill.configure(text="  MONITORING  ", fg_color="#1f7a37")
        else:
            self.status_pill.configure(text="  MONITORING OFF  ", fg_color="#6e7681")

        self._set_pause_ui(agent.paused)

        # progress
        prog = agent.progress
        if prog["state"] == "idle":
            self.progress.set(1.0)
            self.scan_state.configure(text="Idle", text_color=MUTED)
            self.scan_detail.configure(text="Waiting for next scan cycle")
        else:
            self.progress.set(prog["processed"] / max(prog["total"], 1))
            self.scan_state.configure(
                text=("Building baseline..." if prog["state"] == "baseline" else "Scanning..."),
                text_color=ACCENT)
            self.scan_detail.configure(
                text=f"{prog['processed']} / {prog['total']}  {prog['label']}")

        # last activity
        ls = agent.last_scan["time"]
        lp = agent.last_snapshot["time"]
        self.fim_time.configure(
            text="Last FIM scan: " + (time.strftime("%H:%M:%S", time.localtime(ls)) if ls else "-"))
        self.proc_time.configure(
            text="Last process snapshot: " +
                 (time.strftime("%H:%M:%S", time.localtime(lp)) if lp else "-"))

        self.refresh_alerts()

    def _update_chips(self, counts):
        names = {1: "Info", 2: "Warning", 3: "Critical"}
        colors = {1: INFO, 2: WARN, 3: CRIT}
        # find labels on the chips frame
        chips_frame = self.chips_frame
        children = [c for c in chips_frame.winfo_children() if isinstance(c, ctk.CTkLabel)]
        for sev, label in zip((1, 2, 3), children):
            open_n = counts.get(sev, {}).get("open", 0)
            label.configure(text=f"{names[sev]}: {open_n} open",
                            text_color=colors[sev])

    def refresh_alerts(self):
        try:
            rows = self.agent.storage.alerts(min_severity=1, limit=12)
        except Exception:
            rows = []
        clear_tree(self.alert_tree)
        for r in rows:
            self.alert_tree.insert(
                "", "end",
                values=(time.strftime("%H:%M:%S", time.localtime(r["ts"])),
                        {1: "Info", 2: "Warning", 3: "Critical"}[r["severity"]],
                        r["source"], r["title"]),
                tags=(f"sev_{r['severity']}",))

    def refresh(self):
        self._refresh_tick()