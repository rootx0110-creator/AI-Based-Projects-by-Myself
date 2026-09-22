"""Rule Library: search, filter, inspect, export and manage pack rules."""
from __future__ import annotations

import os
from tkinter import filedialog

import customtkinter as ctk

from ..rules_core import STAGES, severity_bucket
from . import theme
from .table import attach_scrollbar, make_tree
from .widgets import Panel, make_button


class LibraryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)
        self._filters = {"stage": "__all__", "severity": "__all__",
                         "source": "__all__", "q": ""}
        self._build_top()
        self._build_table()
        self._build_detail()

    # ---------------------------------------------------------------- layout
    def _build_top(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for i in range(6):
            top.grid_columnconfigure(i, weight=1)

        self.search = ctk.CTkEntry(top, placeholder_text="Search id / description / mitre ...",
                                   fg_color=theme.PANEL, border_color=theme.LINE,
                                   font=theme.font(12), height=36)
        self.search.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        self.search.bind("<KeyRelease>", lambda _e: self._on_filter())

        stage_vals = ["__all__"] + [s["name"] for s in STAGES]
        self.stage_cb = self._combo(top, stage_vals, "__all__", 1)
        self.sev_cb = self._combo(top, ["__all__", "Low", "Medium", "High", "Critical"], "__all__", 2)
        source_vals = ["__all__", "apache_access", "windows_security", "sysmon",
                       "syscheck", "syslog", "audit", "custom"]
        self.source_cb = self._combo(top, source_vals, "__all__", 3)

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.grid(row=0, column=4, columnspan=2, sticky="e")
        make_button(actions, "Validate", self._validate, "ghost")\
            .pack(side="left", padx=(0, 6))
        make_button(actions, "Export XML", self._export_xml, "ghost")\
            .pack(side="left", padx=6)
        make_button(actions, "Export JSON", self._export_json, "ghost")\
            .pack(side="left", padx=(6, 0))

    def _combo(self, master, values, default, col):
        cb = ctk.CTkOptionMenu(
            master, values=values, command=lambda _v: self._on_filter(),
            fg_color=theme.PANEL, button_color=theme.PANEL2,
            button_hover_color=theme.PANEL3, text_color=theme.FG,
            dropdown_fg_color=theme.PANEL2, dropdown_hover_color=theme.ACCENT,
            font=theme.font(12), height=36, corner_radius=8)
        cb.set(default)
        cb.grid(row=0, column=col, sticky="ew", padx=8)
        return cb

    def _build_table(self):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        self.tree = make_tree(box, [
            ("id", "Rule ID", 86),
            ("level", "Lvl", 52),
            ("stage", "Stage", 110),
            ("mitre", "MITRE", 78),
            ("source", "Source", 100),
            ("desc", "Description", 300),
        ])
        self.tree.grid(row=0, column=0, sticky="nsew")
        attach_scrollbar(box, self.tree)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())

    def _build_detail(self):
        panel = Panel(self, "Rule detail")
        panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        body = panel.content
        body.grid_rowconfigure(4, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.d_rid = ctk.CTkLabel(body, text="", text_color=theme.ACCENT,
                                  font=theme.font(24, "bold"), anchor="w")
        self.d_rid.grid(row=0, column=0, sticky="ew", padx=18, pady=(8, 0))
        self.d_meta = ctk.CTkLabel(body, text="", text_color=theme.MUTED,
                                   font=theme.font(12), anchor="w")
        self.d_meta.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 4))
        self.d_desc = ctk.CTkLabel(body, text="", text_color=theme.FG,
                                   font=theme.font(12), anchor="w",
                                   wraplength=420)
        self.d_desc.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.d_xml = ctk.CTkTextbox(body, fg_color="#0a0e18",
                                    text_color="#c8f0d0",
                                    font=theme.mono(12), corner_radius=8,
                                    border_width=1, border_color=theme.LINE)
        self.d_xml.grid(row=3, column=0, sticky="nsew", padx=18, pady=(4, 8))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 14))
        self.btn_toggle = make_button(actions, "Disable", self._toggle, "ghost")
        self.btn_toggle.pack(side="left", padx=(0, 6))
        self.btn_report = make_button(actions, "Rule HTML report", self._single_report, "ghost")
        self.btn_report.pack(side="left", padx=6)
        self.btn_del = make_button(actions, "Delete", self._delete, "danger")
        self.btn_del.pack(side="left", padx=(6, 0))

    # ---------------------------------------------------------------- actions
    def refresh(self):
        self._on_filter()

    def _current(self):
        sel = self.tree.selection()
        if not sel:
            return None
        iid = int(self.tree.item(sel[0], "values")[0])
        return self.app.rulepack.get(iid)

    def _on_filter(self):
        self._filters["q"] = self.search.get().lower()
        stage = self.stage_cb.get()
        sev = self.sev_cb.get()
        src = self.source_cb.get()
        q = self._filters["q"]
        self.tree.delete(*self.tree.get_children())
        rules = sorted(self.app.rulepack.enabled(), key=lambda r: int(r["id"]))
        for idx, r in enumerate(rules):
            if stage != "__all__" and r.stage_name != stage:
                continue
            if sev != "__all__":
                b = severity_bucket(r.level)
                if not b or b["name"] != sev:
                    continue
            if src != "__all__" and r["log_source"] != src:
                continue
            if q and not any(
                    token in f"{r.rid} {r['description']} {r['mitre']} {r['group']}".lower()
                    for token in q.split()):
                continue
            tag = "occ" if idx % 2 == 0 else "alt"
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r.rid, r.level, r.stage_name,
                                     r["mitre"], r["log_source"], r["description"]),
                             tags=(tag,))
        self._on_select()

    def _on_select(self):
        r = self._current()
        if r is None:
            self.d_rid.configure(text="")
            self.d_meta.configure(text="")
            self.d_desc.configure(text="")
            self.d_xml.delete("1.0", "end")
            self.btn_toggle.configure(state="disabled")
            self.btn_report.configure(state="disabled")
            self.btn_del.configure(state="disabled")
            return
        b = severity_bucket(r.level)
        color = theme.severity_level_color(r.level)
        self.d_rid.configure(text=f"{r.rid}  (level {r.level})", text_color=color)
        self.d_meta.configure(text=(
            f"{r.stage_name}  \u2022  MITRE {r['mitre']}  \u2022  {r['log_source']}  \u2022  {r['group']}"
        ))
        self.d_desc.configure(text=r["description"])
        self.d_xml.delete("1.0", "end")
        self.d_xml.insert("1.0", r["xml"])
        enabled = r.get("enabled", True)
        self.btn_toggle.configure(text="Disable" if enabled else "Enable")
        self.btn_toggle.configure(state="normal")
        self.btn_report.configure(state="normal")
        self.btn_del.configure(state="normal" if r.get("created_by") == "builder" else "disabled")

    def _validate(self):
        issues = self.app.rulepack.validate()
        if issues:
            self.app.set_status(f"{len(issues)} issue(s) - {issues[0]}")
        else:
            self.app.set_status("Pack validation passed.")

    def _export_xml(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xml", initialfile="local_rules.xml",
            filetypes=[("XML rules", "*.xml")],
            initialdir=self.app.export_dir)
        if not path:
            return
        self.app.rulepack.export_xml(path)
        self.app.set_status(f"Exported {self.app.rulepack.total} rules to {path}")

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile="rulepack.json",
            filetypes=[("JSON pack", "*.json")],
            initialdir=self.app.export_dir)
        if not path:
            return
        self.app.rulepack.export_json(path)
        self.app.set_status(f"Pack saved to {path}")

    def _toggle(self):
        r = self._current()
        if not r:
            return
        r["enabled"] = not r.get("enabled", True)
        self.app.save_pack(f"{r.rid} {'enabled' if r['enabled'] else 'disabled'}.")
        self._on_filter()

    def _delete(self):
        r = self._current()
        if not r:
            return
        self.app.rulepack.remove(int(r["id"]))
        self.app.save_pack(f"Deleted rule {r.rid}.")
        self._on_filter()

    def _single_report(self):
        r = self._current()
        if not r:
            return
        from ..report import generate_single_rule_report
        dest = os.path.join(self.app.export_dir, f"rule_{r.rid}_report.html")
        with open(dest, "w", encoding="utf-8") as f:
            f.write(generate_single_rule_report(self.app.rulepack, int(r["id"])))
        self.app.open_report_in_browser(dest)
        self.app.set_status(f"Report written: {dest}")