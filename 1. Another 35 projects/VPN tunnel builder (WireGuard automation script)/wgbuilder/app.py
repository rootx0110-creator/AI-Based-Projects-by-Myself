"""Main window + application controller for the VPN Tunnel Builder."""

import ctypes
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from wgbuilder import __title__, __version__, __tagline__
from wgbuilder.core import configs, report
from wgbuilder.core.store import Store
from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Footer

from wgbuilder.ui.views.dashboard import DashboardView
from wgbuilder.ui.views.builder import BuilderView
from wgbuilder.ui.views.peers import PeersView
from wgbuilder.ui.views.deploy import DeployView
from wgbuilder.ui.views.reports import ReportsView
from wgbuilder.ui.views.settings import SettingsView


def _enable_dpi_awareness():
    for fn in ("SetProcessDpiAwareness", ):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            return
        except Exception:  # noqa: BLE001
            pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


class App:
    """Owns the window, the store and cross-view workflows."""

    NAV = [
        ("dashboard", "Dashboard", "\u25a1"),
        ("builder", "Tunnel Builder", "\u2699"),
        ("peers", "Peers & Devices", "\u21bb"),
        ("deploy", "Deploy", "\u2b73"),
        ("reports", "Reports & Logs", "\u2693"),
        ("settings", "Settings", "\u2630"),
    ]

    def __init__(self, data_folder: str | None = None, _boot_test=None):
        self.store = Store(data_folder=data_folder)
        self.store.load()

        self.root = tk.Tk()
        self.root.title(f"{__title__} \u2014 {__tagline__}")
        self.root.geometry("1180x740")
        self.root.minsize(1080, 680)
        theme.apply(self.root)

        self._views = {
            "dashboard": DashboardView,
            "builder": BuilderView,
            "peers": PeersView,
            "deploy": DeployView,
            "reports": ReportsView,
            "settings": SettingsView,
        }
        self._current = None
        self._nav_buttons = {}
        self._build_chrome()
        self.switch("dashboard")
        if _boot_test:
            self.root.after(700, lambda: _boot_test(self))
        self.root.mainloop()

    # ---- chrome ---------------------------------------------------------
    def _build_chrome(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        rail = ttk.Frame(self.root, style="Rail.TFrame")
        rail.grid(row=0, column=0, sticky="ns")
        rail.configure(width=230)
        rail.grid_propagate(False)
        rail.columnconfigure(0, weight=1)

        brand = ttk.Frame(rail, style="Rail.TFrame")
        brand.pack(fill="x", padx=18, pady=(22, 14))
        tk.Label(brand, text="VPN TUNNEL", bg=theme.BG_SOFT, fg=theme.TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(brand, text="BUILDER", bg=theme.BG_SOFT, fg=theme.ACCENT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Frame(brand, height=1, bg=theme.BORDER).pack(fill="x", pady=(10, 0))

        tk.Label(rail, text="NAVIGATION", bg=theme.BG_SOFT, fg=theme.MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24, pady=(4, 4))

        for pid, label, _ in self.NAV:
            btn = ttk.Button(rail, text=label, style="Nav.TButton",
                             command=lambda p=pid: self.switch(p))
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[pid] = btn

        rail_fill = ttk.Frame(rail, style="Rail.TFrame")
        rail_fill.pack(fill="both", expand=True)
        tk.Label(rail_fill, text=f"v{__version__} \u00b7 lab/authorized use",
                 bg=theme.BG_SOFT, fg=theme.MUTED,
                 font=("Segoe UI", 8)).pack(side="bottom", pady=14)

        main = ttk.Frame(self.root, style="TFrame")
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = tk.Frame(main, bg=theme.BG)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 6))
        self._header_title = tk.Label(header, text="", bg=theme.BG, fg=theme.TEXT,
                                      font=theme.FONT_TITLE)
        self._header_title.pack(anchor="w")
        self._header_sub = tk.Label(header, text="", bg=theme.BG, fg=theme.MUTED,
                                    font=("Segoe UI", 9))
        self._header_sub.pack(anchor="w")

        self.content = ttk.Frame(main, style="TFrame")
        self.content.grid(row=1, column=0, sticky="nsew", padx=28, pady=(6, 4))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.footer = Footer(main)
        self.footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 12))
        self.footer.meta_var.set(f"data: {self.store.data_folder}")

    # ---- navigation -----------------------------------------------------
    def switch(self, page_id: str):
        if page_id == self._current:
            self.refresh_current()
            return
        for c in self.content.winfo_children():
            c.destroy()
        view_cls = self._views[page_id]
        view = view_cls(self.content, self)
        view.build()
        self._current = page_id
        self._set_header(page_id)
        for pid, btn in self._nav_buttons.items():
            btn.state(["!pressed"])
            btn.configure(style="NavActive.TButton" if pid == page_id else "Nav.TButton")

    def _set_header(self, page_id: str):
        meta = {
            "dashboard": ("Overview", "Tunnel health and quick actions"),
            "builder": ("Server profile", "Subnet, port, keys and network policy"),
            "peers": ("Peers & devices", "Client keypairs, addresses and QR import"),
            "deploy": ("Deploy & export", "Write server + client configs to disk"),
            "reports": ("Reports & logs", "HTML report download and activity trail"),
            "settings": ("Settings", "Defaults, storage and WireGuard CLI path"),
        }
        label, sub = meta[page_id]
        self._header_title.configure(text=label)
        self._header_sub.configure(text=sub)

    def refresh_current(self):
        v = self.content.winfo_children()
        if v and hasattr(v[0], "refresh"):
            v[0].refresh()

    def notify(self, message: str, level: str = "info", timeout_ms: int = 6000):
        self.footer.notify(message, level, timeout_ms)

    def save(self):
        self.store.save()
        self.store.log("info", "State saved")

    # ---- workflows -------------------------------------------------------
    def generate_report(self, auto_open: bool = True, suffix: str = "") -> str | None:
        state = self.store.snapshot()
        doc = report.build_report(state, self.store.events, suffix)
        default_name = report.default_filename()
        from tkinter import filedialog, messagebox

        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")],
            title="Download VPN Tunnel Builder report")
        if not path:
            return None
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(doc)
        except OSError as exc:
            messagebox.showerror("Report", f"Could not write report:\n{exc}")
            self.notify("Report save failed", "error")
            return None
        self.store.log("info", f"HTML report downloaded -> {path}")
        self.store.save()
        self.notify(f"Report saved: {os.path.basename(path)}", "good")
        if auto_open:
            try:
                os.startfile(path)
            except OSError:
                pass
        return path

    def export_configs(self) -> tuple[str | None, list[str]]:
        """Export centered on a folder picker; returns (folder, written files)."""
        import datetime
        from tkinter import filedialog, messagebox

        srv = self.store.server
        if not srv.get("private_key"):
            messagebox.showwarning("Export", "Generate server keys first.")
            return None, []
        folder = filedialog.askdirectory(parent=self.root, title="Choose export folder")
        if not folder:
            return None, []
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = os.path.join(folder, f"wireguard-tunnel-{stamp}")
        os.makedirs(target, exist_ok=True)
        written = []
        try:
            sconf = configs.build_server_config(srv, self.store.peers)
            server_file = os.path.join(target, f"{srv.get('interface_name') or 'wg0'}.conf")
            with open(server_file, "w", encoding="utf-8") as fh:
                fh.write(sconf)
            written.append(server_file)
            for p in sorted(self.store.peers, key=lambda x: x.get("name", "")):
                cconf = configs.build_client_config(srv, p, __title__)
                safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in p["name"])
                cpath = os.path.join(target, f"client-{safe}.conf")
                with open(cpath, "w", encoding="utf-8") as fh:
                    fh.write(cconf)
                written.append(cpath)
        except ValueError as exc:
            messagebox.showwarning("Export", str(exc))
            return None, []
        self.store.record_export(target, len(self.store.peers))
        self.store.save()
        self.notify(f"Exported {len(written)} config file(s) to {target}", "good")
        return target, written

    def detect_wg(self) -> dict:
        """Detect the WireGuard CLI; returns {'name', 'path', 'ok', 'hint'}."""
        srv = self.store.server
        profiles = [
            ("wireguard", self.store.settings.get("wg_cli_path")),
            ("wg", shutil.which("wg")),
            ("wireguard", shutil.which("wireguard")),
            ("wg-quick", shutil.which("wg-quick")),
        ]
        for name, path in profiles:
            if not path or not os.path.exists(path):
                continue
            try:
                subprocess.run([path, "--version"], capture_output=True, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                return {"name": name, "path": path, "ok": True, "hint": ""}
            except Exception:  # noqa: BLE001
                continue
        return {"name": "", "path": "", "ok": False,
                "hint": ("No wg CLI found. This tool only builds configs - bring the "
                         "tunnel up with the official WireGuard app or a wg-quick host.")}


def run(data_folder: str | None = None):
    _enable_dpi_awareness()
    App(data_folder=data_folder)


if __name__ == "__main__":
    run()