"""Three notebook pages: SubnetCalculator, VlsmPlanner, Reports."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import core
from . import theme as T
from . import report as RPT
from .widgets import (Card, Metric, ResultTable, danger_button, ghost_button,
                      primary_button)

MAX_ONSCREEN_ROWS = 256


# --------------------------------------------------------------------------
# Helper shared by pages
# --------------------------------------------------------------------------

def _block_for_hosts(req: int) -> tuple:
    block = 1
    while block < req + 2:
        block <<= 1
    pfx = 32 - block.bit_length() + 1
    return block, pfx


def _usable_for_prefix(prefix: int, block: int = None) -> int:
    if block is None:
        block = 1 << (32 - prefix) if prefix < 32 else 1
    return block if prefix >= 31 else block - 2


# --------------------------------------------------------------------------
# Tab 1 — Subnet Calculator
# --------------------------------------------------------------------------

class SubnetPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self._syncing = False
        self._last_subnets_meta = {}

        self.ip_var = tk.StringVar(value="192.168.1.10")
        self.prefix_var = tk.StringVar(value="26")
        self.mask_var = tk.StringVar(value="255.255.255.192")
        self.hosts_var = tk.StringVar(value="62")
        self.subnets_var = tk.StringVar(value="4")
        self.mode_var = tk.StringVar(value="Prefix")

        self._build()
        self._derive_from_prefix(26)

    # ---- layout ---------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)

        card = Card(self, title="Input")
        card.grid(row=0, column=0, sticky="ew")
        card.body.columnconfigure(0, weight=1)

        row1 = tk.Frame(card.body, bg=T.PANEL)
        row1.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for c in range(2):
            row1.columnconfigure(c, weight=1)

        ip_frame = tk.Frame(row1, bg=T.PANEL)
        ip_frame.pack(fill="x", expand=True)
        ttk.Label(ip_frame, text="IP address", style="Panel.TLabel").pack(anchor="w")
        self.ip_entry = ttk.Entry(ip_frame, textvariable=self.ip_var, width=26,
                                  font=T.FONT_MONO)
        self.ip_entry.pack(fill="x", pady=(3, 0))
        self.ip_entry.bind("<Return>", lambda e: self.calculate())

        pfx_frame = tk.Frame(row1, bg=T.PANEL)
        pfx_frame.pack(fill="x", expand=True)
        ttk.Label(pfx_frame, text="Prefix length", style="Panel.TLabel").pack(anchor="w")
        self.prefix_spin = ttk.Spinbox(pfx_frame, from_=0, to=32,
                                       textvariable=self.prefix_var, width=8,
                                       font=T.FONT_MONO)
        self.prefix_spin.set = lambda v: None
        self.prefix_spin.pack(anchor="w", pady=(3, 0))
        self.prefix_var.trace_add("write", self._on_prefix_var)

        row2 = tk.Frame(card.body, bg=T.PANEL)
        row2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(row2, text="Express the subnet as:",
                  style="MetricKey.TLabel").pack(side="left", padx=(0, 14))

        self.mask_combo = ttk.Combobox(row2, textvariable=self.mask_var, width=19,
                                       state="readonly", values=self._mask_options(),
                                       font=T.FONT_MONO)
        self.mask_combo.pack(side="left", padx=(0, 12))
        self.mask_combo.bind("<<ComboboxSelected>>", self._on_mask_selected)

        self.hosts_entry = ttk.Entry(row2, textvariable=self.hosts_var, width=8,
                                     font=T.FONT_MONO)
        self.hosts_entry.pack(side="left", padx=(0, 12))
        self.hosts_var.trace_add("write", self._on_hosts_var)

        self.subnets_entry = ttk.Entry(row2, textvariable=self.subnets_var,
                                       width=8, font=T.FONT_MONO)
        self.subnets_entry.pack(side="left")
        self.subnets_var.trace_add("write", self._on_subnets_var)

        row3 = tk.Frame(card.body, bg=T.PANEL)
        row3.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(row3, text="The highlighted field drives the calculation; the "
                             "others update automatically.",
                  style="OnBgMuted.TLabel").pack(side="left")

        btns = tk.Frame(card.body, bg=T.PANEL)
        btns.grid(row=3, column=0, sticky="ew")
        primary_button(btns, "Calculate", command=self.calculate).pack(side="left")
        ghost_button(btns, "Show all subnets",
                     command=self.list_subnets).pack(side="left", padx=(10, 0))

        # ---- results -----------------------------------------------------
        self.result_card = Card(self, title="Subnet details")
        self.result_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self.result_card.body.columnconfigure(1, weight=2)

        metrics_left = tk.Frame(self.result_card.body, bg=T.PANEL)
        metrics_left.grid(row=0, column=0, sticky="n")
        metrics_right = tk.Frame(self.result_card.body, bg=T.PANEL)
        metrics_right.grid(row=0, column=1, sticky="n", padx=(28, 0))

        self.metrics = {}
        pairs = [
            ("Network", "network"), ("Broadcast", "broadcast"),
            ("First usable", "first_usable"), ("Last usable", "last_usable"),
            ("Usable hosts", "usable_hosts"), ("Total addresses", "total_addresses"),
            ("Subnet mask", "mask"), ("Wildcard mask", "wildcard"),
        ]
        for i, (label, key) in enumerate(pairs):
            parent = metrics_left if i < 4 else metrics_right
            r, c = (i % 4) if i < 4 else (i - 4), 0
            m = Metric(parent, label, "–")
            m.grid(row=r, column=c, sticky="w", padx=(0, 26), pady=4)
            self.metrics[key] = m

        self.note_label = ttk.Label(self.result_card.body, text="",
                                    style="Muted.TLabel", wraplength=600)
        self.note_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

        # --------- binary map ---------------------------------------------
        self.map_card = Card(self, title="32-bit address map — network / host bits")
        self.map_card.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.map_card.body.columnconfigure(0, weight=1)
        self.map_canvas = tk.Canvas(self.map_card.body, bg=T.PANEL, height=64,
                                    highlightthickness=0)
        self.map_canvas.grid(row=0, column=0, sticky="ew")
        self.map_canvas.bind("<Configure>", lambda e: self.redraw_map())
        legend = tk.Frame(self.map_card.body, bg=T.PANEL)
        legend.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self._swatch(legend, T.ACCENT, "Network bits (prefix)")
        self._swatch(legend, T.TEAL, "Host bits")

        self.map_binary = "0" * 32
        self.map_prefix = 0

        # --------- derived subnets table -----------------------------------
        self.list_card = Card(self, title="Derived subnets (fixed length)")
        self.list_card.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.table = ResultTable(self.list_card.body, height=10,
                                 columns=["#", "Network", "First usable",
                                          "Last usable", "Broadcast", "Mask",
                                          "Usable"],
                                 mono_columns=("Network", "First usable",
                                               "Last usable", "Broadcast",
                                               "Mask"))
        self.table.pack(fill="both", expand=True)
        self.list_note = ttk.Label(self.list_card.body, text="No table generated yet.",
                                   style="Muted.TLabel")
        self.list_note.pack(anchor="w", pady=(8, 0))

    def _swatch(self, parent, color, text):
        f = tk.Frame(parent, bg=T.PANEL)
        f.pack(side="left", padx=(0, 18))
        tk.Label(f, bg=color, width=2, height=1).pack(side="left")
        ttk.Label(f, text=text, style="Muted.TLabel").pack(side="left", padx=(6, 0))

    @staticmethod
    def _mask_options():
        return [core.prefix_to_mask(p) for p in range(33)]

    # ---- linking the four lenses ----------------------------------------
    def _class_default(self) -> int:
        try:
            return core.ip_class(core.ip_to_int(self.ip_var.get()))["default_prefix"]
        except ValueError:
            return 24

    def _on_prefix_var(self, *_):
        if self._syncing:
            return
        try:
            p = int(self.prefix_var.get())
        except (ValueError, TypeError):
            return
        if core.validate_prefix(p):
            self._derive_from_prefix(p)

    def _on_mask_selected(self, *_):
        if self._syncing:
            return
        try:
            p = core.mask_to_prefix(self.mask_var.get())
        except ValueError:
            return
        self._derive_from_prefix(p)

    def _on_hosts_var(self, *_):
        if self._syncing:
            return
        raw = self.hosts_var.get().strip()
        if not raw.isdigit():
            return
        h = int(raw)
        if 1 <= h <= (1 << 30):
            self._derive_from_prefix(core.prefix_from_hosts(h))

    def _on_subnets_var(self, *_):
        if self._syncing:
            return
        raw = self.subnets_var.get().strip()
        if not raw.isdigit():
            return
        n = int(raw)
        if n < 1:
            return
        try:
            borrow = core.prefix_from_subnets(n)
        except ValueError:
            return
        p = self._class_default() + borrow
        if self._class_default() >= 24 and p <= 32:
            self._derive_from_prefix(p)

    def _derive_from_prefix(self, p: int):
        self._syncing = True
        try:
            self.prefix_var.set(str(p))
            self.mask_var.set(core.prefix_to_mask(p))
            self.hosts_var.set(str(_usable_for_prefix(p)))
            default = self._class_default()
            self.subnets_var.set(str(1 << (p - default) if p >= default else 1))
            self.mode_var.set("Prefix")
        finally:
            self._syncing = False

    # ---- actions ---------------------------------------------------------
    def calculate(self, *_):
        ip = self.ip_var.get().strip()
        if not core.validate_ip(ip):
            self.app.status("Invalid IP address.", kind="error")
            return
        try:
            p = int(self.prefix_var.get())
        except ValueError:
            self.app.status("Invalid prefix.", kind="error")
            return
        try:
            s = core.calculate_subnet(ip, p)
        except ValueError as e:
            self.app.status(str(e), kind="error")
            return

        for key, m in self.metrics.items():
            m.set_text(str(s[key]))
        cls = s["class"]
        extra = []
        if s.get("is_subnet_of_classful"):
            extra.append(f"Classful {cls} /{s['class_default_prefix']} block → "
                         f"{s['subnets_in_class']} subnets")
        else:
            extra.append(f"Class {cls} default /{s['class_default_prefix']}")
        extra.append(f"Usable hosts = {s['usable_hosts']:,.0f} "
                     f"(2^{s['host_bits']} − 2" +
                     (")" if p not in (31, 32) else " per RFC 3021)"))
        self.note_label.configure(text=" · ".join(extra))

        self.map_binary = s["ip_binary"]
        self.map_prefix = p
        self.redraw_map()

        self.app.current_subnet = s
        self.table.clear()
        self.list_note.configure(text="Show all subnets to populate this table.")
        self.app.status(f"Subnet {s['network']}/{p} calculated — "
                        f"{s['usable_hosts']:,} usable hosts.", kind="ok")

    def redraw_map(self):
        c = self.map_canvas
        c.delete("all")
        w = max(c.winfo_width(), 300)
        cell = max(13, int((w - 40 - 4 * 10) / 38))
        gap, sep, pad = 3, 12, 12
        x = pad
        binary = self.map_binary
        pfx = self.map_prefix
        for i in range(32):
            bit = binary[i] if i < len(binary) else "0"
            if bit == "1":
                fill, fg = T.ACCENT, "#FFFFFF"
            else:
                fill, fg = T.TEAL, "#FFFFFF"
            x0, y0 = x, 8
            x1, y1 = x + cell, 8 + cell
            c.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#FFFFFF", width=2)
            c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=bit, fill=fg,
                          font=T.FONT_MAP)
            x += cell + gap
            if i in (7, 15, 23):
                x += sep

    # ---- derived subnets --------------------------------------------------
    def list_subnets(self):
        s = self.app.current_subnet
        if not s:
            self.app.status("Calculate a subnet first.", kind="warn")
            return
        p = s["prefix"]
        try:
            result = core.derive_subnets(s["network"], p, max_rows=MAX_ONSCREEN_ROWS)
        except ValueError as e:
            self.app.status(str(e), kind="error")
            return
        rows = [{"#": r["index"], "Network": r["network"], "First usable": r["first"],
                 "Last usable": r["last"], "Broadcast": r["broadcast"],
                 "Mask": r["mask"], "Usable": r["usable"]} for r in result["subnets"]]
        self.table.populate(rows, ["#", "Network", "First usable", "Last usable",
                                   "Broadcast", "Mask", "Usable"])
        if result["truncated"]:
            self.list_note.configure(
                text=f"Showing the first {len(rows)} of {result['total']:,} subnets. "
                     f"The HTML report includes all of them.")
        else:
            self.list_note.configure(
                text=f"All {result['total']:,} subnets shown.")
        self._last_subnets_meta = {"list": result["subnets"],
                                   "total": result["total"],
                                   "truncated": result["truncated"]}
        s["_subnets_table"] = result["subnets"]
        s["_total_count"] = result["total"]
        self.app.status(f"{result['total']:,} subnets derived.", kind="ok")


# --------------------------------------------------------------------------
# Tab 2 — VLSM Planner
# --------------------------------------------------------------------------

class VlsmPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.segments = []  # list of {"name": str, "hosts": int}

        self.base_ip_var = tk.StringVar(value="10.10.0.0")
        self.base_prefix_var = tk.StringVar(value="24")
        self.seg_name_var = tk.StringVar()
        self.seg_hosts_var = tk.StringVar(value="50")

        self.columnconfigure(0, weight=1)
        self._build()
        self._update_capacity()
        self.base_prefix_var.trace_add("write", lambda *_: self._update_capacity())

    # ---- layout ---------------------------------------------------------
    def _build(self):
        base = Card(self, title="Base network")
        base.grid(row=0, column=0, sticky="ew")
        f = base.body
        ttk.Label(f, text="Network", style="Panel.TLabel").grid(row=0, column=0,
                                                                sticky="w")
        ttk.Entry(f, textvariable=self.base_ip_var, width=20,
                  font=T.FONT_MONO).grid(row=1, column=0, sticky="w", padx=(0, 16))
        ttk.Label(f, text="Prefix", style="Panel.TLabel").grid(row=0, column=1,
                                                               sticky="w")
        ttk.Spinbox(f, from_=1, to=29, textvariable=self.base_prefix_var,
                    width=7, font=T.FONT_MONO).grid(row=1, column=1, sticky="w")
        ttk.Label(f, text="", style="Panel.TLabel").grid(row=0, column=2)
        self.capacity_label = ttk.Label(f, text="", style="MetricValue.TLabel")
        self.capacity_label.grid(row=1, column=2, sticky="w", padx=(22, 0))

        # -- segment editor -------------------------------------------------
        ed = Card(self, title="Required segments")
        ed.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        f = ed.body
        f.columnconfigure(0, weight=1)

        inp = tk.Frame(f, bg=T.PANEL)
        inp.grid(row=0, column=0, sticky="ew")
        ttk.Label(inp, text="Segment name", style="Panel.TLabel").pack(side="left")
        self.name_entry = ttk.Entry(inp, textvariable=self.seg_name_var, width=24)
        self.name_entry.pack(side="left", padx=(0, 14))
        ttk.Label(inp, text="Usable hosts needed", style="Panel.TLabel").pack(side="left")
        self.hosts_entry = ttk.Entry(inp, textvariable=self.seg_hosts_var, width=8)
        self.hosts_entry.pack(side="left", padx=(0, 14))
        primary_button(inp, "Add segment", command=self.add_segment).pack(side="left")

        btns = tk.Frame(f, bg=T.PANEL)
        btns.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        ghost_button(btns, "Remove selected", command=self.remove_selected).pack(side="left")
        ghost_button(btns, "Clear all", command=self.clear_segments).pack(side="left", padx=(8, 0))
        ghost_button(btns, "Example data", command=self.load_sample).pack(side="left", padx=(8, 0))
        ghost_button(btns, "Import JSON", command=self.import_json).pack(side="left", padx=(8, 0))
        ghost_button(btns, "Export JSON", command=self.export_json).pack(side="left", padx=(8, 0))

        self.seg_table = ResultTable(f, height=6,
                                     columns=["Segment", "Usable hosts",
                                              "Block size", "Prefix"],
                                     mono_columns=())
        self.seg_table.grid(row=2, column=0, sticky="nsew")
        self.seg_summary = ttk.Label(f, text="0 segments · 0 hosts required",
                                     style="Muted.TLabel")
        self.seg_summary.grid(row=3, column=0, sticky="w", pady=(8, 0))

        # -- plan ------------------------------------------------------------
        plan = Card(self, title="VLSM allocation — largest demand first")
        plan.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        f = plan.body
        f.columnconfigure(0, weight=1)
        alloc_row = tk.Frame(f, bg=T.PANEL)
        alloc_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        primary_button(alloc_row, "Allocate (VLSM)", command=self.allocate).pack(side="left")
        self.plan_summary = ttk.Label(alloc_row, text="", style="MetricValue.TLabel")
        self.plan_summary.pack(side="left", padx=(18, 0))

        self.plan_table = ResultTable(
            f, height=10,
            columns=["Segment", "Req hosts", "Prefix", "Block",
                     "Network", "First usable", "Last usable", "Broadcast", "Mask",
                     "Usable"],
            mono_columns=("Network", "First usable", "Last usable", "Broadcast", "Mask"))
        self.plan_table.grid(row=1, column=0, sticky="nsew")
        self.plan_warning = ttk.Label(f, text="", style="Muted.TLabel", wraplength=900)
        self.plan_warning.grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.rowconfigure(3, weight=1)

    # ---- capacity ---------------------------------------------------------
    def _update_capacity(self):
        try:
            p = int(self.base_prefix_var.get())
            net = core.calculate_subnet(self.base_ip_var.get(), p)
            self.capacity_label.configure(
                text=f"Capacity: {net['total_addresses']:,} addresses "
                     f"(usable {net['usable_hosts']:,})")
        except ValueError:
            self.capacity_label.configure(text="Capacity: —")

    # ---- segment list -------------------------------------------------------
    def add_segment(self):
        if not core.validate_ip(self.base_ip_var.get()):
            self.app.status("Base network IP is not valid.", kind="error")
            return
        name = self.seg_name_var.get().strip()
        if not name:
            self.app.status("Segment name is required.", kind="warn")
            return
        raw = self.seg_hosts_var.get().strip()
        if not raw.isdigit() or int(raw) < 1:
            self.app.status("Usable hosts must be a positive integer.", kind="warn")
            return
        self.segments.append({"name": name, "hosts": int(raw)})
        self.seg_name_var.set("")
        self.seg_hosts_var.set("50")
        self.refresh_segments()
        self.name_entry.focus_set()
        self.app.status(f"Segment '{name}' added.", kind="ok")

    def remove_selected(self):
        iids = self.seg_table.selected_iids()
        for iid in reversed(sorted(iids, key=int)):
            idx = int(iid)
            if 0 <= idx < len(self.segments):
                self.segments.pop(idx)
        self.refresh_segments()

    def clear_segments(self):
        self.segments.clear()
        self.refresh_segments()

    def load_sample(self):
        self.segments = [
            {"name": "Finance floor", "hosts": 120},
            {"name": "Marketing LAN", "hosts": 30},
            {"name": "HR department", "hosts": 15},
            {"name": "Guest Wi-Fi", "hosts": 8},
            {"name": "Management", "hosts": 3},
        ]
        self.refresh_segments()

    def import_json(self):
        path = filedialog.askopenfilename(
            title="Import segments", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                data = data.get("segments", [])
            self.segments = [{"name": str(d.get("name", "")),
                              "hosts": int(d.get("hosts", d.get("required_hosts", 0)))}
                             for d in data]
            self.refresh_segments()
            self.app.status("Segments imported.", kind="ok")
        except (json.JSONDecodeError, ValueError, KeyError, OSError) as e:
            self.app.status(f"Import failed: {e}", kind="error")

    def export_json(self):
        if not self.segments:
            self.app.status("Nothing to export.", kind="warn")
            return
        path = filedialog.asksaveasfilename(
            title="Export segments", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialfile="vlsm_segments.json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"segments": self.segments}, fh, indent=2)
        self.app.status(f"Segments exported to {path}", kind="ok")

    def refresh_segments(self):
        rows = []
        for seg in self.segments:
            block, pfx = _block_for_hosts(seg["hosts"])
            rows.append({"Segment": seg["name"], "Usable hosts": seg["hosts"],
                         "Block size": block, "Prefix": f"/{pfx}"})
        self.seg_table.populate(rows, ["Segment", "Usable hosts", "Block size", "Prefix"])
        total = sum(s["hosts"] for s in self.segments)
        self.seg_summary.configure(
            text=f"{len(self.segments)} segment(s) · {total:,} hosts required")

    # ---- allocation ----------------------------------------------------------
    def allocate(self):
        if not core.validate_ip(self.base_ip_var.get()):
            self.app.status("Base network IP is not valid.", kind="error")
            return
        try:
            pfx = int(self.base_prefix_var.get())
        except ValueError:
            self.app.status("Invalid base prefix.", kind="error")
            return
        if not self.segments:
            self.app.status("Add segments before allocating.", kind="warn")
            return
        segs = [core.VlsmSegment(s["name"], s["hosts"]) for s in self.segments]
        try:
            plan = core.vlsm_plan(self.base_ip_var.get(), pfx, segs)
        except core.PlanOverflowError as e:
            plan = core.vlsm_plan(self.base_ip_var.get(), pfx, segs,
                                  raise_on_overflow=False)
            self._show_plan(plan)
            self.plan_warning.configure(
                text=f"Overflow: demand exceeds base capacity by {e.deficit:,} "
                     f"addresses. Only the leading segments fit; reduce demand "
                     f"or enlarge the base network.")
            self.app.status(f"Overflow — deficit {e.deficit:,} addresses.",
                            kind="warn")
            return
        self._show_plan(plan)
        self.plan_warning.configure(text="")
        self.app.current_plan = plan
        self.app.status(
            f"VLSM plan allocated: {len(plan.allocations)} segments, "
            f"{plan.utilization_pct:.1f}% utilized.", kind="ok")

    def _show_plan(self, plan):
        rows = [{"Segment": a.name, "Req hosts": a.required_hosts,
                 "Prefix": f"/{a.prefix}", "Block": a.block_size,
                 "Network": a.network, "First usable": a.first,
                 "Last usable": a.last, "Broadcast": a.broadcast,
                 "Mask": a.mask, "Usable": a.usable}
                for a in plan.allocations]
        self.plan_table.populate(
            rows, ["Segment", "Req hosts", "Prefix", "Block", "Network",
                   "First usable", "Last usable", "Broadcast", "Mask", "Usable"])
        self.plan_summary.configure(
            text=f"Utilization {plan.utilization_pct:.1f}%  ·  "
                 f"{plan.used:,} / {plan.base_capacity:,} addresses used")
        self.app.current_plan = plan


# --------------------------------------------------------------------------
# Tab 3 — Reports
# --------------------------------------------------------------------------

class ReportPage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.kind_var = tk.StringVar(value="subnet")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        pick = Card(self, title="Report contents")
        pick.grid(row=0, column=0, columnspan=2, sticky="ew")
        row = pick.body
        for label, val in (("Subnet calculation", "subnet"),
                           ("VLSM plan", "vlsm"),
                           ("Combined (both)", "combined")):
            ttk.Radiobutton(row, text=label, value=val, variable=self.kind_var,
                            style="Panel.TRadiobutton").pack(side="left",
                                                             padx=(0, 22))

        act = Card(self, title="Export")
        act.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        row = act.body
        primary_button(row, "Export HTML", command=self.export_html).pack(side="left")
        ghost_button(row, "Open in browser", command=self.open_browser).pack(side="left",
                                                                            padx=(10, 0))
        ghost_button(row, "Open export folder", command=self.open_folder).pack(side="left",
                                                                               padx=(10, 0))

        info = Card(self, title="What will be exported")
        info.grid(row=1, column=1, sticky="ew", pady=(16, 0))
        self.info_label = ttk.Label(info.body, text="", style="Muted.TLabel",
                                    wraplength=430, justify="left")
        self.info_label.pack(anchor="w")

        hist = Card(self, title="Exports this session")
        hist.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        self.hist_table = ResultTable(hist.body, height=6,
                                      columns=["#", "Document", "Saved to"],
                                      mono_columns=("Saved to",))
        self.hist_table.pack(fill="both", expand=True)
        self.hist_summary = ttk.Label(hist.body, text="", style="Muted.TLabel")
        self.hist_summary.pack(anchor="w", pady=(8, 0))
        self.rowconfigure(2, weight=1)

    # ---- payload ----------------------------------------------------------
    def build_payload(self, kind: str):
        subnet = self.app.current_subnet
        plan = self.app.current_plan
        if kind == "subnet":
            if not subnet:
                raise ValueError("No subnet calculation yet — calculate one first.")
            p = RPT.subnet_report_payload(subnet, "Subnet Calculation Report")
            if subnet.get("_subnets_table"):
                p["subnets_table"] = subnet["_subnets_table"]
                p["total_count"] = subnet.get("_total_count", len(subnet["_subnets_table"]))
            else:
                p["subnets_table"] = None
            return p
        if kind == "vlsm":
            if not plan:
                raise ValueError("No VLSM plan yet — run Allocate first.")
            return RPT.vlsm_report_payload(plan, "VLSM Allocation Report")
        # combined
        if not subnet and not plan:
            raise ValueError("Nothing to export yet.")
        return RPT.combined_report_payload(subnet or {}, plan or None,
                                           "SubnetPlanner — Combined Report")

    def refresh(self):
        subnet = self.app.current_subnet
        plan = self.app.current_plan
        parts = []
        parts.append("Subnet calculation: " + (
            (f"ready ({subnet.get('network')}/{subnet.get('prefix')}, "
             f"{subnet.get('usable_hosts'):,} usable hosts)" if subnet else "not yet")))
        parts.append("VLSM plan: " + (
            (f"ready ({plan.used:,} of {plan.base_capacity:,} addresses, "
             f"{plan.utilization_pct:.1f}%)" if plan else "not yet")))
        self.info_label.configure(text="\n".join(parts))

    # ---- actions ------------------------------------------------------------
    def export_html(self):
        kind = self.kind_var.get()
        try:
            payload = self.build_payload(kind)
        except ValueError as e:
            self.app.status(str(e), kind="warn")
            return
        default_dir = self.app.export_dir
        os.makedirs(default_dir, exist_ok=True)
        import datetime as _dt
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = {"subnet": "subnet_report", "vlsm": "vlsm_report",
                "combined": "combined_report"}[kind]
        path = filedialog.asksaveasfilename(
            title="Save HTML report", defaultextension=".html",
            filetypes=[("HTML document", "*.html")],
            initialdir=default_dir, initialfile=f"{name}_{stamp}.html")
        if not path:
            return
        try:
            html = RPT.render_html(payload)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
        except OSError as e:
            self.app.status(f"Export failed: {e}", kind="error")
            return
        self.app.exported_paths.append(path)
        self.app.export_dir = os.path.dirname(path)
        self.app.status(f"Report exported: {path}", kind="ok")
        self.refresh_history()

    def open_browser(self):
        import webbrowser
        if self.app.exported_paths:
            webbrowser.open(self.app.exported_paths[-1])
        else:
            self.app.status("Export a report before opening the browser.",
                            kind="warn")

    def open_folder(self):
        import subprocess
        folder = self.app.export_dir
        os.makedirs(folder, exist_ok=True)
        subprocess.Popen(["explorer", folder])

    def refresh_history(self):
        rows = [{"#": i, "Document": os.path.basename(p), "Saved to": p}
                for i, p in enumerate(self.app.exported_paths, start=1)]
        self.hist_table.populate(rows, ["#", "Document", "Saved to"])
        self.hist_summary.configure(
            text=f"{len(self.app.exported_paths)} report(s) exported this session.")