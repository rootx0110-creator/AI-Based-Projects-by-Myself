"""Settings: defaults, data location, wg CLI path, about."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from wgbuilder import __version__, __title__
from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Card, SectionTitle


class SettingsView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store

    def build(self):
        body = ttk.Frame(self.container, style="TFrame")
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        s = self.store.settings
        defaults = Card(body, title="Default values for new configs")
        defaults.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        form = ttk.Frame(defaults.body, style="Card.TFrame")
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.v_dns = tk.StringVar(value=str(s.get("default_dns", "1.1.1.1")))
        self.v_mtu = tk.StringVar(value=str(s.get("default_mtu", 1420)))
        self.v_ka = tk.StringVar(value=str(s.get("default_keepalive", 25)))
        for i, (label, var, w) in enumerate([
                ("Default DNS", self.v_dns, 0),
                ("Default MTU", self.v_mtu, 0),
                ("Default keepalive (s)", self.v_ka, 0)]):
            ttk.Label(form, text=label, style="CardMuted.TLabel").grid(
                row=i, column=0, sticky="w", padx=(0, 14), pady=5)
            e = ttk.Entry(form, textvariable=var)
            e.grid(row=i, column=1, sticky="w", pady=5, padx=(0, 999))
            e.configure(width=10)

        ttk.Button(defaults.body, text="Save defaults", style="Accent.TButton",
                   command=self._save_defaults).pack(fill="x", pady=(12, 0))

        disk = Card(body, title="Storage", accent=theme.ACCENT_ALT)
        disk.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        tk.Label(disk.body, text="Application state (keys, peers, events) is stored as "
                 "a single JSON file. Reports you download go wherever you choose.",
                 bg=theme.PANEL, fg=theme.MUTED, wraplength=380, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))
        self.folder_var = tk.StringVar(value=self.store.data_folder)
        row = ttk.Frame(disk.body, style="Card.TFrame")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.folder_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Browse\u2026", style="Ghost.TButton",
                   command=self._browse_folder).grid(row=0, column=1, padx=(6, 0))
        os_path = os.path.join(self.store.data_folder, "state.json")
        tk.Label(disk.body, text=f"state.json -> {os_path}", bg=theme.PANEL,
                 fg=theme.MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

        cli = Card(body, title="WireGuard CLI")
        cli.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 8), pady=(12, 0))
        tk.Label(cli.body, text="Optional override for the wg binary used by the "
                 "Deploy page's self-diagnostics. Not required to build configs.",
                 bg=theme.PANEL, fg=theme.MUTED, wraplength=800, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))
        crow = ttk.Frame(cli.body, style="Card.TFrame")
        crow.pack(fill="x")
        crow.columnconfigure(0, weight=1)
        self.v_wg = tk.StringVar(value=str(s.get("wg_cli_path", "")))
        ttk.Entry(crow, textvariable=self.v_wg).grid(row=0, column=0, sticky="ew")
        ttk.Button(crow, text="Browse\u2026", style="Ghost.TButton",
                   command=self._browse_wg).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(crow, text="Save CLI path", command=self._save_wg).grid(
            row=0, column=2, padx=(6, 0))

        about = Card(body, title="About")
        about.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0, 8), pady=(12, 0))
        tk.Label(about.body, text=f"{__title__} v{__version__}\n"
                 "WireGuard tunnel builder - offline config factory and report "
                 "generator.\n\nFor authorized, lab and training use only. Exported "
                 "configs contain private keys.",
                 bg=theme.PANEL, fg=theme.MUTED, font=("Segoe UI", 9),
                 justify="left").pack(anchor="w")

    def refresh(self):
        pass

    def _save_defaults(self):
        try:
            mtu = int(self.v_mtu.get())
            ka = int(self.v_ka.get())
        except ValueError:
            messagebox.showwarning("Settings", "MTU and keepalive must be integers.")
            return
        self.store.settings["default_dns"] = self.v_dns.get().strip() or "1.1.1.1"
        self.store.settings["default_mtu"] = mtu
        self.store.settings["default_keepalive"] = ka
        self.store.save()
        self.app.notify("Defaults saved", "good")

    def _browse_folder(self):
        if hasattr(self.app, "root"):
            folder = filedialog.askdirectory(parent=self.app.root,
                                             title="Data folder")
        else:
            folder = filedialog.askdirectory(title="Data folder")
        if not folder:
            return
        if messagebox.askyesno("Storage",
                               "Move state.json into the new folder now?\n"
                               f"(Old state remains where it was.)"):
            self._move_state(folder)
        else:
            self.folder_var.set(folder)

    def _move_state(self, new_folder: str):
        self.store.save()
        os.makedirs(new_folder, exist_ok=True)
        try:
            os.replace(self.store.path, os.path.join(new_folder, "state.json"))
        except OSError as exc:
            messagebox.showerror("Storage", f"Could not move state file:\n{exc}")
            return
        self.store.data_folder = new_folder
        self.store.path = os.path.join(new_folder, "state.json")
        self.store.settings["data_folder"] = new_folder
        self.store.save()
        self.folder_var.set(new_folder)
        self.app.footer.meta_var.set(f"data: {new_folder}")
        self.app.notify("State file moved", "good")

    def _browse_wg(self):
        path = filedialog.askopenfilename(parent=self.app.root, title="wg executable")
        if path:
            self.v_wg.set(path)

    def _save_wg(self):
        self.store.settings["wg_cli_path"] = self.v_wg.get().strip()
        self.store.save()
        self.app.notify("WireGuard CLI path saved", "good")