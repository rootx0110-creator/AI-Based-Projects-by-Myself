"""Deploy & Export: bulk export of configs, wg CLI detection, instructions."""

import os
import tkinter as tk
from tkinter import ttk

from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Card, SectionTitle


class DeployView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store

    def build(self):
        body = ttk.Frame(self.container, style="TFrame")
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        # preview summary
        top = Card(body, title="Export bundle")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.preview = tk.StringVar()
        tk.Label(top.body, textvariable=self.preview, bg=theme.PANEL, fg=theme.TEXT,
                 font=theme.FONT_MONO, justify="left", anchor="w").pack(anchor="w")
        bar = ttk.Frame(top.body, style="Card.TFrame")
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="\u2b73  Export all to folder\u2026",
                   style="Accent.TButton", command=self._export).pack(side="left")
        ttk.Button(bar, text="Detect WireGuard CLI", style="Ghost.TButton",
                   command=self._detect).pack(side="left", padx=8)
        self.detect_lbl = tk.Label(bar, text="", bg=theme.PANEL, fg=theme.MUTED,
                                   font=("Segoe UI", 9))
        self.detect_lbl.pack(side="left", padx=8)

        # instructions
        mid = Card(body, title="Bring the tunnel up")
        mid.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        text = (
            "Linux server:  sudo apt install wireguard; sudo wg-quick up wg0.conf\n"
            "   (Persist across reboot: systemctl enable wg-quick@wg0)\n\n"
            "Windows server / client: open the official WireGuard app > Import tunnel(s)\n"
            "   and select the exported .conf files.\n\n"
            "Mobile peers: scan the QR inside the client config preview from the\n"
            "   Peers & Devices page, or import the client-<name>.conf file.\n\n"
            "This tool only creates the configuration; the actual tunnel is brought\n"
            "   up by wg-quick / the official clients."
        )
        tk.Label(mid.body, text=text, bg=theme.PANEL, fg=theme.TEXT, justify="left",
                 font=theme.FONT_MONO, anchor="w").pack(anchor="w")

        # recent exports
        SectionTitle(body, "Export history").grid(row=2, column=0, sticky="w", pady=(4, 8))
        self.tree = ttk.Treeview(body, columns=("at", "folder", "peers"), show="headings")
        self.tree.heading("at", text="When")
        self.tree.heading("folder", text="Folder")
        self.tree.heading("peers", text="Peers")
        self.tree.column("at", width=160, stretch=False)
        self.tree.column("folder", width=640)
        self.tree.column("peers", width=60, anchor="center", stretch=False)
        self.tree.grid(row=3, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        vsb.grid(row=3, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.refresh()

    def refresh(self):
        if not hasattr(self, "tree"):
            return
        srv = self.store.server
        peer_count = len(self.store.peers)
        lines = [f"interface : {srv.get('interface_name') or 'wg0'}",
                 f"listen    : UDP {srv.get('listen_port', 51820)}",
                 f"subnet    : {srv.get('subnet')}  server {srv.get('address')}",
                 f"endpoint  : {srv.get('endpoint_host') or '(not set - clients cannot connect)'}",
                 f"peers     : {peer_count} device(s) -> one client-<name>.conf each",
                 "the folder receives wg0.conf + all client configs in one pass"]
        self.preview.set("\n".join(lines))

        self.tree.delete(*self.tree.get_children())
        for e in reversed(self.store.exports):
            self.tree.insert("", "end", values=(
                str(e.get("at", ""))[:19].replace("T", " "),
                e.get("folder", ""), e.get("peer_count", 0)))

        det = self.app.detect_wg()
        if det["ok"]:
            self.detect_lbl.configure(text=f"{det['name']} found: {det['path']}",
                                      fg=theme.GOOD)
        else:
            self.detect_lbl.configure(text="wg CLI not detected (config build only)",
                                      fg=theme.WARN)

    def _export(self):
        self.app.export_configs()
        self.refresh()

    def _detect(self):
        det = self.app.detect_wg()
        if det["ok"]:
            self.app.notify(f"WireGuard CLI found: {det['path']}", "good")
        else:
            self.app.notify("No wg CLI on this machine - config build only.", "warn")