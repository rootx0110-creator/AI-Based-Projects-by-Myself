import time

import customtkinter as ctk
from tkinter import filedialog

from ..alerts import SEVERITIES
from ..reporter import build_csv_rows
from .theme import ACCENT, BG, CRIT, MUTED, OK, TEXT, FONT_FAMILY
from .widgets import build_btn, build_label, card, clear_tree, make_scrollbar, make_tree

_SEV_ORDER = {"All": 1, "Info": 1, "Warning": 2, "Critical": 3}


class AlertsView(ctk.CTkFrame):
    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self.sev_filter = "All"
        self.src_filter = "All"
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        build_label(header, "Alert Log", size=22, weight="bold").pack(side="left")

        body = card(self, title="Security Events")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=8)

        self.sev_menu = ctk.CTkComboBox(
            bar, values=["All", "Critical", "Warning", "Info"], width=120, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly",
            command=self._on_sev)
        self.sev_menu.set("All")
        self.sev_menu.pack(side="left")

        self.src_menu = ctk.CTkComboBox(
            bar, values=["All", "fim", "process", "agent"], width=120, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly",
            command=self._on_src)
        self.src_menu.set("All")
        self.src_menu.pack(side="left", padx=8)

        self.alert_count = build_label(bar, "", size=12, color=MUTED)
        self.alert_count.pack(side="left", padx=12)

        build_btn(bar, "Export CSV", self._export_csv).pack(side="right")
        build_btn(bar, "Clear Log", self._clear).pack(side="right", padx=0)
        build_btn(bar, "Acknowledge Selected", self._ack_sel, primary=True).pack(side="right",
                                                                                 padx=6)

        self.tree = make_tree(body, ["time", "severity", "source", "status", "title", "detail"],
                              [130, 80, 80, 80, 240, 600], height=16)
        make_scrollbar(body, self.tree)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", lambda e: self._ack_sel())

    def _on_sev(self, value):
        self.sev_filter = value
        self.refresh()

    def _on_src(self, value):
        self.src_filter = value
        self.refresh()

    def _sev_min(self):
        return _SEV_ORDER[self.sev_filter]

    def _source(self):
        s = self.src_filter
        return None if s == "All" else s

    def _rows(self):
        try:
            return self.agent.storage.alerts(min_severity=self._sev_min(),
                                             source=self._source(), limit=10000)
        except Exception:
            return []

    def _ack_sel(self):
        for item in self.tree.selection():
            try:
                self.agent.storage.ack_alert(int(item))
            except (ValueError, TypeError):
                continue
        self.refresh()

    def _clear(self):
        self.agent.storage.clear_alerts(self._source())
        self.refresh()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export alert log",
            defaultextension=".csv",
            initialfile="hids-alert-log.csv",
            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        try:
            import csv as _csv
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                _csv.writer(fh).writerows(build_csv_rows(self._rows()))
            self.alert_count.configure(text=f"Exported -> {path}", text_color=OK)
        except Exception as exc:
            self.alert_count.configure(text=f"Export failed: {exc}", text_color=CRIT)

    def refresh(self):
        rows = self._rows()
        clear_tree(self.tree)
        for r in rows:
            label = SEVERITIES.get(r["severity"], str(r["severity"]))
            self.tree.insert("", str(r["id"]), values=(
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
                label,
                r["source"],
                "" if r["status"] == "open" else "acked",
                r["title"],
                r["detail"] or "",
            ), tags=(f"sev_{r['severity']}",))
        self.alert_count.configure(text=f"{len(rows)} events shown")