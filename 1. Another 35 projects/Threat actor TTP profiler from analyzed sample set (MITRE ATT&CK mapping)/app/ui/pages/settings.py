"""Settings page: engine configuration and about."""

from __future__ import annotations

import os

import customtkinter as ctk
from tkinter import filedialog, messagebox

from .. import theme
from .. import widgets as w
from ...core.yara_engine import YaraEngine, load_rules_meta


class SettingsPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        

    def _build(self) -> None:
        outer = ctk.CTkScrollableFrame(self.frame, fg_color=theme.BG)
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        outer.grid_columnconfigure(0, weight=1)

        w.header(outer, "Settings & Engine", "YARA configuration, thresholds and environment info").grid(
            row=0, column=0, sticky="ew", pady=(0, 10))

        yara_card = w.card(outer, "YARA Detection Engine", row=1, column=0, pady=(0, 10))
        state = "Native yara-python (installed)" if self.app.workbench.yara.is_native else (
            "Pseudo-YARA fallback active" if self.app.workbench.yara.rules_path else "Unavailable")
        self.yara_status = ctk.CTkLabel(yara_card.body, text=state, anchor="w",
                                        font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                                        text_color=theme.GOOD if self.app.workbench.yara.is_native else theme.WARN)
        self.yara_status.grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))
        detail = self.app.workbench.yara.error or "Rule file: %s" % (
            self.app.workbench.yara.rules_path or "none")
        ctk.CTkLabel(yara_card.body, text=detail, anchor="w", justify="left", wraplength=900,
                     font=ctk.CTkFont(theme.FONT, theme.FS_TINY), text_color=theme.TEXT_MUTED).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 8))
        ctk.CTkLabel(yara_card.body, text="Custom rule file (text scan or *.yar):", anchor="w",
                     font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT).grid(
            row=2, column=0, sticky="w", padx=(6, 10), pady=5)
        self.rules_entry = ctk.CTkEntry(yara_card.body, height=32, corner_radius=6,
                                        fg_color=theme.BG_2, border_color=theme.BORDER,
                                        text_color=theme.TEXT)
        self.rules_entry.grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        yara_card.grid_columnconfigure(1, weight=1)
        browse = ctk.CTkButton(yara_card, text="Browse…", width=96, height=32, corner_radius=6,
                               fg_color="transparent", hover_color=theme.FRAME_2, text_color=theme.TEXT,
                               font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), command=self._browse_rules)
        browse.grid(row=2, column=2, padx=6)
        apply_btn = ctk.CTkButton(yara_card.body, text="Apply Custom Rules", width=190, height=36,
                                  corner_radius=8, fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                                  font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"), command=self._apply_rules)
        apply_btn.grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 4))

        threshold = w.card(outer, "Detection Tuning", row=2, column=0, pady=(0, 10))
        ctk.CTkLabel(threshold.body,
                     text="Minimum evidence confidence to surface a technique (default 0 = show all). "
                     "Lower values surface more faint string-only matches.", justify="left",
                     wraplength=900, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT_MUTED).grid(
            row=0, column=0, sticky="w", padx=6, pady=5)
        row = ctk.CTkFrame(threshold.body, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", padx=6, pady=4)
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text="Confidence floor in ATT&CK view:", font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                     text_color=theme.TEXT).grid(row=0, column=0, padx=(0, 10))
        om = ctk.CTkOptionMenu(row, values=["0", "20", "35", "50", "65", "80"], width=84, height=30,
                               corner_radius=6, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), fg_color=theme.FRAME_2,
                               button_color=theme.ACCENT, command=lambda v: self._sync_min(v))
        om.set(self.app.page_objects["attack"].min_conf.get())
        om.grid(row=0, column=1, sticky="w")

        about = w.card(outer, "About & Data", row=3, column=0)
        about.body.grid_columnconfigure(0, weight=1)
        info = ctk.CTkLabel(about.body, justify="left", wraplength=900,
                            font=ctk.CTkFont(theme.FONT_MONO, theme.FS_MONO_SM), text_color=theme.TEXT_MUTED,
                            text=self._about_text())
        info.grid(row=0, column=0, sticky="w", padx=6, pady=6)

    def _about_text(self) -> str:
        lines = []
        lines.append("Application: Threat Actor TTP Profiler  v1.0.0")
        lines.append("Purpose:  static fingerprinting of an analyzed sample set -> MITRE ATT&CK mapping"
                     " -> threat actor similarity")
        lines.append("Data directory:  %s" % self._data_dir())
        lines.append("Knowledge base:  %d techniques, %d detection rules, %d actor profiles" % (
            len(self.app.workbench.attack_db.techniques),
            len(self.app.workbench.attack_db.rules),
            len(self.app.workbench.actor_db.all_actor_ids())))
        lines.append("Sources:  PE imports/DLLs, embedded strings & IOCs, section entropy & packer "
                     "signatures, YARA classification")
        lines.append("")
        lines.append("Typical workflow")
        lines.append("  1. Add analyzed samples (exe/dll/scripts or previously exported JSON)")
        lines.append("  2. Run full analysis (background, threaded)")
        lines.append("  3. Review technique evidence and rank actors on the Threat Actor page")
        lines.append("  4. Download the standalone HTML report from the Reports page")
        return "\n".join(lines)

    def _data_dir(self) -> str:
        from ..main_window import resource_path
        return os.path.dirname(resource_path("data")) + os.sep + "data"

    def _browse_rules(self) -> None:
        path = filedialog.askopenfilename(title="Select YARA rule file",
                                          filetypes=[("YARA rules", "*.yar *.yara *.ys"),
                                                     ("Text", "*.txt"), ("All files", "*.*")])
        if path:
            self.rules_entry.delete(0, "end")
            self.rules_entry.insert(0, path)

    def _apply_rules(self) -> None:
        path = self.rules_entry.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Rule file", "Please choose an existing file.")
            return
        try:
            names = self.app.workbench.yara.compile_user_rules(path)
        except Exception as exc:
            messagebox.showerror("YARA compile error", str(exc))
            return
        self.yara_status.configure(
            text="Custom rules loaded (%d rules, native)" % len(names))
        self.app.set_status("Loaded %d custom YARA rules." % len(names))
        names_txt = ", ".join(load_rules_meta(path)[:8])
        self._rules_meta_text = names_txt

    def _sync_min(self, value: str) -> None:
        self.app.page_objects["attack"].min_conf.set(value)
        self.app.page_objects["attack"].refresh()

    def on_show(self) -> None:
        pass

    def refresh(self) -> None:
        pass