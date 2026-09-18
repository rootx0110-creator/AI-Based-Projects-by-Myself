"""gui/app.py — presentation layer (layer L4).

Colorful tabbed Tkinter UI. Owns memory.json / state.json persistence and
report export. All Tk calls happen on the main thread; capture runs on the
engine thread and communicates only via queue + events.
"""
from __future__ import annotations

import json
import os
import queue
import time
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core.filters import DisplayFilter
from core.packets import Packet, hexdump
from core.report import write_report
from core.sniffer import (ALL_INTERFACES, ALL_IFACE_LABEL, RawSocketSniffer,
                          interface_ip, list_ipv4_interfaces, local_ipv4s)
from core.stats import ProtocolStats

RUNTIME = Path(__file__).resolve().parent.parent / "runtime"

# ------------------------------------------------------------------ palette
C = {
    "bg":      "#0f1420",
    "panel":   "#161d2e",
    "panel2":  "#1b2338",
    "ink":     "#e8ecf4",
    "mut":     "#8b96ad",
    "cyan":    "#22d3ee",
    "green":   "#4ade80",
    "orange":  "#fb923c",
    "violet":  "#a78bfa",
    "pink":    "#f472b6",
    "red":     "#f87171",
}

PROTO_COLOR = {"TCP": C["cyan"], "UDP": C["green"], "ICMP": C["orange"],
               "OTHER": C["violet"]}

TABS = [
    ("capture", "🎛  Capture", C["cyan"]),
    ("packets", "📋  Packets", C["green"]),
    ("detail",  "🔍  Detail",  C["orange"]),
    ("stats",   "📊  Stats",   C["violet"]),
    ("report",  "📄  Report",  C["pink"]),
]

TABLE_CAP = 1000          # rows shown in the Treeview
BUFFER_CAP = 5000         # packets kept in RAM


class SnifferApp:
    # ------------------------------------------------------------ lifecycle
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Packet Sniffer — Raw Sockets")
        root.geometry("1280x800")
        root.minsize(1000, 640)
        root.configure(bg=C["bg"])

        # engine + data
        self.engine = RawSocketSniffer()
        self.stats = ProtocolStats()
        self.filter = DisplayFilter()
        self.packets: list[Packet] = []
        self.visible: list[Packet] = []
        self.selected: Packet | None = None
        self.paused = False
        self.phase = "idle"          # idle/capturing/paused/stopped/error
        self.session: dict = {}
        self.errors: list[str] = []
        self._stat_pulse = 0

        # persistence
        RUNTIME.mkdir(exist_ok=True)
        self.memory = self._load_json("memory.json", self._default_memory())
        self.state = self._load_json("state.json", self._default_state())

        # UI state vars — restore saved interface by matching its IP
        iface_entries = list_ipv4_interfaces()
        saved_ip = interface_ip(self.state.get("last_interface", ""))
        restored = next((e for e in iface_entries
                         if interface_ip(e) == saved_ip), None)
        if restored is None and saved_ip == ALL_INTERFACES:
            restored = ALL_IFACE_LABEL
        self.iface_var = StringVar(value=restored or iface_entries[0])
        self.filter_var = StringVar(value=self.state.get("filter", ""))
        self._quick = {p: BooleanVar(
            value=(p in self.state.get("quick_filters",
                                       ["TCP", "UDP", "ICMP", "OTHER"])))
            for p in ("TCP", "UDP", "ICMP", "OTHER")}

        self._build_style()
        self._build_layout()
        self._refresh_visible(rescroll=True)
        self._update_live()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()                 # start UI poll loop
        self._save_state()

    # ------------------------------------------------------------ persistence
    @staticmethod
    def _default_memory() -> dict:
        return {"version": 1, "session_count": 0, "total_packets_seen": 0,
                "total_bytes_seen": 0, "protocol_history": {},
                "top_talkers": [], "known_hosts": {}, "port_labels": {},
                "recent_filters": [], "notes": ""}

    @staticmethod
    def _default_state() -> dict:
        return {"version": 1, "phase": "idle", "session": {},
                "last_interface": "", "filter": "", "quick_filters": [],
                "stats_snapshot": {}, "last_report": {}, "errors": []}

    def _load_json(self, name: str, default: dict) -> dict:
        p = RUNTIME / name
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    default.update(data)
                    return default
        except (json.JSONDecodeError, OSError):
            pass
        return default

    def _save_json(self, name: str, data: dict) -> None:
        try:
            p = RUNTIME / name
            p.parent.mkdir(exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str),
                           encoding="utf-8")
            os.replace(tmp, p)       # atomic swap
        except OSError as exc:
            self.errors.append(f"save {name}: {exc}")

    def _save_memory(self) -> None:
        m = self.memory
        m["saved_at"] = datetime.now().isoformat(timespec="seconds")
        m["total_packets_seen"] = (m.get("total_packets_seen", 0)
                                   + self.stats.total_packets)
        m["total_bytes_seen"] = (m.get("total_bytes_seen", 0)
                                 + self.stats.total_bytes)
        for proto, n in self.stats.by_protocol.items():
            m["protocol_history"][proto] = \
                m["protocol_history"].get(proto, 0) + n
        talkers = [{"ip": ip, "packets": p, "bytes": b}
                   for ip, p, b in self.stats.top_talkers(10)]
        if talkers:
            m["top_talkers"] = talkers
        m["notes"] = self.notes.get("1.0", "end").strip()
        self._save_json("memory.json", m)

    def _save_state(self) -> None:
        self.state.update({
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "phase": self.phase,
            "session": self.session,
            "last_interface": self.iface_var.get(),
            "filter": self.filter_var.get(),
            "quick_filters": [p for p, v in self._quick.items() if v.get()],
            "stats_snapshot": self.stats.summary(),
            "errors": self.errors[-10:],
        })
        self._save_json("state.json", self.state)

    # ------------------------------------------------------------ UI build
    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=C["bg"], borderwidth=0,
                        tabmargins=[8, 8, 8, 0])
        style.configure("TNotebook.Tab", background=C["panel"],
                        foreground=C["mut"], padding=[18, 9],
                        font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", C["panel2"])],
                  foreground=[("selected", C["ink"])])
        style.configure("TFrame", background=C["bg"])
        style.configure("TLabel", background=C["bg"], foreground=C["ink"])
        style.configure("TButton", background=C["panel2"], foreground=C["ink"],
                        borderwidth=0, padding=8, font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", C["cyan"])],
                  foreground=[("active", "#06202a")])
        style.configure("TCombobox", fieldbackground=C["panel2"],
                        background=C["panel2"], foreground=C["ink"])
        style.configure("Treeview", background=C["panel"], foreground=C["ink"],
                        fieldbackground=C["panel"], rowheight=24,
                        borderwidth=0)
        style.configure("Treeview.Heading", background=C["panel2"],
                        foreground=C["mut"], font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#22d3ee33")])

    def _build_layout(self) -> None:
        header = self._header = self._frame(self.root)
        header.pack(fill="x", padx=14, pady=(12, 4))

        tk_emoji = self._label(header, "📡", C["cyan"],
                               ("Segoe UI Emoji", 18))
        tk_emoji.pack(side="left", padx=(2, 8))
        self._label(header, "Packet Sniffer", C["ink"],
                    ("Segoe UI", 17, "bold")).pack(side="left")
        self._label(header, "raw sockets · SIO_RCVALL", C["mut"],
                    ("Segoe UI", 9)).pack(side="right", padx=12)
        self.status_pill = self._label(header, "● IDLE", C["mut"],
                                       ("Segoe UI", 10, "bold"),
                                       bg=C["panel"], padx=14, pady=4)
        self.status_pill.pack(side="right")
        badge_text, badge_color = self._admin_badge_args()
        self._admin_badge = self._label(header, badge_text, badge_color,
                                        ("Segoe UI", 9, "bold"),
                                        bg=C["panel"], padx=12, pady=4)
        self._admin_badge.pack(side="right", padx=(0, 10))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=10)

        self.tab_capture = self._frame(self.notebook)
        self.tab_packets = self._frame(self.notebook)
        self.tab_detail = self._frame(self.notebook)
        self.tab_stats = self._frame(self.notebook)
        self.tab_report = self._frame(self.notebook)
        self.tab_colors: dict[str, str] = {}
        for tab, (key, label, color) in zip(
                (self.tab_capture, self.tab_packets, self.tab_detail,
                 self.tab_stats, self.tab_report), TABS):
            self.notebook.add(tab, text=label)
            self.tab_colors[key] = color

        self._build_capture_tab()
        self._build_packets_tab()
        self._build_detail_tab()
        self._build_stats_tab()
        self._build_report_tab()

    # small widget factories that default to the dark theme
    def _frame(self, parent, bg: str | None = None) -> "tk.Frame":
        import tkinter as tk
        return tk.Frame(parent, bg=bg or C["bg"])

    def _label(self, parent, text: str, fg: str, font, bg: str | None = None,
               **kw):
        import tkinter as tk
        return tk.Label(parent, text=text, fg=fg, font=font,
                        bg=bg or C["bg"], **kw)

    def _build_capture_tab(self) -> None:
        f = self.tab_capture
        card = self._frame(f, C["panel"])
        card.pack(fill="both", expand=True, padx=10, pady=10)

        self._label(card, "Capture control", C["cyan"],
                    ("Segoe UI", 13, "bold"), bg=C["panel"]).pack(
            anchor="w", padx=16, pady=(16, 2))
        self._label(card, "Bind the raw socket to one of this machine's IPv4 "
                          "interfaces. Windows requires administrator rights.",
                    C["mut"], ("Segoe UI", 9), bg=C["panel"]).pack(
            anchor="w", padx=16)

        row = self._frame(card, C["panel"])
        row.pack(fill="x", padx=16, pady=14)
        self._label(row, "Interface:", C["ink"], ("Segoe UI", 10),
                    bg=C["panel"]).pack(side="left")
        # Not readonly: users can also paste a specific local IP directly.
        self.iface_combo = ttk.Combobox(
            row, textvariable=self.iface_var,
            values=list_ipv4_interfaces(), width=48)
        self.iface_combo.pack(side="left", padx=8)
        ttk.Button(row, text="⟳ Refresh", command=self.refresh_interfaces)\
            .pack(side="left", padx=4)
        ttk.Button(row, text="▶ Start", command=self.start_capture)\
            .pack(side="left", padx=4)
        ttk.Button(row, text="⏸ Pause", command=self.toggle_pause)\
            .pack(side="left", padx=4)
        ttk.Button(row, text="⏹ Stop", command=self.stop_capture)\
            .pack(side="left", padx=4)

        self._label(card, "💡 Tips: run as Administrator (raw sockets need "
                          "elevation). 'ALL IPv4 interfaces' captures on "
                          "every adapter at once — use it if you are unsure "
                          "which IP belongs to your Wi-Fi. A marked UDP "
                          "self-test is sent on Start and must appear "
                          "within ~2 s on the adapter(s) you picked.",
                    C["orange"], ("Segoe UI", 9), bg=C["panel"],
                    wraplength=560, justify="left").pack(anchor="w", padx=16,
                                                         pady=(0, 10))

        live = self._frame(card, C["panel"])
        live.pack(fill="x", padx=16, pady=8)
        self.live_labels: dict[str, "tk.Label"] = {}
        for name, col in (("Packets", C["cyan"]), ("Bytes", C["green"]),
                          ("Pkt/s", C["orange"]), ("Dropped", C["red"])):
            box = self._frame(live, C["panel2"])
            box.pack(side="left", padx=5)
            box.configure(padx=14, pady=10)
            lbl = self._label(box, "0", col, ("Segoe UI", 15, "bold"),
                              bg=C["panel2"])
            lbl.pack()
            self._label(box, name, C["mut"], ("Segoe UI", 9),
                        bg=C["panel2"]).pack()
            self.live_labels[name] = lbl

        notes = tk_labelframe(card, " Operator notes (persisted to memory.json) ",
                              C["violet"])
        notes.pack(fill="both", expand=True, padx=16, pady=12)
        self.notes = ScrolledText(notes, bg=C["panel2"], fg=C["ink"],
                                  insertbackground=C["ink"], height=6,
                                  relief="flat", font=("Consolas", 10))
        self.notes.pack(fill="both", expand=True, padx=8, pady=8)
        self.notes.insert("1.0", self.memory.get("notes", ""))

    def _build_packets_tab(self) -> None:
        f = self.tab_packets
        bar = self._frame(f)
        bar.pack(fill="x", padx=10, pady=(8, 2))
        self._label(bar, "Filter:", C["ink"], ("Segoe UI", 10)).pack(side="left")
        self.filter_entry = tk_entry(bar, self.filter_var)
        self.filter_entry.pack(side="left", padx=8, ipady=5)
        ttk.Button(bar, text="Apply", command=self.apply_filter)\
            .pack(side="left")
        self.filter_lbl = self._label(bar, "", C["red"], ("Segoe UI", 9))
        self.filter_lbl.pack(side="left", padx=8)
        for proto, var in self._quick.items():
            tk_check(bar, proto, var, PROTO_COLOR[proto],
                     command=self.apply_filter).pack(side="left", padx=6)

        wrap = self._frame(f)
        wrap.pack(fill="both", expand=True, padx=10, pady=8)
        cols = ("time", "src", "dst", "proto", "len", "flags", "info")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=22)
        for cid, txt, w, anchor in (
                ("time", "Time", 95, "w"), ("src", "Source", 150, "w"),
                ("dst", "Destination", 150, "w"),
                ("proto", "Proto", 70, "center"), ("len", "Len", 65, "e"),
                ("flags", "Flags", 55, "center"), ("info", "Info", 520, "w")):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor=anchor)
        ys = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ys.pack(side="right", fill="y")

        for tag, color in (("tcp", C["cyan"]), ("udp", C["green"]),
                           ("icmp", C["orange"]), ("other", C["violet"])):
            self.tree.tag_configure(tag, foreground=color)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_packet)

        self._label(f, "Click a row to inspect it in the Detail tab",
                    C["mut"], ("Segoe UI", 9)).pack(anchor="w", padx=12,
                                                    pady=(0, 6))

    def _build_detail_tab(self) -> None:
        f = self.tab_detail
        self._label(f, "Packet detail", C["orange"],
                    ("Segoe UI", 13, "bold")).pack(anchor="w", padx=14,
                                                   pady=(10, 2))
        self.detail_summary = self._label(f, "No packet selected.", C["mut"],
                                          ("Segoe UI", 10))
        self.detail_summary.pack(anchor="w", padx=14)
        pane = self._frame(f)
        pane.pack(fill="both", expand=True, padx=10, pady=8)
        self.detail_tree = ttk.Treeview(pane, columns=("f", "v"),
                                        show="headings", height=14)
        self.detail_tree.heading("f", text="Field")
        self.detail_tree.heading("v", text="Value")
        self.detail_tree.column("f", width=220, anchor="w")
        self.detail_tree.column("v", width=520, anchor="w")
        self.detail_tree.pack(side="left", fill="both", expand=True)
        ys = ttk.Scrollbar(pane, orient="vertical",
                           command=self.detail_tree.yview)
        ys.pack(side="right", fill="y")
        self.detail_tree.configure(yscrollcommand=ys.set)
        self.hex_view = ScrolledText(pane, bg="#0b0f18", fg="#9fe8ff",
                                     insertbackground=C["ink"], relief="flat",
                                     font=("Consolas", 10), width=46)
        self.hex_view.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.hex_view.insert("1.0", "Select a packet in the Packets tab…")
        self.hex_view.config(state="disabled")

    def _build_stats_tab(self) -> None:
        f = self.tab_stats
        self._label(f, "Live statistics", C["violet"],
                    ("Segoe UI", 13, "bold")).pack(anchor="w", padx=14,
                                                   pady=(10, 4))
        self.stats_area = self._frame(f)
        self.stats_area.pack(fill="both", expand=True, padx=14, pady=6)

    def _build_report_tab(self) -> None:
        f = self.tab_report
        card = self._frame(f, C["panel"])
        card.pack(fill="both", expand=True, padx=10, pady=10)
        self._label(card, "HTML report", C["pink"], ("Segoe UI", 13, "bold"),
                    bg=C["panel"]).pack(anchor="w", padx=16, pady=(16, 2))
        self._label(card, "Generates a colorful, self-contained HTML report "
                          "(KPIs, protocol mix, top talkers, packet table, "
                          "hex dump of the focus packet).",
                    C["mut"], ("Segoe UI", 9), bg=C["panel"], wraplength=620,
                    justify="left").pack(anchor="w", padx=16)
        btns = self._frame(card, C["panel"])
        btns.pack(anchor="w", padx=16, pady=14)
        ttk.Button(btns, text="⬇  Save report as…",
                   command=self.export_report).pack(side="left", padx=4)
        ttk.Button(btns, text="🌐  Build & open in browser",
                   command=lambda: self.export_report(open_browser=True))\
            .pack(side="left", padx=4)
        ttk.Button(btns, text="💾  Save session (memory + state)",
                   command=self._save_all).pack(side="left", padx=4)
        self.report_lbl = self._label(card, "", C["green"], ("Segoe UI", 10),
                                      bg=C["panel"])
        self.report_lbl.pack(anchor="w", padx=16, pady=4)
        err = tk_labelframe(card, " Recent errors ", C["red"])
        err.pack(fill="both", expand=True, padx=16, pady=12)
        self.err_view = ScrolledText(err, bg=C["panel2"], fg=C["ink"],
                                     insertbackground=C["ink"], relief="flat",
                                     font=("Consolas", 9), height=8)
        self.err_view.pack(fill="both", expand=True, padx=8, pady=8)

    # ------------------------------------------------------------ actions
    def refresh_interfaces(self) -> None:
        """Re-scan adapters (e.g. after connecting/disconnecting Wi-Fi)."""
        entries = list_ipv4_interfaces()
        self.iface_combo["values"] = entries
        cur = self.iface_var.get().strip()
        if (cur not in entries and interface_ip(cur) not in local_ipv4s()
                and interface_ip(cur) != ALL_INTERFACES):
            self.iface_var.set(entries[0])

    def start_capture(self) -> None:
        if self.engine.running:
            return
        self.refresh_interfaces()
        entry = self.iface_var.get().strip()
        host = interface_ip(entry)          # "1.2.3.4  —  Wi-Fi" -> "1.2.3.4"
        if host != ALL_INTERFACES and host not in local_ipv4s():
            messagebox.showerror(
                "Not a local address",
                f"{host} is not one of this PC's own IPv4 addresses.\n\n"
                "A raw socket can only bind to a local address. Pick one "
                "from the list, or choose 'ALL IPv4 interfaces'.")
            return
        ok = self.engine.start(host)
        if not ok:
            err = self.engine.last_error or "unknown error"
            messagebox.showerror("Raw socket error", err)
            self.errors.append(err)
            self.phase = "error"
            self._set_status("● ERROR", C["red"])
            self._save_state()
            return
        self.packets.clear()
        self.visible.clear()
        self.tree.delete(*self.tree.get_children())
        self.stats.reset()
        self.paused = False
        self.phase = "capturing"
        bound = self.engine.bound_targets
        self.session = {
            "id": f"s-{datetime.now():%Y%m%d-%H%M%S}",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "interface": "+".join(bound) or host,
            "filter": self.filter_var.get(), "drops": 0,
        }
        self.memory["session_count"] = self.memory.get("session_count", 0) + 1
        self._set_status(
            "● CAPTURING", C["green"])
        if len(bound) > 1:
            self._set_status(f"● CAPTURING ({len(bound)} adapters)",
                             C["green"])
        self._save_state()
        # Capture self-test: marked UDP datagrams to the bound address(es);
        # they must appear within ~2 s if the raw socket is truly working.
        for ip in bound:
            self.root.after(400, lambda ip=ip: RawSocketSniffer.send_probe(ip))

    def stop_capture(self) -> None:
        if not self.engine.running:
            return
        self.engine.stop()
        self.phase = "stopped"
        self.session["ended_at"] = datetime.now().isoformat(timespec="seconds")
        self.session["drops"] = self.engine.dropped
        self._set_status("● STOPPED", C["orange"])
        self._save_memory()
        self._save_state()

    def toggle_pause(self) -> None:
        if self.phase not in ("capturing", "paused"):
            return
        self.paused = not self.paused
        self.phase = "paused" if self.paused else "capturing"
        self._set_status("● PAUSED" if self.paused else "● CAPTURING",
                         C["pink"] if self.paused else C["green"])
        self._save_state()

    def apply_filter(self) -> None:
        ok = self.filter.set(self.filter_var.get())
        self.filter_lbl.config(text="" if ok else f"⚠ {self.filter.error}")
        self._refresh_visible(rescroll=True)
        self._save_state()

    def export_report(self, open_browser: bool = False) -> None:
        if not self.packets:
            if not messagebox.askyesno(
                    "Empty capture",
                    "No packets captured yet.\nGenerate report anyway?"):
                return
        default = f"sniffer_report_{datetime.now():%Y%m%d_%H%M%S}.html"
        path = filedialog.asksaveasfilename(
            defaultextension=".html", initialfile=default,
            filetypes=[("HTML report", "*.html")])
        if not path:
            return
        out = write_report(path, self.packets, self.stats, self.session,
                           memory=self.memory, state=self.state,
                           selected_index=self.selected.index
                           if self.selected else None)
        self.state["last_report"] = {
            "path": str(out),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "packets": len(self.packets)}
        self.report_lbl.config(text=f"✔ Report written: {out}")
        self._save_state()
        if open_browser:
            import webbrowser
            webbrowser.open(Path(out).as_uri())

    def _save_all(self) -> None:
        self._save_memory()
        self._save_state()
        self.report_lbl.config(text="✔ memory.json + state.json saved")

    # ------------------------------------------------------------ data pump
    def _tick(self) -> None:
        """Main-loop poll: drain queue in batches, refresh UI."""
        try:
            got = 0
            while got < 400:                    # batch limit per tick
                try:
                    pkt = self.engine.queue.get_nowait()
                except queue.Empty:
                    break
                got += 1
                self.packets.append(pkt)
                self.stats.add(pkt)
            if len(self.packets) > BUFFER_CAP:
                del self.packets[:BUFFER_CAP // 2]
            # surface engine problems (dead thread, firewall blocks, ...)
            while True:
                try:
                    err = self.engine.error_queue.get_nowait()
                except queue.Empty:
                    break
                self.errors.append(err)
                self.err_view.config(state="normal")
                self.err_view.insert("1.0", f"[{datetime.now():%H:%M:%S}] {err}\n")
                self.err_view.config(state="disabled")
                self._set_status("● ERROR", C["red"])
            if got:
                if not self.paused:
                    self._refresh_visible()
                self._update_live()
                self._draw_stats()
        except Exception:
            self.errors.append(traceback.format_exc(limit=3))

        self._stat_pulse += 1
        if self._stat_pulse >= 50 and self.phase == "capturing":
            self._stat_pulse = 0
            self._save_state()                 # heartbeat every ~5 s

        self.root.after(100, self._tick)

    def _passes(self, pkt: Packet) -> bool:
        if not self.filter.match(pkt):
            return False
        enabled = [p for p, v in self._quick.items() if v.get()]
        return not enabled or pkt.protocol in enabled

    def _refresh_visible(self, rescroll: bool = False) -> None:
        self.visible = [p for p in self.packets if self._passes(p)]
        self.tree.delete(*self.tree.get_children())
        tagmap = {"TCP": "tcp", "UDP": "udp", "ICMP": "icmp"}
        for p in self.visible[-TABLE_CAP:]:
            tag = tagmap.get(p.protocol, "other")
            self.tree.insert("", "end", values=(
                p.time_str, p.src_ip, p.dst_ip, p.protocol, p.length,
                p.flags, p.info), tags=(tag,))
        if rescroll:
            self.tree.yview_moveto(1.0)

    def _update_live(self) -> None:
        v = {"Packets": f"{self.stats.total_packets:,}",
             "Bytes": f"{self.stats.total_bytes / 1024:.1f} KB",
             "Pkt/s": f"{self.stats.pps():.1f}",
             "Dropped": str(self.engine.dropped)}
        for name, lbl in self.live_labels.items():
            lbl.config(text=v.get(name, "-"))

    def _draw_stats(self) -> None:
        for w in self.stats_area.winfo_children():
            w.destroy()

        def bar_row(parent, label, frac, color, value, row):
            self._label(parent, label[:38], C["ink"], ("Segoe UI", 9))\
                .grid(row=row, column=0, sticky="w", pady=2)
            canvas = tk_canvas(parent, 300, 14)
            canvas.create_rectangle(0, 0, max(4, int(300 * frac)), 14,
                                    fill=color, width=0)
            canvas.grid(row=row, column=1, padx=8, pady=2)
            self._label(parent, value, C["mut"], ("Segoe UI", 9))\
                .grid(row=row, column=2, sticky="w", pady=2)

        grid = self._frame(self.stats_area)
        grid.pack(anchor="w")

        def section(title, color, start_row, items_draw):
            self._label(grid, title, color, ("Segoe UI", 9, "bold"))\
                .grid(row=start_row, column=0, columnspan=3, sticky="w",
                      pady=(14, 2))
            return start_row + 1

        row = section("PROTOCOLS", C["violet"], 0, None)
        protos = self.stats.protocol_counts()
        peak = max((n for _p, n in protos), default=1) or 1
        for proto, n in protos:
            bar_row(grid, proto, n / peak,
                    PROTO_COLOR.get(proto, C["violet"]), f"{n:,}", row)
            row += 1

        row = section("TOP TALKERS (bytes)", C["cyan"], row + 1, None)
        talkers = self.stats.top_talkers(6)
        tpeak = max((b for _i, _p, b in talkers), default=1) or 1
        for ip, pkts, b in talkers:
            bar_row(grid, ip, b / tpeak, C["cyan"],
                    f"{pkts:,} pkts · {b / 1024:.0f} KB", row)
            row += 1

        row = section("TOP CONVERSATIONS", C["green"], row + 1, None)
        convos = self.stats.top_conversations(6)
        cpeak = max((b for _c, b in convos), default=1) or 1
        for convo, b in convos:
            bar_row(grid, convo, b / cpeak, C["green"], f"{b / 1024:.0f} KB",
                    row)
            row += 1

    # ------------------------------------------------------------ selection
    def _on_select_packet(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        match = next((p for p in self.visible
                      if p.time_str == values[0] and p.src_ip == values[1]
                      and p.info == values[6]), None)
        if not match:
            return
        self.selected = match
        self.notebook.select(self.tab_detail)
        self.detail_summary.config(
            text=f"Packet #{match.index} — {match.info}",
            fg=PROTO_COLOR.get(match.protocol, C["ink"]))
        fields = [
            ("No.", match.index), ("Time", match.time_str),
            ("Source", f"{match.src_ip}:{match.src_port}"),
            ("Destination", f"{match.dst_ip}:{match.dst_port}"),
            ("Protocol", match.protocol), ("TCP flags", match.flags or "-"),
            ("TTL", match.ttl), ("Length", f"{match.length} bytes"),
            ("Info", match.info)]
        self.detail_tree.delete(*self.detail_tree.get_children())
        for k, v in fields:
            self.detail_tree.insert("", "end", values=(k, v))
        self.hex_view.config(state="normal")
        self.hex_view.delete("1.0", "end")
        self.hex_view.insert("1.0", hexdump(match.raw, max_lines=256))
        self.hex_view.config(state="disabled")

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _is_admin() -> bool:
        import sys
        if sys.platform != "win32":
            return True
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _admin_badge_args(self) -> tuple[str, str]:
        if self._is_admin():
            return "(admin ✓)", C["green"]
        return "⚠ not admin", C["red"]

    def _set_status(self, text: str, color: str) -> None:
        self.status_pill.config(text=text, fg=color)

    def _on_close(self) -> None:
        try:
            self.engine.stop()
            self._save_memory()
            self._save_state()
        finally:
            self.root.destroy()

    # -------------------------------------------------- smoke-test helper
    def run_ui(self, seconds: float = 1.0) -> int:
        """Pump the Tk event loop briefly (used by the smoke test)."""
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.02)
        return len(self.packets)


# ------------------------------------------------- small tk helper builders
def _tk():
    import tkinter as tk
    return tk


def tk_labelframe(parent, text: str, fg: str):
    tk = _tk()
    return tk.LabelFrame(parent, text=text, fg=fg, bg=C["panel"],
                         font=("Segoe UI", 9, "bold"), bd=0)


def tk_check(parent, text: str, var, color: str, command):
    tk = _tk()
    return tk.Checkbutton(parent, text=text, variable=var, command=command,
                          bg=C["bg"], fg=color, activebackground=C["bg"],
                          activeforeground=color, selectcolor=C["panel2"],
                          bd=0, font=("Segoe UI", 9, "bold"))


def tk_canvas(parent, w: int, h: int):
    tk = _tk()
    return tk.Canvas(parent, width=w, height=h, bg=C["panel2"],
                     highlightthickness=0)


def tk_entry(parent, textvariable):
    tk = _tk()
    return tk.Entry(parent, textvariable=textvariable, bg=C["panel2"],
                    fg=C["ink"], insertbackground=C["ink"], relief="flat",
                    width=46)


def launch() -> None:
    root = Tk()
    SnifferApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
