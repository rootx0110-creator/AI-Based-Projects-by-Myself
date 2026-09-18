import customtkinter as ctk

from .theme import BG, MUTED, TEXT, FONT_FAMILY, ACCENT
from .widgets import build_btn, build_label, build_switch, card


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self.cfg = dict(self.agent.config)
        self._vars = {}
        self._build()

    def _var(self, key):
        if key not in self._vars:
            self._vars[key] = ctk.StringVar(value=str(self.cfg[key]))
        return self._vars[key]

    def _gvar(self, key):
        return self._vars[key].get()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        build_label(header, "Settings", size=22, weight="bold").pack(side="left")

        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        col = ctk.CTkFrame(body, fg_color=BG)
        col.pack(side="left", fill="both", expand=True, padx=6)

        # --- Monitoring toggles ---
        mon = card(col, title="Detection Modules")
        mon.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(mon, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)
        self.fim_sw = ctk.BooleanVar(value=bool(self.cfg["fim_enabled"]))
        row, _ = build_switch(inner, "File integrity monitoring", self.fim_sw, self._mark_dirty)
        row.pack(fill="x", pady=3)
        self.proc_sw = ctk.BooleanVar(value=bool(self.cfg["process_enabled"]))
        row2, _ = build_switch(inner, "Process monitoring", self.proc_sw, self._mark_dirty)
        row2.pack(fill="x", pady=3)
        self.auto_sw = ctk.BooleanVar(value=bool(self.cfg["auto_whitelist_processes"]))
        row3, _ = build_switch(inner, "Auto-learn process whitelist",
                               self.auto_sw, self._mark_dirty)
        row3.pack(fill="x", pady=3)

        # --- Tuning ---
        tune = card(col, title="Tuning")
        tune.pack(fill="x", pady=(8, 4))
        grid = ctk.CTkFrame(tune, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=10)
        self._grid(grid, "scan_interval_sec", "FIM scan interval (sec)")
        self._grid(grid, "process_interval_sec", "Process interval (sec)")
        self._grid(grid, "max_file_size_mb", "Max file size to hash (MB)")
        self._grid(grid, "high_cpu_threshold", "High CPU threshold (%)")
        self._grid(grid, "high_mem_threshold_mb", "High memory threshold (MB)")

        row_sub = ctk.CTkFrame(tune, fg_color="transparent")
        row_sub.pack(fill="x", padx=14, pady=(0, 10))
        build_label(row_sub, "Hash algorithm", size=12).pack(side="left")
        self.algo_menu = ctk.CTkComboBox(
            row_sub, values=["sha256", "sha1", "md5"], width=140, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly",
            command=lambda _: self._mark_dirty())
        self.algo_menu.set(self.cfg["hash_algorithm"])
        self.algo_menu.pack(side="left", padx=10)

        # --- Save bar ---
        savebar = ctk.CTkFrame(col, fg_color="transparent")
        savebar.pack(fill="x", pady=8)
        build_btn(savebar, "Save Settings", self._save, primary=True).pack(side="left")
        self.save_msg = build_label(savebar, "", size=12, color=MUTED)
        self.save_msg.pack(side="left", padx=12)

        side = ctk.CTkFrame(body, fg_color=BG, width=340)
        side.pack(side="left", fill="y", padx=6)
        info = card(side, title="About")
        info.pack(fill="x", pady=4)
        box = ctk.CTkFrame(info, fg_color="transparent")
        box.pack(fill="x", padx=14, pady=10)
        build_label(box, "HIDS Agent", size=16, weight="bold").pack(anchor="w")
        build_label(box, """Host-based intrusion detection agent combining
file integrity monitoring (hashes, baselines,
drift detection) with process monitoring
(new / resource-hogging processes).

Data is stored locally in:
%LOCALAPPDATA%\\HIDS_Agent
""", size=11, color=MUTED).pack(anchor="w", pady=(6, 0))

    def _grid(self, parent, key, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        row.grid_columnconfigure(0, weight=1)
        build_label(row, label, size=12).grid(row=0, column=0, sticky="w")
        var = self._var(key)
        e = ctk.CTkEntry(row, width=130, height=28, textvariable=var, fg_color="#141a24",
                         border_color="#2a3444", text_color=TEXT,
                         font=(FONT_FAMILY, 11))
        e.grid(row=0, column=1, sticky="e")
        e.bind("<KeyRelease>", lambda ev: self._mark_dirty())

    def _mark_dirty(self):
        self.save_msg.configure(text="Unsaved changes", text_color="#d29922")

    def _save(self):
        try:
            cfg = dict(self.cfg)
            cfg["fim_enabled"] = bool(self.fim_sw.get())
            cfg["process_enabled"] = bool(self.proc_sw.get())
            cfg["auto_whitelist_processes"] = bool(self.auto_sw.get())
            cfg["scan_interval_sec"] = max(2, int(self._gvar("scan_interval_sec")))
            cfg["process_interval_sec"] = max(2, int(self._gvar("process_interval_sec")))
            cfg["max_file_size_mb"] = max(1, int(self._gvar("max_file_size_mb")))
            cfg["high_cpu_threshold"] = float(self._gvar("high_cpu_threshold"))
            cfg["high_mem_threshold_mb"] = int(self._gvar("high_mem_threshold_mb"))
            cfg["hash_algorithm"] = self.algo_menu.get()
            self.agent.save_settings(cfg)
            self.cfg = dict(cfg)
            self.save_msg.configure(text="Saved", text_color="#3fb950")
        except (ValueError, KeyError) as exc:
            self.save_msg.configure(text=f"Invalid value: {exc}", text_color="#f85149")

    def refresh(self):
        pass