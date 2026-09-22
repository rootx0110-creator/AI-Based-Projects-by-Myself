"""Dashboard: KPI cards, quick actions, server snapshot and recent activity."""

import tkinter as tk
from tkinter import ttk

from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Card, StatCard, SectionTitle


class DashboardView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store
        self.body = ttk.Frame(container, style="TFrame")
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)

    def build(self):
        self.refresh()

    def refresh(self):
        for c in self.body.winfo_children():
            c.destroy()
        srv = self.store.server
        ready = bool(srv.get("private_key") and srv.get("endpoint_host"))

        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=1)
        self.body.columnconfigure(2, weight=1)
        self.body.columnconfigure(3, weight=1)
        self.body.rowconfigure(1, weight=1)

        cards = [
            ("Tunnel state", "Ready" if ready else "Setup needed",
             "Server keys + endpoint host set" if ready else "Finish the Tunnel Builder",
             theme.GOOD if ready else theme.WARN),
            ("Peers", str(len(self.store.peers)),
             "configured devices \u00b7 imported via QR or file",
             theme.ACCENT_ALT),
            ("Config exports", str(len(self.store.exports)),
             "deployments written to disk", theme.ACCENT),
            ("Server key", "Generated" if srv.get("public_key") else "Missing",
             "Curve25519 / preserves address space", theme.GOOD if srv.get("public_key") else theme.DANGER),
        ]
        for i, (cap, value, sub, accent) in enumerate(cards):
            StatCard(self.body, value=value, caption=f"{cap}\n{sub}", accent=accent,
                     relief="flat", borderwidth=0).grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 6),
                pady=(0, 12))

        # left column: server snapshot + activity
        left = ttk.Frame(self.body, style="TFrame")
        left.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        srv_card = Card(left, title="Server snapshot")
        srv_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        rows = [
            ("Profile name", srv.get("interface_name") or "wg0"),
            ("Listen port (UDP)", str(srv.get("listen_port", 51820))),
            ("Subnet", srv.get("subnet", "-")),
            ("Server address", srv.get("address", "-")),
            ("Endpoint host", srv.get("endpoint_host") or "(unset)"),
            ("DNS", srv.get("dns") or "-"),
            ("MTU", str(srv.get("mtu", 1420))),
        ]
        grid = ttk.Frame(srv_card.body, style="Card.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        for i, (k, v) in enumerate(rows):
            ttk.Label(grid, text=k, style="CardMuted.TLabel").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=3)
            ttk.Label(grid, text=v, style="Card.TLabel",
                      font=theme.FONT_MONO).grid(row=i, column=1, sticky="w", pady=3)

        act_card = Card(left, title="Recent activity")
        act_card.grid(row=1, column=0, sticky="nsew")
        evs = list(reversed(self.store.events[-8:]))
        if not evs:
            ttk.Label(act_card.body, text="No activity yet.",
                      style="CardMuted.TLabel").pack(anchor="w")
        for e in evs:
            row = ttk.Frame(act_card.body, style="Card.TFrame")
            row.pack(fill="x", pady=2)
            stamp = str(e.get("at", "")).split("T")[-1][:8]
            lvl = (e.get("level") or "info").upper()
            color = {"INFO": theme.MUTED, "WARN": theme.WARN,
                     "ERROR": theme.DANGER}.get(lvl, theme.MUTED)
            tk.Label(row, text=stamp, bg=theme.PANEL, fg=theme.MUTED,
                     font=theme.FONT_MONO, width=9, anchor="w").pack(side="left")
            tk.Label(row, text=lvl, bg=theme.PANEL, fg=color,
                     font=("Segoe UI", 8, "bold"), width=6, anchor="w").pack(side="left")
            tk.Label(row, text=e.get("message", ""), bg=theme.PANEL,
                     fg=theme.TEXT, anchor="w").pack(side="left", fill="x", expand=True)

        # right column: quick actions
        right = ttk.Frame(self.body, style="TFrame")
        right.grid(row=1, column=2, columnspan=2, sticky="nsew", padx=(6, 0))
        right.columnconfigure(0, weight=1)

        SectionTitle(right, "Quick actions").grid(row=0, column=0, sticky="w",
                                                  padx=2, pady=(0, 8))
        card = Card(right, title="Workflows")
        card.grid(row=1, column=0, sticky="ew")
        actions = [
            ("\u26ab  New peer device", lambda: self._add_peer()),
            ("\u23f7  Export all configs", lambda: self.app.export_configs()),
            ("\u2693  Download HTML report", lambda: self.app.generate_report()),
            ("\u2699  Configure server", lambda: self.app.switch("builder")),
            ("\u21bb  Manage peers & QR", lambda: self.app.switch("peers")),
        ]
        for i, (label, cmd) in enumerate(actions):
            ttk.Button(card.body, text=label, command=cmd).pack(
                fill="x", pady=3, padx=4)

        warn = ttk.Frame(card.body, style="Card.TFrame")
        warn.pack(fill="x", pady=(12, 0))
        tk.Frame(warn, bg=theme.BORDER_SOFT).pack(fill="x")
        tk.Label(warn, text="Security note", bg=theme.PANEL, fg=theme.WARN,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 2))
        tk.Label(warn, text="Reports and exported .conf files contain private "
                            "keys. Handle them like key material and store them "
                            "in a trusted location only.",
                 bg=theme.PANEL, fg=theme.MUTED, wraplength=430, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w")

    def _add_peer(self):
        self.app.switch("peers")