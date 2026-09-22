"""Peers & Devices: inventory table, add/edit/delete, config + QR preview."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import ImageTk

from wgbuilder import __title__
from wgbuilder.core import configs, keys, qr
from wgbuilder.ui import theme


class PeersView:
    def __init__(self, container, app):
        self.container = container
        self.app = app
        self.store = app.store

    def build(self):
        body = ttk.Frame(self.container, style="TFrame")
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(body, style="TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(toolbar, text="+  Add peer", style="Accent.TButton",
                   command=self._add).pack(side="left")
        ttk.Button(toolbar, text="Open client config", command=self._open_config
                   ).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side="left")
        ttk.Button(toolbar, text="Rotate keys", command=self._rotate).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left")

        cols = ("name", "ip", "allowed", "keepalive", "public", "created")
        self.tree = ttk.Treeview(body, columns=cols, show="headings",
                                 selectmode="browse")
        heads = {
            "name": ("Device", 160), "ip": ("Tunnel IP", 110),
            "allowed": ("Allowed IPs", 130), "keepalive": ("KA (s)", 70),
            "public": ("Public key", 300), "created": ("Created", 150),
        }
        for c, (txt, w) in heads.items():
            self.tree.heading(c, text=txt)
            anchor = "center" if c in ("keepalive",) else "w"
            self.tree.column(c, width=w, anchor=anchor, stretch=(c in ("name", "public")))
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<Double-1>", lambda e: self._open_config())

        self.hint = ttk.Label(body, style="Muted.TLabel",
                              text="Select a row, then double-click or use Open client "
                                   "config to view the import file + QR.")
        self.hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.refresh()

    def refresh(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        for p in sorted(self.store.peers, key=lambda x: x.get("name", "")):
            pub = p.get("public_key", "")
            short = pub[:10] + "\u2026" + pub[-6:] if len(pub) > 18 else pub
            self.tree.insert("", "end", iid=p["id"], values=(
                p.get("name", ""), p.get("ip", "-"), p.get("allowed_ips", "-"),
                p.get("keepalive", ""), short,
                str(p.get("created_at", ""))[:19].replace("T", " ")))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Peers", "Select a peer first.")
            return None
        return self.store.peer(sel[0])

    def _next_free_ip(self):
        taken = [p.get("ip") for p in self.store.peers if p.get("ip")]
        try:
            for ip in configs.next_peer_candidates(self.store.server.get("subnet", "10.0.0.0/24"),
                                                   taken):
                return str(ip)
        except Exception:  # noqa: BLE001
            return ""

    def _add(self):
        dlg = PeerDialog(self.app.root, self.store.settings.get("default_keepalive", 25),
                         suggest_ip=self._next_free_ip())
        if not dlg.result:
            return
        name, ip, keepalive = dlg.result
        if any(p.get("name", "").lower() == name.lower() for p in self.store.peers):
            messagebox.showwarning("Peers", f"A peer named '{name}' already exists.")
            return
        ip = ip.strip() or self._next_free_ip()
        if not ip:
            messagebox.showwarning("Peers", "No free address available on this subnet.")
            return
        peer = self.store.new_peer(name, ip=ip, keepalive=keepalive)
        peer["allowed_ips"] = f"{ip}/32"
        peer["name"] = name
        self.store.save()
        self.app.notify(f"Peer '{name}' added - {ip}", "good")
        self.refresh()

    def _edit(self):
        p = self._selected()
        if not p:
            return
        dlg = PeerDialog(self.app.root, p.get("keepalive", 25), name=p.get("name", ""),
                         ip=p.get("ip", ""))
        if not dlg.result:
            return
        name, ip, keepalive = dlg.result
        for other in self.store.peers:
            if other["id"] != p["id"] and other.get("name", "").lower() == name.lower():
                messagebox.showwarning("Peers", "That peer name is already in use.")
                return
        p["name"] = name
        p["ip"] = ip
        p["allowed_ips"] = f"{ip}/32" if ip else ""
        p["keepalive"] = int(keepalive)
        self.store.log("info", f"Peer updated: {name}")
        self.store.save()
        self.app.notify(f"Peer '{name}' updated", "good")
        self.refresh()

    def _delete(self):
        p = self._selected()
        if not p:
            return
        if not messagebox.askyesno("Delete", f"Remove peer '{p.get('name')}' and its keys?"):
            return
        self.store.remove_peer(p["id"])
        self.store.save()
        self.app.notify(f"Peer '{p.get('name')}' removed", "warn")
        self.refresh()

    def _rotate(self):
        p = self._selected()
        if not p:
            return
        if not messagebox.askyesno("Rotate keys",
                                   f"Generate a fresh keypair for '{p.get('name')}'?"):
            return
        self.store.rotate_peer_keys(p["id"])
        self.store.save()
        self.app.notify(f"Keys rotated for {p.get('name')}", "good")
        self.refresh()

    def _open_config(self):
        p = self._selected()
        if not p:
            return
        srv = self.store.server
        if not srv.get("endpoint_host"):
            messagebox.showwarning("Peers",
                                   "Set an endpoint host in the Tunnel Builder first.")
            return
        try:
            text = configs.build_client_config(srv, p, __title__)
        except ValueError as exc:
            messagebox.showwarning("Peers", str(exc))
            return
        ClientConfigDialog(self.app.root, p, srv, text)


class PeerDialog(tk.Toplevel):
    """Small modal for creating/editing a peer."""

    def __init__(self, parent, default_keepalive, name="", ip="",
                 suggest_ip=""):
        super().__init__(parent)
        self.title("Peer details")
        self.configure(bg=theme.PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        body = ttk.Frame(self, style="Card.TFrame", padding=18)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        self.v_name = tk.StringVar(value=name)
        self.v_ip = tk.StringVar(value=ip)
        self.v_ka = tk.StringVar(value=str(default_keepalive))

        ttk.Label(body, text="Device name", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(body, textvariable=self.v_name).grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(body, text="Tunnel IP", style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        iprow = ttk.Frame(body, style="Card.TFrame")
        iprow.grid(row=1, column=1, sticky="ew", pady=6)
        iprow.columnconfigure(0, weight=1)
        entry = ttk.Entry(iprow, textvariable=self.v_ip)
        entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(iprow, text="Auto", style="Ghost.TButton",
                   command=lambda: self.v_ip.set(suggest_ip)).grid(row=0, column=1, padx=(6, 0))
        hint_ip = suggest_ip or "(no free address - subnet may be full)"
        tk.Label(body, text=f"Recommended next free: {hint_ip}", bg=theme.PANEL,
                 fg=theme.MUTED, font=("Segoe UI", 8)).grid(
            row=2, column=1, sticky="w")

        ttk.Label(body, text="Persistent keepalive (s)", style="CardMuted.TLabel").grid(
            row=3, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Spinbox(body, from_=0, to=65535, textvariable=self.v_ka, width=8).grid(
            row=3, column=1, sticky="w", pady=6)

        btns = ttk.Frame(body, style="Card.TFrame")
        btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save peer", style="Accent.TButton",
                   command=self._ok).pack(side="right")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.v_name.set(name)
        entry.focus_set()
        self.wait_window()

    def _ok(self):
        name = self.v_name.get().strip()
        keep = self.v_ka.get().strip()
        if not name:
            messagebox.showwarning("Peer", "Device name is required.", parent=self)
            return
        if not keep.isdigit() or not 0 <= int(keep) <= 65535:
            messagebox.showwarning("Peer", "Keepalive must be 0-65535 seconds.",
                                   parent=self)
            return
        self.result = (name, self.v_ip.get().strip(), int(keep))
        self.destroy()


class ClientConfigDialog(tk.Toplevel):
    """Preview of a client .conf with its QR code and copy / save actions."""

    def __init__(self, parent, peer, srv, text):
        super().__init__(parent)
        self.title(f"Client config - {peer.get('name')}")
        self.configure(bg=theme.PANEL)
        self.geometry("880x560")
        self.transient(parent)
        self.grab_set()
        self.text = text

        note = tk.Label(self, text="Scan the QR in the official WireGuard app, "
                        "copy the config text, or save it as a .conf file for import.",
                        bg=theme.ACCENT_DIM, fg=theme.ACCENT, anchor="w", padx=14, pady=8,
                        font=("Segoe UI", 9))
        note.pack(fill="x")

        mid = ttk.Frame(self, style="Card.TFrame")
        mid.pack(fill="both", expand=True, padx=14, pady=12)
        mid.columnconfigure(0, weight=0)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

        qframe = ttk.Frame(mid, style="Card.TFrame")
        qframe.grid(row=0, column=0, sticky="n", padx=(0, 14))
        try:
            img = qr.qr_image(text, size=8)
            self._photo = ImageTk.PhotoImage(img)
            tk.Label(qframe, image=self._photo, bg=theme.PANEL).pack()
        except Exception:  # noqa: BLE001
            tk.Label(qframe, text="QR unavailable", bg=theme.PANEL,
                     fg=theme.MUTED).pack()
        tk.Label(qframe, text=peer.get("name"), bg=theme.PANEL, fg=theme.TEXT,
                 font=("Segoe UI", 10, "bold")).pack(pady=(8, 0))

        txt = tk.Text(mid, wrap="none", relief="flat", bg=theme.PANEL_ALT,
                      fg=theme.TEXT, insertbackground=theme.TEXT, font=theme.FONT_MONO,
                      padx=12, pady=10)
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.grid(row=0, column=1, sticky="nsew")
        hsb = ttk.Scrollbar(mid, orient="horizontal", command=txt.xview)
        hsb.grid(row=1, column=1, sticky="ew")
        vsb = ttk.Scrollbar(mid, orient="vertical", command=txt.yview)
        vsb.grid(row=0, column=2, sticky="ns")
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        bar = ttk.Frame(self, style="Card.TFrame")
        bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bar, text="Copy to clipboard", style="Accent.TButton",
                   command=self._copy).pack(side="left")
        ttk.Button(bar, text="Save .conf file", command=self._save).pack(side="left", padx=8)
        ttk.Button(bar, text="Close", style="Ghost.TButton",
                   command=self.destroy).pack(side="right")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.text)
        self.bell()

    def _save(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".conf",
            initialfile="client.conf", filetypes=[("WireGuard config", "*.conf")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.text)
        self.bell()