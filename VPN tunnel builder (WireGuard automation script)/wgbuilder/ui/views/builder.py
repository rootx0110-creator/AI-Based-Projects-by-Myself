"""Tunnel Builder: server profile parameters + keypair management."""

import tkinter as tk
from tkinter import ttk, messagebox

import ipaddress

from wgbuilder.core import keys, configs
from wgbuilder.ui import theme
from wgbuilder.ui.widgets import Card, KeyField


class BuilderView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store
        self.body = ttk.Frame(container, style="TFrame")
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)

    def build(self):
        srv = self.store.server
        cols = ttk.Frame(self.body, style="TFrame")
        cols.grid(row=0, column=0, sticky="nsew")
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)
        cols.rowconfigure(0, weight=1)

        # --- left: parameters -------------------------------------------
        card = Card(cols, title="Network parameters")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form = ttk.Frame(card.body, style="Card.TFrame")
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        self.vars = {}
        fields = [
            ("Profile / interface name", "interface_name"),
            ("Listen port (UDP)", "listen_port"),
            ("Subnet (CIDR)", "subnet"),
            ("Server address on tunnel", "address"),
            ("Endpoint host (public IP or DNS)", "endpoint_host"),
            ("DNS pushed to clients", "dns"),
            ("MTU", "mtu"),
        ]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label, style="CardMuted.TLabel").grid(
                row=i, column=0, sticky="w", padx=(0, 14), pady=5)
            var = tk.StringVar(value=str(srv.get(key, "")))
            entry = ttk.Entry(form, textvariable=var)
            entry.grid(row=i, column=1, sticky="ew", pady=5)
            self.vars[key] = var

        self.subnet_hint = tk.StringVar(
            value=configs.describe_subnet(str(self.vars["subnet"].get() or "10.0.0.0/24")))
        tk.Label(form, textvariable=self.subnet_hint, bg=theme.PANEL, fg=theme.MUTED,
                 font=("Segoe UI", 9)).grid(row=len(fields), column=1, sticky="w")

        ttk.Label(form, text="PostUp / PostDown (optional, server-side)",
                  style="CardMuted.TLabel").grid(row=len(fields) + 1, column=0,
                                                 sticky="w", padx=(0, 14), pady=(10, 5))
        self.vars["post_up"] = tk.StringVar(value=str(srv.get("post_up", "")))
        self.vars["post_down"] = tk.StringVar(value=str(srv.get("post_down", "")))
        ttk.Entry(form, textvariable=self.vars["post_up"]).grid(
            row=len(fields) + 1, column=1, sticky="ew", pady=5)
        ttk.Entry(form, textvariable=self.vars["post_down"]).grid(
            row=len(fields) + 2, column=1, sticky="ew", pady=5)

        btn = ttk.Button(card.body, text="Save server profile",
                         style="Accent.TButton", command=self.save)
        btn.pack(fill="x", pady=(14, 0))
        ttk.Button(card.body, text="Reset subnet defaults",
                   style="Ghost.TButton", command=self._defaults).pack(fill="x", pady=(6, 0))

        # --- right: keys --------------------------------------------------
        kcard = Card(cols, title="Server keypair (Curve25519)", accent=theme.ACCENT_ALT)
        kcard.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        info = tk.Label(kcard.body, text="WireGuard keys are generated 100% "
                        "on-device. The public key is what clients put in their "
                        "[Peer] sections.",
                        bg=theme.PANEL, fg=theme.MUTED, wraplength=330, justify="left",
                        font=("Segoe UI", 9))
        info.pack(anchor="w", pady=(0, 12))

        self.priv_field = KeyField(kcard.body, "PRIVATE KEY", srv.get("private_key", ""))
        self.priv_field.pack(fill="x", pady=(0, 14))
        self.pub_var = tk.StringVar(value=srv.get("public_key", ""))
        ttk.Label(kcard.body, style="CardMuted.TLabel").pack(anchor="w")
        self.pub_field = KeyField(kcard.body, "PUBLIC KEY (shared)",
                                  srv.get("public_key", ""))
        self.pub_field.pack(fill="x", pady=(0, 14))

        btns = ttk.Frame(kcard.body, style="Card.TFrame")
        btns.pack(fill="x")
        ttk.Button(btns, text="Generate new keypair",
                   style="Accent.TButton", command=self.regenerate,
                   ).pack(side="left")
        ttk.Button(btns, text="Paste private key",
                   style="Ghost.TButton", command=self.paste_key).pack(side="left", padx=8)
        ttk.Button(btns, text="Copy public key",
                   style="Ghost.TButton", command=self.copy_pub).pack(side="left")

    def _defaults(self):
        self.vars["subnet"].set("10.0.0.0/24")
        self.vars["address"].set("10.0.0.1")
        self.vars["dns"].set(self.store.settings.get("default_dns", "1.1.1.1"))
        self.vars["mtu"].set(str(self.store.settings.get("default_mtu", 1420)))
        self.vars["listen_port"].set("51820")
        self._refresh_hint()

    def _refresh_hint(self):
        try:
            self.subnet_hint.set(configs.describe_subnet(self.vars["subnet"].get()))
        except ValueError:
            self.subnet_hint.set("invalid subnet")
        except Exception:  # noqa: BLE001
            self.subnet_hint.set("invalid subnet")

    def save(self):
        srv = self.store.server
        text_map = {
            "interface_name": "interface_name",
            "endpoint_host": "endpoint_host",
            "post_up": "post_up",
            "post_down": "post_down",
        }
        for key, dest in text_map.items():
            srv[dest] = self.vars[key].get().strip()

        try:
            port = int(self.vars["listen_port"].get())
            if not 1 <= port <= 65535:
                raise ValueError("Port must be 1-65535")
            srv["listen_port"] = port
        except ValueError as exc:
            messagebox.showwarning("Builder", f"Listen port invalid.\n{exc}")
            return
        try:
            net = configs.normalize_subnet(self.vars["subnet"].get())
            srv["subnet"] = str(net)
        except ValueError:
            messagebox.showwarning("Builder", "Subnet must be a valid CIDR, e.g. 10.0.0.0/24")
            return
        try:
            addr = ipaddress.IPv4Address(self.vars["address"].get())
        except ValueError:
            messagebox.showwarning("Builder", "Server address is not a valid IPv4 address")
            return
        try:
            mtu = int(self.vars["mtu"].get())
        except ValueError:
            messagebox.showwarning("Builder", "MTU must be an integer")
            return
        if addr not in configs.normalize_subnet(str(net)):
            messagebox.showwarning("Builder",
                                   "Server address is outside the configured subnet")
            return
        srv["address"] = str(addr)
        srv["mtu"] = mtu
        srv["dns"] = self.vars["dns"].get().strip() or "1.1.1.1"
        host = srv["endpoint_host"].strip()
        if not host:
            messagebox.showwarning("Builder", "Set an endpoint host so clients can "
                                   "reach the server (public IP or hostname).")
            return
        self.store.log("info", f"Server profile updated (port {port}, subnet {srv['subnet']})")
        self.store.save()
        self.app.notify("Server profile saved", "good")

    def regenerate(self):
        if not messagebox.askyesno("Regenerate", "Replace the current server keypair?\n"
                                    "Existing client configs will no longer match."):
            return
        priv, pub = keys.generate_keypair()
        self.store.server["private_key"] = priv
        self.store.server["public_key"] = pub
        self.store.server["updated_at"] = __import__("datetime").datetime.now().isoformat()
        self.store.log("warn", "Server keypair regenerated")
        self.store.save()
        self.priv_field.set(priv)
        self.pub_field.set(pub)
        self.app.notify("New server keypair generated", "good")

    def paste_key(self):
        from tkinter import simpledialog
        val = simpledialog.askstring("Paste private key",
                                     "Private key (wg genkey output):",
                                     parent=self.app.root)
        if not val:
            return
        val = val.strip()
        if not keys.is_valid_key(val):
            messagebox.showerror("Validate", "That does not look like a WireGuard key "
                                   "(44 chars, base64).")
            return
        pub = keys.derive_public(val)
        self.store.server["private_key"] = val
        self.store.server["public_key"] = pub
        self.store.log("info", "Server key imported from clipboard/paste")
        self.store.save()
        self.priv_field.set(val)
        self.pub_field.set(pub)
        self.app.notify("Server key imported", "good")

    def copy_pub(self):
        self.pub_field._copy()

    def refresh(self):
        self.build()