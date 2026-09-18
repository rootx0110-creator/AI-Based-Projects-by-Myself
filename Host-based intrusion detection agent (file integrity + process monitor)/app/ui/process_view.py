import time

import customtkinter as ctk

from .theme import ACCENT, BG, CRIT, MUTED, OK, TEXT, WARN, FONT_FAMILY
from .widgets import build_btn, build_label, card, clear_tree, entry, make_scrollbar, make_tree


class ProcessView(ctk.CTkFrame):
    SNAP_EVERY = 4

    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self._cached = []
        self._last_snap = 0.0
        self._build()
        self.refresh(force=True)

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        build_label(header, "Process Monitor", size=22, weight="bold").pack(side="left")
        self.new_badge = ctk.CTkLabel(header, text="", corner_radius=10, fg_color=CRIT,
                                      text_color="#ffffff", font=(FONT_FAMILY, 11, "bold"),
                                      padx=8, pady=2)
        self.new_badge.pack(side="left", padx=12, pady=8)
        self.last_snap = build_label(header, "no snapshot yet", size=12, color=MUTED)
        self.last_snap.pack(side="right", pady=8)

        body = card(self, title="Running Processes")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=8)
        self.search = entry(bar, placeholder="Filter by name / pid / user...")
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda e: self.refresh(force=True))
        self.proc_count = build_label(bar, "", size=12, color=MUTED)
        self.proc_count.pack(side="left", padx=12)
        build_btn(bar, "Snapshot Now", self.agent.request_proc_snapshot, primary=True).pack(
            side="right")
        build_btn(bar, "Refresh View", lambda: self.refresh(force=True)).pack(side="right",
                                                                              padx=6)
        build_btn(bar, "Update Whitelist", self._rebuild_whitelist).pack(side="right", padx=6)

        self.tree = make_tree(body, ["pid", "name", "user", "cpu", "mem_mb", "status",
                                     "started", "exe"],
                              [60, 160, 150, 60, 80, 60, 130, 480], height=16)
        make_scrollbar(body, self.tree)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _rebuild_whitelist(self):
        rows = self.agent.procs.snapshot()
        self.agent.procs.update_whitelist(rows)
        self.agent.reset_process_state()
        self._flash("Whitelist rebuilt")

    def _flash(self, msg):
        self.last_snap.configure(text=msg, text_color=OK)

    def refresh(self, force=False):
        now = time.time()
        if force or (now - self._last_snap) >= self.SNAP_EVERY:
            self._last_snap = now
            try:
                self._cached = self.agent.procs.snapshot()
            except Exception:
                pass

        query = self.search.get().strip().lower()
        rows = self._cached

        filter_rows = [r for r in rows if not query or
                       query in r["name"].lower() or query in str(r["pid"]) or
                       query in r["user"].lower()]
        clear_tree(self.tree)
        for r in filter_rows:
            self.tree.insert("", "end", values=(
                r["pid"], r["name"], r["user"], f'{r["cpu"]:.1f}',
                f'{r["mem_mb"]:.1f}', r["status"], r["started"], r["exe"]))
        self.proc_count.configure(text=f"{len(filter_rows)} of {len(rows)} processes")

        last = self.agent.last_snapshot["time"]
        if last:
            self.last_snap.configure(
                text="Snapshot " + time.strftime("%H:%M:%S", time.localtime(last)) +
                     f"  ({self.agent.last_snapshot['count']} processes)",
                text_color=MUTED)

        new = self.agent.last_snapshot.get("new", 0)
        if new:
            self.new_badge.configure(text=f"  {new} NEW  ")
        else:
            self.new_badge.configure(text="")