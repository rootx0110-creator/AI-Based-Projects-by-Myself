"""Application window: sidebar navigation, view routing, pack lifecycle."""
from __future__ import annotations

import os
import threading
import webbrowser
from datetime import datetime

import customtkinter as ctk

from .. import rules_core as core
from ..rules_library import library_rules
from . import theme
from .dashboard import DashboardView
from .library import LibraryView
from .chain import ChainView
from .builder import BuilderView
from .reports import ReportsView

APP_TITLE = "Wazuh / OSSEC Detection Rule Pack Studio"
APP_VERSION = "1.0.0"


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  -  {APP_VERSION}")
        self.geometry("1380x860")
        self.minsize(1160, 720)
        self.configure(fg_color=theme.BG)

        self.pack_json, self.export_dir, self.xml_export = core.default_data_paths()
        self.rulepack = self._load_pack()

        self._view = None
        self._heading = None
        self._subtitle = None

        self._build_shell()
        self._navigate("dashboard")

    # ------------------------------------------------------------------ state
    def _load_pack(self):
        pack = None
        if os.path.exists(self.pack_json):
            try:
                pack = core.RulePack.load(self.pack_json)
            except Exception:
                pack = None
        if pack is None:
            pack = core.RulePack()
            pack.load_library(library_rules())
            pack.save(self.pack_json)
        return pack

    def save_pack(self, notify: str | None = None) -> None:
        self._save_pack()
        if notify:
            self.set_status(notify)
        self.refresh_all()

    def _save_pack(self, update_state_md: bool = True) -> None:
        self.rulepack.save(self.pack_json)
        if update_state_md:
            self._write_state_md()

    def _write_state_md(self) -> None:
        lines = [
            "# State - RulePackStudio",
            "# Field format: key = value",
            f"updated = {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"version = {APP_VERSION}",
            f"pack_name = {self.rulepack.name}",
            f"rule_count = {self.rulepack.total}",
            f"stages_covered = {self.rulepack.stages_covered}",
            "data_dir = " + os.path.dirname(self.pack_json),
            "export_dir = " + self.export_dir,
            "xml_export = " + self.xml_export,
        ]
        try:
            with open(os.path.join(os.path.dirname(self.pack_json), "..", "state.md"),
                      "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError:
            pass

    # ---------------------------------------------------------------- shell
    def _build_shell(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # sidebar
        side = ctk.CTkFrame(self, width=232, fg_color=theme.PANEL,
                            corner_radius=0)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        side.grid_rowconfigure(10, weight=1)

        logo_box = ctk.CTkFrame(side, fg_color="transparent")
        logo_box.pack(fill="x", padx=18, pady=(22, 4))
        badge = ctk.CTkLabel(
            logo_box, text="RPS", text_color="#0b0f19",
            font=theme.font(20, "bold"), width=46, height=46, corner_radius=12,
            fg_color=theme.ACCENT)
        badge.pack(side="left")
        ctk.CTkLabel(
            logo_box, text="RULE PACK\nSTUDIO",
            text_color=theme.FG, font=theme.font(15, "bold"),
            justify="left").pack(side="left", padx=(12, 0))

        ctk.CTkLabel(side, text="WAZUH / OSSEC",
                     text_color=theme.MUTED, font=theme.font(10, "bold"),
                     anchor="w").pack(fill="x", padx=22)
        ctk.CTkLabel(side, text="Detection Rule Pack Studio",
                     text_color=theme.MUTED, font=theme.font(10),
                     anchor="w").pack(fill="x", padx=22, pady=(0, 14))

        self._nav_buttons = {}
        for i, (key, label) in enumerate(theme.NAV):
            btn = ctk.CTkButton(
                side, text=f"  {label}", height=38, corner_radius=8,
                anchor="w", fg_color="transparent", text_color=theme.MUTED,
                hover_color=theme.PANEL2, font=theme.font(13),
                command=lambda k=key: self._navigate(k))
            btn.pack(fill="x", padx=12, pady=3)
            self._nav_buttons[key] = btn

        # sidebar footer - quick actions
        footer = ctk.CTkFrame(side, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=(0, 14))
        ctk.CTkButton(
            footer, text="Validate Pack", height=34, corner_radius=8,
            fg_color=theme.PANEL2, hover_color=theme.PANEL3,
            text_color=theme.FG, font=theme.font(12),
            command=self._validate_all).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            footer, text="Export local_rules.xml", height=34, corner_radius=8,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color="#ffffff", font=theme.font(12),
            command=self._export_xml).pack(fill="x")
        ctk.CTkLabel(footer, text=f"v{APP_VERSION}",
                     text_color="#4a5570", font=theme.font(10),
                     anchor="w").pack(fill="x", pady=(10, 0))

        # main column
        right = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color=theme.BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 4))
        self._heading = ctk.CTkLabel(header, text="", text_color=theme.FG,
                                     font=theme.font(22, "bold"), anchor="w")
        self._heading.pack(fill="x")
        self._subtitle = ctk.CTkLabel(header, text="", text_color=theme.MUTED,
                                      font=theme.font(12), anchor="w")
        self._subtitle.pack(fill="x", pady=(2, 0))

        self._content = ctk.CTkFrame(right, fg_color=theme.BG, corner_radius=0)
        self._content.grid(row=1, column=0, sticky="nsew", padx=26, pady=8)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        status = ctk.CTkFrame(right, fg_color=theme.PANEL, corner_radius=8,
                              height=30)
        status.grid(row=2, column=0, sticky="ew", padx=26, pady=(4, 16))
        self._status = ctk.CTkLabel(status, text="Ready.",
                                    text_color=theme.MUTED,
                                    font=theme.font(11))
        self._status.pack(side="left", padx=14, pady=4)

    # -------------------------------------------------------------- routing
    def _navigate(self, key: str):
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=theme.ACCENT, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=theme.MUTED)

        title_map = {
            "dashboard": ("Detections at a glance", "Pack metrics for the Web Kill Chain"),
            "library": ("Rule Library", "Browse, search, filter and export the pack"),
            "chain": ("Attack Chain Coverage", "Kill-chain stages mapped to detection rules"),
            "builder": ("Rule Builder", "Author a new rule with live XML preview"),
            "reports": ("Reports & Export", "Generate offline HTML reports"),
        }
        title, sub = title_map.get(key, ("", ""))
        self._heading.configure(text=title)
        self._subtitle.configure(text=sub)

        for w in self._content.winfo_children():
            w.destroy()

        cls = {
            "dashboard": DashboardView,
            "library": LibraryView,
            "chain": ChainView,
            "builder": BuilderView,
            "reports": ReportsView,
        }[key]
        view = cls(self._content, self)
        view.grid(row=0, column=0, sticky="nsew")
        self._view = view
        view.refresh()

    # ------------------------------------------------------------- status
    def set_status(self, msg: str) -> None:
        self._status.configure(text=msg)
        self.after(4000, lambda: self._status.configure(text="Ready."))

    def refresh_all(self) -> None:
        if self._view is not None:
            self._view.refresh()

    # ------------------------------------------------------------ actions
    def _validate_all(self):
        issues = self.rulepack.validate()
        if issues:
            self.set_status(f"{len(issues)} validation issue(s): {issues[0]}")
        else:
            self.set_status("Validation passed: pack is clean.")

    def _export_xml(self):
        try:
            self.rulepack.export_xml(self.xml_export)
            self.set_status(f"Exported {self.rulepack.total} rules to {self.xml_export}")
        except OSError as exc:
            self.set_status(f"Export failed: {exc}")

    def open_report_in_browser(self, path: str) -> None:
        threading.Thread(target=webbrowser.open,
                         args=("file:///" + os.path.abspath(path).replace("\\", "/"),),
                         daemon=True).start()