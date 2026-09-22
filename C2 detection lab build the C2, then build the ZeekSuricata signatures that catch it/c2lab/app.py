"""C2 Detection Lab — Tkinter GUI.

Standard desktop layout: menu bar, toolbar, tabbed notebook (Dashboard /
Lab Control / Generated Signatures / Reports / Documentation) and a status
bar. All network work happens on daemon threads; the GUI consumes a
thread-safe queue via a periodic ``after()`` ticker.
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __title__, __version__
from . import detect as detect_mod
from . import report as report_mod
from .client import BeaconClient
from .config import LabConfig, app_data_dir, first_free_port
from .docs import DOCS, export_docs
from .presets import get_profile, profile_names
from .report import export_events_as_json, render_summary
from .server import BeaconEvent, C2Server
from .signatures import build_all_rules
from .util import utc_now

STAMP = "C2DetectionLab"


class IconFactory:
    """Draws a simple lab shield icon at runtime with Pillow."""

    @staticmethod
    def photo_image(size: int = 64) -> tk.PhotoImage:
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            m = size // 6
            d.rounded_rectangle(
                [m, m, size - m, size - m], radius=size // 5, fill=(15, 42, 67, 255)
            )
            d.ellipse(
                [size * 0.24, size * 0.24, size * 0.76, size * 0.76],
                fill=(37, 99, 235, 255),
            )
            d.ellipse(
                [size * 0.32, size * 0.32, size * 0.68, size * 0.68],
                fill=(255, 255, 255, 255),
            )
            try:
                font = ImageFont.load_default(size=int(size * 0.30))
            except (TypeError, ValueError):
                font = ImageFont.load_default()
            text = "C2"
            bbox = d.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(
                ((size - w) / 2, (size - h) / 2 - bbox[1]),
                text,
                font=font,
                fill=(15, 42, 67, 255),
            )
            from PIL import ImageTk

            return ImageTk.PhotoImage(img)
        except Exception:
            return tk.PhotoImage()


class App(tk.Tk):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_obj = LabConfig()
        self.server: C2Server | None = None
        self.client: BeaconClient | None = None
        self.collected: list[BeaconEvent] = []
        self.session_result = None
        self.rules_cache: dict = {}
        self.report_path: Path | None = None

        self.title(f"{__title__} v{__version__}")
        self.geometry("1220x820")
        self.minsize(1060, 700)

        self._style_theme()
        self.icon = IconFactory.photo_image(64)
        self.iconphoto(True, self.icon)

        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_statusbar()

        self._refresh_signature_tab()
        self.after(300, self._poll_queue)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ setup
    def _style_theme(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("CardTitle.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("CardValue.TLabel", font=("Segoe UI", 22, "bold"))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Session", accelerator="Ctrl+N", command=self.clear_session)
        file_menu.add_separator()
        rep_menu = tk.Menu(file_menu, tearoff=0)
        rep_menu.add_command(label="HTML (Full)", command=lambda: self.generate_report("full"))
        rep_menu.add_command(label="HTML (Summary)", command=lambda: self.generate_report("summary"))
        rep_menu.add_command(label="JSON log", command=self.export_json)
        file_menu.add_cascade(label="Export", menu=rep_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Alt+F4", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="Generate Report (Full)", accelerator="Ctrl+S",
                                command=lambda: self.generate_report("full"))
        report_menu.add_command(label="Generate Report (Summary)", accelerator="Ctrl+Shift+S",
                                command=lambda: self.generate_report("summary"))
        report_menu.add_command(label="Open Report in Browser", accelerator="Ctrl+O",
                                command=self.open_report)
        report_menu.add_command(label="Save Report As…", command=self.save_report_as)
        menubar.add_cascade(label="Report", menu=report_menu)

        rules_menu = tk.Menu(menubar, tearoff=0)
        rules_menu.add_command(label="Export Signatures…", accelerator="Ctrl+E",
                               command=self.export_signatures)
        rules_menu.add_command(label="Copy Suricata Rules", command=self.copy_suricata)
        rules_menu.add_command(label="Copy Zeek Signatures", command=self.copy_zeek)
        menubar.add_cascade(label="Rules", menu=rules_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", accelerator="F1", command=self._show_docs_tab)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.bind_all("<Control-n>", lambda e: self.clear_session())
        self.bind_all("<Control-r>", lambda e: self.run_detection())
        self.bind_all("<Control-s>", lambda e: self.generate_report("full"))
        self.bind_all("<Control-S>", lambda e: self.generate_report("summary"))
        self.bind_all("<Control-o>", lambda e: self.open_report())
        self.bind_all("<Control-e>", lambda e: self.export_signatures())
        self.bind_all("<F1>", lambda e: self._show_docs_tab())

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(side="top", fill="x")
        ttk.Button(bar, text="Start Lab", command=self.start_lab).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Stop Lab", command=self.stop_lab).pack(side="left", padx=4)
        ttk.Button(bar, text="Clear", command=self.clear_session).pack(side="left", padx=4)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Run Detection", command=self.run_detection).pack(side="left", padx=4)
        ttk.Button(bar, text="Generate Report", command=lambda: self.generate_report("full")
                   ).pack(side="left", padx=4)
        ttk.Button(bar, text="Open Report", command=self.open_report).pack(side="left", padx=4)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Simulate Demo Session", command=self.simulate_demo
                   ).pack(side="left", padx=4)

    def _build_main(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(4, 0))

        self.tab_dashboard = ttk.Frame(self.notebook, padding=12)
        self.tab_controls = ttk.Frame(self.notebook, padding=12)
        self.tab_rules = ttk.Frame(self.notebook, padding=12)
        self.tab_reports = ttk.Frame(self.notebook, padding=12)
        self.tab_docs = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_dashboard, text=" Dashboard ")
        self.notebook.add(self.tab_controls, text=" C2 Lab Control ")
        self.notebook.add(self.tab_rules, text=" Generated Signatures ")
        self.notebook.add(self.tab_reports, text=" Reports & Download ")
        self.notebook.add(self.tab_docs, text=" Documentation ")

        self._build_dashboard()
        self._build_controls()
        self._build_rules()
        self._build_reports()
        self._build_docs()

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, relief="sunken", padding=(6, 3))
        bar.pack(side="bottom", fill="x")
        self.status_server = ttk.Label(bar, text="server: stopped")
        self.status_server.pack(side="left", padx=8)
        self.status_beacons = ttk.Label(bar, text="beacons: 0")
        self.status_beacons.pack(side="left", padx=8)
        self.status_file = ttk.Label(bar, text="")
        self.status_file.pack(side="right", padx=8)

    # ------------------------------------------------------------- dashboard
    def _build_dashboard(self) -> None:
        grid = ttk.Frame(self.tab_dashboard)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2, 3), uniform="c", weight=1)
        self.cards = {}
        labels = [
            ("Beacons Captured", "beacons"),
            ("Findings", "findings"),
            ("Alerts (>INFO)", "alerts"),
            ("Verdict", "verdict"),
        ]
        for i, (title, key) in enumerate(labels):
            card = ttk.Frame(grid, relief="groove", borderwidth=1, padding=14)
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=6)
            ttk.Label(card, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            value = ttk.Label(card, text="—", style="CardValue.TLabel")
            value.pack(anchor="w", pady=(6, 0))
            self.cards[key] = value

        bottom = ttk.Frame(self.tab_dashboard)
        bottom.pack(fill="both", expand=True, pady=(10, 0))
        ttk.Label(bottom,
                  text="Recent findings — double-click an item to copy its evidence."
                  ).pack(anchor="w")
        self.findings_box = tk.Listbox(bottom, height=12, font=("Consolas", 10))
        self.findings_box.pack(fill="both", expand=True)
        self.findings_box.bind("<Double-Button-1>", self._copy_selected_finding)

        quick = ttk.Frame(bottom)
        quick.pack(fill="x", pady=(8, 0))
        ttk.Button(quick, text="Run Detection Now", command=self.run_detection
                   ).pack(side="left", padx=(0, 6))
        ttk.Button(quick, text="Download HTML Report (Full)",
                   command=lambda: self.generate_report("full")).pack(side="left", padx=6)
        ttk.Button(quick, text="Download HTML Report (Summary)",
                   command=lambda: self.generate_report("summary")).pack(side="left", padx=6)

    # ----------------------------------------------------------- lab control
    def _build_controls(self) -> None:
        top = ttk.Frame(self.tab_controls)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Profile").grid(row=0, column=0, sticky="w", pady=5)
        self.ctl_profile = ttk.Combobox(top, values=profile_names(), state="readonly", width=38)
        self.ctl_profile.grid(row=0, column=1, sticky="w", pady=5)
        self.ctl_profile.set(self.config_obj.profile_name)
        self.ctl_profile.bind("<<ComboboxSelected>>", lambda e: self._refresh_signature_tab())

        ttk.Label(top, text="Port").grid(row=0, column=2, sticky="e", padx=(24, 6), pady=5)
        self.ctl_port = ttk.Spinbox(top, from_=1024, to=65535, width=8)
        self.ctl_port.grid(row=0, column=3, sticky="w", pady=5)
        self.ctl_port.set(self.config_obj.port)

        ttk.Label(top, text="Beacon interval (s)").grid(row=1, column=0, sticky="w", pady=5)
        self.ctl_interval = ttk.Spinbox(top, from_=1, to=3600, width=10)
        self.ctl_interval.grid(row=1, column=1, sticky="w", pady=5)
        self.ctl_interval.set(self.config_obj.beacon_interval)

        ttk.Label(top, text="Jitter (%)").grid(row=1, column=2, sticky="e", padx=(24, 6), pady=5)
        self.ctl_jitter = ttk.Spinbox(top, from_=0, to=100, increment=5, width=8)
        self.ctl_jitter.grid(row=1, column=3, sticky="w", pady=5)
        self.ctl_jitter.set(int(self.config_obj.jitter))

        ttk.Label(top, text="Duration (s)").grid(row=1, column=4, sticky="e", padx=(24, 6), pady=5)
        self.ctl_duration = ttk.Spinbox(top, from_=5, to=3600, width=8)
        self.ctl_duration.grid(row=1, column=5, sticky="w", pady=5)
        self.ctl_duration.set(self.config_obj.duration)

        actions = ttk.Frame(self.tab_controls)
        actions.pack(fill="x", pady=(8, 6))
        ttk.Button(actions, text="Start Lab", command=self.start_lab).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Stop Lab", command=self.stop_lab).pack(side="left", padx=6)
        ttk.Button(actions, text="Clear Session", command=self.clear_session).pack(side="left", padx=6)

        ttk.Label(self.tab_controls,
                  text="Live beacon monitor — each row is one HTTP check-in the C2 listener captured."
                  ).pack(anchor="w", pady=(6, 2))

        cols = ("#", "UTC timestamp", "Method", "URI", "User-Agent", "UA hash", "RTT (ms)")
        widths = (50, 150, 70, 170, 260, 110, 80)
        frame = ttk.Frame(self.tab_controls)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    # ------------------------------------------------------------ signatures
    def _build_rules(self) -> None:
        bar = ttk.Frame(self.tab_rules)
        bar.pack(fill="x")
        ttk.Label(bar, text="Profile:").pack(side="left")
        self.rules_profile = ttk.Combobox(bar, values=profile_names(), state="readonly", width=38)
        self.rules_profile.pack(side="left", padx=6)
        self.rules_profile.set(self.config_obj.profile_name)
        self.rules_profile.bind("<<ComboboxSelected>>", lambda e: self._refresh_signature_tab())
        ttk.Button(bar, text="Export Signatures…", command=self.export_signatures
                   ).pack(side="left", padx=6)

        notebook = ttk.Notebook(self.tab_rules)
        notebook.pack(fill="both", expand=True, pady=(8, 0))
        self.rule_texts = {}
        for name in ("Suricata — c2_beacons.rules", "Zeek — c2_beacons.sig",
                     "Zeek script — beacon_detect.zeek"):
            page = ttk.Frame(notebook)
            text = tk.Text(page, wrap="none", font=("Consolas", 10), padx=8, pady=8)
            vsb = ttk.Scrollbar(page, orient="vertical", command=text.yview)
            hsb = ttk.Scrollbar(page, orient="horizontal", command=text.xview)
            text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            text.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            page.rowconfigure(0, weight=1)
            page.columnconfigure(0, weight=1)
            text.config(state="disabled")
            self.rule_texts[name] = text
            notebook.add(page, text=" " + name.split(" — ")[0] + " ")

    def _refresh_signature_tab(self) -> None:
        profile = get_profile(self.rules_profile.get() or self.config_obj.profile_name)
        self.rules_cache = build_all_rules(profile)
        mapping = [
            ("Suricata — c2_beacons.rules", "c2_beacons.rules"),
            ("Zeek — c2_beacons.sig", "c2_beacons.sig"),
            ("Zeek script — beacon_detect.zeek", "beacon_detect.zeek"),
        ]
        for tab_key, file_key in mapping:
            text = self.rule_texts.get(tab_key)
            if not text:
                continue
            text.config(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", self.rules_cache.get(file_key, ""))
            text.config(state="disabled")

    # --------------------------------------------------------------- reports
    def _build_reports(self) -> None:
        left = ttk.Frame(self.tab_reports)
        left.pack(side="left", fill="y", padx=(0, 10))
        info = ttk.LabelFrame(left, text="Report download options", padding=10)
        info.pack(fill="x")
        ttk.Button(info, text="Download HTML — Full", width=30,
                   command=lambda: self.generate_report("full")).pack(fill="x", pady=3)
        ttk.Button(info, text="Download HTML — Summary", width=30,
                   command=lambda: self.generate_report("summary")).pack(fill="x", pady=3)
        ttk.Button(info, text="Open Report in Browser", width=30,
                   command=self.open_report).pack(fill="x", pady=3)
        ttk.Button(info, text="Save Report As…", width=30,
                   command=self.save_report_as).pack(fill="x", pady=3)
        ttk.Button(info, text="Export JSON session log", width=30,
                   command=self.export_json).pack(fill="x", pady=3)
        ttk.Separator(info).pack(fill="x", pady=8)
        ttk.Button(info, text="Export Signatures (rules)…", width=30,
                   command=self.export_signatures).pack(fill="x", pady=3)
        ttk.Button(info, text="Export Documentation…", width=30,
                   command=self.export_docs).pack(fill="x", pady=3)

        out = ttk.LabelFrame(left, text="Output folder", padding=8)
        out.pack(fill="x", pady=(12, 0))
        self.out_label = ttk.Label(out, text=str(app_data_dir()), wraplength=220, foreground="#334155")
        self.out_label.pack(anchor="w")
        ttk.Button(out, text="Change…", command=self._pick_output_dir).pack(anchor="w", pady=(6, 0))

        right = ttk.Frame(self.tab_reports)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Report preview").pack(anchor="w")
        self.preview = tk.Text(right, wrap="word", font=("Segoe UI", 10), padx=10, pady=8,
                               state="disabled")
        self.preview.pack(fill="both", expand=True)
        self.preview.insert("1.0", _PREVIEW_HINT)

    def _pick_output_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=str(app_data_dir()), title="Output folder")
        if chosen:
            self.config_obj.output_dir = Path(chosen)
            self.out_label.config(text=str(Path(chosen)))

    # ------------------------------------------------------------------ docs
    def _build_docs(self) -> None:
        bar = ttk.Frame(self.tab_docs)
        bar.pack(fill="x")
        ttk.Label(bar, text="Lab documentation (embedded)").pack(side="left")
        ttk.Button(bar, text="Export Documentation…", command=self.export_docs
                   ).pack(side="right")

        notebook = ttk.Notebook(self.tab_docs)
        notebook.pack(fill="both", expand=True, pady=(8, 0))
        self.doc_texts = {}
        for name in ("architecture.md", "state.md", "memory.md", "RUN_INSTRUCTIONS.md"):
            page = ttk.Frame(notebook)
            text = tk.Text(page, wrap="word", font=("Consolas", 10), padx=10, pady=10)
            vsb = ttk.Scrollbar(page, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=vsb.set)
            text.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            page.rowconfigure(0, weight=1)
            page.columnconfigure(0, weight=1)
            text.insert("1.0", DOCS.get(name, ""))
            text.config(state="disabled")
            self.doc_texts[name] = text
            notebook.add(page, text=" " + name + " ")

    # ------------------------------------------------------------- lifecycle
    def _read_config(self) -> bool:
        try:
            preferred = int(self.ctl_port.get())
            interval = max(1, int(self.ctl_interval.get()))
            jitter = max(0.0, float(self.ctl_jitter.get()))
            duration = max(5, int(self.ctl_duration.get()))
        except (ValueError, tk.TclError):
            messagebox.showerror("Configuration", "Port/interval/jitter/duration must be numbers.")
            return False
        port = first_free_port(preferred)
        self.ctl_port.set(port)
        if port != preferred:
            self._set_status(f"requested port {preferred} busy — using {port}")
        self.config_obj = LabConfig(
            profile_name=self.ctl_profile.get() or self.config_obj.profile_name,
            port=port,
            beacon_interval=interval,
            jitter=jitter,
            duration=duration,
            output_dir=self.config_obj.output_dir,
        )
        return True

    def start_lab(self) -> None:
        if self.server is not None and self.server.running:
            messagebox.showinfo("Lab", "Lab is already running.")
            return
        if not self._read_config():
            return
        profile = get_profile(self.config_obj.profile_name)
        server = C2Server(self.config_obj.host, self.config_obj.port)
        if not server.start():
            messagebox.showerror("C2 Listener", f"Could not bind: {server.error}")
            return
        self.server = server
        client = BeaconClient(server, profile,
                              self.config_obj.beacon_interval,
                              self.config_obj.jitter, self.config_obj.duration)
        self.client = client
        client.start()
        self.status_server.config(text=f"server: RUNNING on {self.config_obj.host}:{self.config_obj.port}")
        self.status_file.config(text=f"profile: {profile.name}")

    def stop_lab(self) -> None:
        if self.client is not None:
            self.client.stop()
            self.client = None
        if self.server is not None:
            self.server.stop()
            self.status_server.config(text="server: stopped")
            self.status_file.config(text="lab stopped")
            self.server = None

    def clear_session(self) -> None:
        if self.client is not None or (self.server is not None and self.server.running):
            if not messagebox.askyesno("New Session",
                                       "A lab session is running. Stop it and clear everything?"):
                return
            self.stop_lab()
        self.collected.clear()
        self.session_result = None
        self.report_path = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_dashboard()
        self._set_report_preview(_PREVIEW_HINT)
        self.status_beacons.config(text="beacons: 0")
        self.status_server.config(text="server: stopped")
        self.status_file.config(text="session cleared")

    def simulate_demo(self) -> None:
        """Generate a synthetic beacon session without touching the network."""
        profile = get_profile(self.ctl_profile.get() or self.config_obj.profile_name)
        base = datetime.now()
        events = []
        interval = max(1, int(self.ctl_interval.get())) if self.ctl_interval.get().strip() else 5
        n = 24
        for i in range(n):
            path = profile.uri_paths[i % len(profile.uri_paths)]
            stamp = base.strftime("%Y-%m-%dT%H:%M:%SZ")
            events.append(BeaconEvent(
                event_id=i + 1,
                timestamp=stamp,
                method=profile.methods[i % len(profile.methods)],
                path=path,
                user_agent=profile.user_agent,
                src_ip="127.0.0.1",
                dst_ip="127.0.0.1",
                host_header="127.0.0.1:8080",
                user_agent_hash="demo0" + format(i, "012x"),
                length=len(path) + 80,
                latency_ms=round(3 + (i % 5), 2),
            ))
            base = base + timedelta(seconds=interval)
        self.stop_lab()
        self.session_result = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.collected = events
        for e in events:
            self.tree.insert("", "end", values=(
                e.event_id, e.timestamp, e.method, e.path,
                e.user_agent[:52], e.user_agent_hash, e.latency_ms))
        self.status_beacons.config(text=f"beacons: {len(events)}")
        self.run_detection()
        self._set_status(f"demo session simulated ({profile.name})")

    # -------------------------------------------------------------- detection
    def run_detection(self) -> None:
        if not self.collected:
            messagebox.showwarning("Detection",
                                   "No beacon events yet. Start the lab, or run a demo session "
                                   "first.")
            return
        profile = get_profile(self.ctl_profile.get() or self.config_obj.profile_name)
        result = detect_mod.analyze_session(list(self.collected), profile)
        result.rule_texts = build_all_rules(profile)
        result.generated_at = utc_now()
        self.session_result = result
        self._refresh_dashboard()
        self._set_report_preview(_render_preview(result))
        self._set_status(f"detection run complete — verdict: {result.verdict}")

    def _refresh_dashboard(self) -> None:
        r = self.session_result
        self.cards["beacons"].config(text=str(len(self.collected)))
        self.cards["findings"].config(text=str(len(r.findings)) if r else "—")
        self.cards["alerts"].config(text=str(len(r.alerts)) if r else "—")
        self.cards["verdict"].config(text=(r.verdict if r else "—"))
        self.findings_box.delete(0, "end")
        if r:
            for f in r.findings:
                self.findings_box.insert(
                    "end", f"[{f.severity:>8}] {f.rule:<24} {f.title} — {f.evidence}")

    def _copy_selected_finding(self, _event=None) -> None:
        sel = self.findings_box.curselection()
        if not sel:
            return
        self.clipboard_clear()
        self.clipboard_append(self.findings_box.get(sel[0]))
        self.bell()

    # ---------------------------------------------------------------- reports
    def generate_report(self, flavour: str) -> None:
        if self.session_result is None:
            self.run_detection()
        if self.session_result is None:
            return
        result = self.session_result
        out = self.config_obj.output_dir / "reports"
        out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = out / f"{STAMP}_{stamp}_{flavour}.html"
        if flavour == "summary":
            content = render_summary(result)
            target.write_text(content, encoding="utf-8")
        else:
            report_mod.save_report(result, target)
        self.report_path = target
        self._set_status(f"saved {target}")
        try:
            webbrowser.open(target.as_uri())
        except Exception:
            pass
        messagebox.showinfo("Report", f"HTML report saved:\n{target}\n\nOpening in browser.")

    def open_report(self) -> None:
        if self.session_result is None:
            self.run_detection()
        if self.session_result is None:
            return
        out = self.config_obj.output_dir / "reports"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = out / f"{STAMP}_{stamp}_preview.html"
        report_mod.save_report(self.session_result, target)
        self.report_path = target
        webbrowser.open(target.as_uri())
        self._set_status(f"opened {target}")

    def save_report_as(self) -> None:
        if self.session_result is None:
            self.run_detection()
        if self.session_result is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML report", "*.html"), ("All files", "*.*")],
            initialfile=f"{STAMP}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        if not path:
            return
        report_mod.save_report(self.session_result, Path(path))
        self.report_path = Path(path)
        self._set_status(f"saved {path}")

    def export_json(self) -> None:
        if not self.collected:
            messagebox.showwarning("Export", "No session events to export.")
            return
        out = self.config_obj.output_dir / "reports"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = out / f"{STAMP}_{stamp}_session.json"
        export_events_as_json(self.collected, target)
        self._set_status(f"exported {target}")

    def export_signatures(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(app_data_dir()),
                                         title="Folder for generated signatures")
        if not folder:
            return
        for name, content in self.rules_cache.items():
            (Path(folder) / name).write_text(content, encoding="utf-8")
        self._set_status(f"signatures exported to {folder}")
        messagebox.showinfo("Rules", f"Signatures written to:\n{folder}")

    def export_docs(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(app_data_dir()),
                                         title="Folder for documentation")
        if not folder:
            return
        written = export_docs(Path(folder))
        self._set_status(f"docs written to {Path(folder) / 'docs'}")
        messagebox.showinfo("Documentation", "Wrote:\n" +
                            "\n".join(str(p) for p in written))

    def copy_suricata(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.rules_cache.get("c2_beacons.rules", ""))
        self._set_status("Suricata rules copied to clipboard")

    def copy_zeek(self) -> None:
        text = (self.rules_cache.get("c2_beacons.sig", "") + "\n\n" +
                "----- beacon_detect.zeek -----\n" + self.rules_cache.get("beacon_detect.zeek", ""))
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Zeek artifacts copied to clipboard")

    def _set_report_preview(self, text: str) -> None:
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.config(state="disabled")

    def _show_docs_tab(self) -> None:
        self.notebook.select(self.tab_docs)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{__title__} v{__version__}\n\n"
            "Build the C2, then build the Zeek / Suricata signatures that catch it.\n\n"
            "Loopback-only laboratory with HTML report export.\n"
            "Docs: architecture.md, state.md, memory.md, RUN_INSTRUCTIONS.md\n\n"
            "Educational tool — for detection-engineering practice only.")

    # --------------------------------------------------------------- polling
    def _poll_queue(self) -> None:
        try:
            if self.server is not None:
                new_events = self.server.drain()
                if new_events:
                    self.collected.extend(new_events)
                    for e in new_events:
                        self.tree.insert("", "end", values=(
                            e.event_id, e.timestamp, e.method, e.path,
                            e.user_agent[:52], e.user_agent_hash, e.latency_ms))
                    if len(self.collected) > 5000:
                        excess = len(self.collected) - 5000
                        self.collected = self.collected[excess:]
                        self.tree.delete(*self.tree.get_children()[:excess])
                    self.status_beacons.config(text=f"beacons: {len(self.collected)}")
                if self.server.running:
                    self.status_server.config(
                        text=f"server: RUNNING on {self.server.host}:{self.server.port}")
                else:
                    self.status_server.config(text="server: stopped")
        except tk.TclError:
            return
        self.after(300, self._poll_queue)

    def _set_status(self, text: str) -> None:
        self.status_file.config(text=text)

    def _on_close(self) -> None:
        try:
            if self.client is not None:
                self.client.stop()
            if self.server is not None:
                self.server.stop()
        finally:
            self.destroy()


_PREVIEW_HINT = (
    "Report preview\n\n"
    "Run a lab session and click 'Run Detection' to generate findings, then use\n"
    "the download buttons on the left to export HTML reports (full or summary).\n\n"
    "HTML reports are self-contained (inline CSS) — share them, print them, or\n"
    "archive them alongside the rules that produced them."
)


def _render_preview(result) -> str:
    lines = [f"REPORT PREVIEW — {result.profile.name}",
             f"Verdict: {result.verdict}", "=" * 62, ""]
    iv = result.interval_stats
    lines.append(f"Beacons: {result.total_events}   Duration: {result.duration_s:.1f}s")
    lines.append(f"Mean interval: {iv.get('mean', '—')}s   CV: {iv.get('cv', '—')}")
    lines.append("")
    sev = {name: 0 for name in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")}
    for f in result.findings:
        sev[f.severity] = sev.get(f.severity, 0) + 1
    lines.append("Severity: " + "  ".join(f"{k}={v}" for k, v in sev.items()))
    lines.append("")
    for f in result.findings:
        lines.append(f"[{f.severity}] {f.title}")
        lines.append(f"    rule: {f.rule}")
        lines.append(f"    evidence: {f.evidence}")
    return "\n".join(lines)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()