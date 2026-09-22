"""Main graphical application - dark themed tkinter lab console."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, __version__
from .core import (
    BeaconSchedule,
    BeaconSimulator,
    DetectionEngine,
    DomainFrontingAnalyzer,
    FrontingRequest,
    TransformPipeline,
    get_techniques,
)
from .reporting import build_html_report

BG = "#0e1117"
PANEL = "#161b22"
LINE = "#30363d"
FG = "#e6edf3"
MUT = "#8b949e"
ACC = "#58a6ff"
OK = "#3fb950"
WARN = "#d29922"
BAD = "#f85149"


class StyleBuilder:
    """Register dark styles for the 'clam' base theme."""

    def apply(self, root: tk.Tk) -> None:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL)
        style.configure(
            "TNotebook", background=BG, borderwidth=0, tabmargins=(4, 4, 4, 0)
        )
        style.configure(
            "TNotebook.Tab",
            background=PANEL,
            foreground=MUT,
            padding=(16, 8),
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ACC)],
            foreground=[("selected", "#0d1117")],
        )
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure(
            "TLabel", background=BG, foreground=FG, font=("Segoe UI", 10)
        )
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", foreground=MUT, font=("Segoe UI", 9))
        style.configure("Accent.TLabel", foreground=ACC, font=("Segoe UI", 10, "bold"))
        style.configure(
            "TButton",
            background=ACC,
            foreground="#0d1117",
            bordercolor=ACC,
            focusthickness=0,
            padding=(12, 7),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TButton",
            background=[("active", "#79c0ff"), ("disabled", "#21262d")],
            foreground=[("disabled", MUT)],
        )
        style.configure(
            "Ghost.TButton",
            background=PANEL,
            foreground=FG,
            bordercolor=LINE,
            padding=(12, 7),
            font=("Segoe UI", 10),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#1c2129")],
        )
        style.configure(
            "TEntry",
            fieldbackground=PANEL,
            foreground=FG,
            bordercolor=LINE,
            insertcolor=FG,
            padding=6,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=PANEL,
            foreground=FG,
            bordercolor=LINE,
            arrowcolor=FG,
        )
        style.configure(
            "Horizontal.TScale",
            background=BG,
            troughcolor=PANEL,
            bordercolor=LINE,
        )
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=FG,
            bordercolor=LINE,
            rowheight=28,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading", background="#1c2129", foreground=MUT,
            font=("Segoe UI", 9, "bold"), relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f6feb")],
            foreground=[("selected", FG)],
        )
        style.configure(
            "TLabelframe", background=BG, bordercolor=LINE, foreground=FG,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TLabelframe.Label", background=BG, foreground=ACC,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TRadiobutton", background=BG, foreground=FG, font=("Segoe UI", 9),
            indicatorbackground=PANEL, indicatorforeground=ACC,
        )
        style.configure(
            "TCheckbutton", background=BG, foreground=FG, font=("Segoe UI", 9),
            indicatorbackground=PANEL, indicatorforeground=ACC,
        )


def _row(
    parent: tk.Widget, title: str, value: str, color: str = ACC, row: int = 0
) -> ttk.Label:
    ttk.Label(parent, text=title, style="Sub.TLabel").grid(
        row=row, column=0, sticky="w", padx=(0, 6)
    )
    val = ttk.Label(parent, text=value, foreground=color, font=("Segoe UI", 16, "bold"))
    val.grid(row=row, column=1, sticky="w")
    return val


class DashboardTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        ttk.Label(
            self, text="C2 Traffic Obfuscation Lab", style="Title.TLabel"
        ).pack(anchor="w", pady=(6, 2))
        ttk.Label(
            self,
            text="Domain fronting concepts, obfuscation techniques and "
            "detection-focused analytics - fully offline simulation.",
            style="Sub.TLabel",
        ).pack(anchor="w")
        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="x", pady=14)
        grid = ttk.Frame(card)
        grid.pack(fill="x", padx=14, pady=12)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        _row(grid, "Techniques", "4", OK, 0)
        _row(grid, "Detection signals", "7+", OK, 1)
        _row(grid, "Beacon mode", "Jitter-aware", OK, 2)
        _row(grid, "Export", "HTML report", OK, 3)
        ttk.Label(grid, text="", style="Sub.TLabel").grid(row=4, columnspan=2)

        ttk.Label(
            self,
            text="What you can do",
            style="Accent.TLabel",
        ).pack(anchor="w", pady=(4, 6))
        for line in (
            "1.  Techniques - encode one command bytes through Base64, XOR, RC4 and AES.",
            "2.  Beacon Lab - generate a check-in schedule with configurable jitter.",
            "3.  Domain Fronting - inspect the SNI vs Host-header mismatch concept.",
            "4.  Detection Lab - score entropy, signatures and beacon regularity.",
            "5.  HTML Report - one-click export of the entire session.",
        ):
            ttk.Label(self, text=line, style="TLabel").pack(anchor="w", pady=1)
        ttk.Label(
            self,
            text="Educational / defensive use only. All traffic is synthetic.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(18, 0))


class TechniquesTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=0, pady=(0, 12))
        cols = ("name", "category", "description")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col, title, width in (
            ("name", "Technique", 160),
            ("category", "Category", 130),
            ("description", "Notes", 520),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        vs = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        for t in get_techniques(7):
            self.tree.insert("", "end", values=(t.name, t.category, t.description))

        cmd = tk.StringVar(value="GET /status?host=WS-0001&user=jsmith&ver=1.0.4")
        self.cmd_var = cmd
        ctl = ttk.Frame(self, style="Card.TFrame")
        ctl.pack(fill="x")
        inner = ttk.Frame(ctl)
        inner.pack(fill="x", padx=14, pady=12)
        ttk.Label(inner, text="Command to obfuscate:").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(inner, textvariable=cmd, width=72)
        entry.grid(row=0, column=1, padx=8)
        ttk.Button(inner, text="Encode Chain", command=self.encode_chain).grid(
            row=0, column=3, padx=(8, 0)
        )
        ttk.Button(
            inner, text="Stage-by-Stage", style="Ghost.TButton", command=self.stage_by_stage
        ).grid(row=0, column=4, padx=6)

        self.out = tk.Text(self, height=14, bg=PANEL, fg=FG, insertbackground=FG,
                           relief="flat", wrap="word", font=("Consolas", 9))
        self.out.pack(fill="both", expand=True, pady=(4, 0))

    def _plain(self) -> bytes:
        return self.cmd_var.get().encode()

    def _log(self, text: str) -> None:
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("end", text)
        self.out.configure(state="disabled")

    def stage_by_stage(self) -> None:
        plain = self._plain()
        seed = 7
        lines = [f"command ({len(plain)} bytes):  {plain.decode(errors='replace')}", ""]
        current = plain
        for t in get_techniques(seed):
            encoded = t.encode(current)
            lines.append(
                f"{t.name:14s} {t.category:14s} -> {encoded.hex()[:80]}{'...' if len(encoded) > 40 else ''}"
            )
            lines.append(f"{'':28s}    len={len(encoded)}  entropy={DetectionEngine.entropy(encoded):.3f}")
            current = encoded
        lines.append("")
        lines.append("chained decode round-trip:  " + current.decode(errors="replace"))
        self._log("\n".join(lines))

    def encode_chain(self) -> None:
        plain = self._plain()
        pipeline = TransformPipeline(get_techniques(7))
        encoded = pipeline.encode(plain)
        decoded = pipeline.decode(encoded)
        lines = [
            f"plaintext:     {plain.decode(errors='replace')}",
            f"encoded hex:   {encoded.hex()}",
            f"encoded len:   {len(encoded)} bytes",
            f"entropy:       {DetectionEngine.entropy(encoded):.3f}",
            f"round-trip ok: {decoded == plain}",
        ]
        self._log("\n".join(lines))


class BeaconTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        self.interval = tk.IntVar(value=60)
        self.jitter = tk.IntVar(value=15)
        self.count = tk.IntVar(value=15)

        ctl = ttk.Frame(self, style="Card.TFrame")
        ctl.pack(fill="x")
        inner = ttk.Frame(ctl)
        inner.pack(fill="x", padx=14, pady=12)
        inner.columnconfigure(1, weight=1)

        def slider(title: str, var: tk.IntVar, lo: int, hi: int) -> None:
            self._slider(inner, title, var, lo, hi)

        slider("Check-in interval (s)", self.interval, 1, 600)
        slider("Jitter (% of interval)", self.jitter, 0, 100)
        slider("Beacon count", self.count, 3, 60)
        ttk.Button(inner, text="Simulate Schedule", command=self.simulate).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(10, 0))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        tree_frame = ttk.Frame(body, style="Card.TFrame")
        tree_frame.grid(row=0, column=0, sticky="nsew")
        self.cols = ("num", "ts", "utc")
        self.tree = ttk.Treeview(tree_frame, columns=self.cols, show="headings")
        for col, title, width in (("num", "#", 40), ("ts", "Epoch", 140), ("utc", "UTC time", 220)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        right = ttk.Frame(body, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.verdict = ttk.Label(
            right, text="Run a simulation to get a beacon verdict.",
            style="Sub.TLabel", wraplength=260, justify="left",
        )
        self.verdict.pack(anchor="w", padx=12, pady=10)
        self.stats_frame = ttk.Frame(right)
        self.stats_frame.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(right, text="", style="Sub.TLabel").pack()

    def _slider(self, parent: tk.Widget, title: str, var: tk.IntVar, lo: int, hi: int, row: int = 0):
        ttk.Label(parent, text=title, style="Sub.TLabel").grid(
            row=row, column=0, sticky="w", pady=3
        )
        scale = ttk.Scale(parent, from_=lo, to=hi, variable=var,
                          command=lambda _v: self._sync_entry(var))
        scale.grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Label(parent, textvariable=var, width=4, style="Accent.TLabel").grid(
            row=row, column=2, sticky="e"
        )

    def _sync_entry(self, var: tk.IntVar) -> None:
        pass

    def simulate(self) -> None:
        sched = BeaconSchedule(
            self.interval.get(), self.jitter.get(), self.count.get(), seed=42
        )
        stats = sched.stats()
        times = sched.generate()
        r = BeaconSimulator()
        verdict = r.verdict(stats)
        self.app.session["beacon"] = {
            "stats": stats,
            "verdict": verdict,
            "rows": r.transcribe(times),
            "times": times,
        }
        self.tree.delete(*self.tree.get_children())
        for row in r.transcribe(times):
            self.tree.insert("", "end", values=(row["beacon"], row["timestamp"], row["utc"]))
        self._render_verdict(stats, verdict)

    def _render_verdict(self, stats: dict, verdict: dict) -> None:
        color = {"HIGH": BAD, "MEDIUM": WARN, "LOW": OK, "INFO": WARN}.get(
            verdict["severity"], OK
        )
        self.verdict.configure(
            text=f"SEVERITY: {verdict['severity']}\n{verdict['label']}",
            foreground=color,
        )
        for child in self.stats_frame.winfo_children():
            child.destroy()
        for i, (k, v) in enumerate(stats.items()):
            ttk.Label(
                self.stats_frame,
                text=f"{k.replace('_', ' '):28s} {v}",
                font=("Consolas", 9),
            ).grid(row=i, column=0, sticky="w")


class FrontingTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        self.sni = tk.StringVar(value="internal.defender.example.com")
        self.host = tk.StringVar(value="cdn-facade.example-cdn.com")
        self.encrypted = tk.BooleanVar(value=True)

        ctl = ttk.Frame(self, style="Card.TFrame")
        ctl.pack(fill="x")
        inner = ttk.Frame(ctl)
        inner.pack(fill="x", padx=14, pady=12)
        ttk.Label(inner, text="TLS SNI (plaintext):").grid(row=0, column=0, sticky="w")
        ttk.Entry(inner, textvariable=self.sni, width=52).grid(
            row=0, column=1, padx=8, pady=3, sticky="w"
        )
        ttk.Label(inner, text="HTTP Host:").grid(row=1, column=0, sticky="w")
        ttk.Entry(inner, textvariable=self.host, width=52).grid(
            row=1, column=1, padx=8, pady=3, sticky="w"
        )
        ttk.Checkbutton(inner, text="Encrypted payload", variable=self.encrypted).grid(
            row=2, column=1, sticky="w", padx=8, pady=3
        )
        ttk.Button(inner, text="Analyse Fronting", command=self.analyze).grid(
            row=3, column=1, sticky="w", padx=8, pady=(6, 0)
        )

        self.out = tk.Text(self, height=18, bg=PANEL, fg=FG, insertbackground=FG,
                           relief="flat", wrap="word", font=("Consolas", 9))
        self.out.pack(fill="both", expand=True, pady=(10, 0))

    def analyze(self) -> None:
        req = FrontingRequest(
            tls_sni=self.sni.get().strip(),
            host_header=self.host.get().strip(),
            encrypted=self.encrypted.get(),
        )
        analysis = DomainFrontingAnalyzer.analyze(req)
        lines = [
            "CONNECTION FLOW",
            "-" * 80,
        ]
        lines += analysis.redirections
        lines += ["", "DETECTION NOTES"]
        lines += ["-" * 80]
        lines += analysis.detector_notes
        lines += [
            "",
            "CONTROLS",
            "-" * 80,
        ]
        lines += DomainFrontingAnalyzer.suggested_controls(not analysis.match)
        lines += [
            "",
            f"Risk score: {analysis.risk_score}/100   "
            f"SNI==Host: {analysis.match}",
        ]
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("end", "\n".join(lines))
        self.out.configure(state="disabled")
        self.app.session["fronting"] = {
            "detector_notes": analysis.detector_notes,
            "controls": DomainFrontingAnalyzer.suggested_controls(not analysis.match),
            "risk_score": analysis.risk_score,
            "match": analysis.match,
            "tls_sni": req.tls_sni,
            "host_header": req.host_header,
        }


class DetectionTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        self.variants = DetectionEngine.build_sample_variants(7)

        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="x")
        cols = ("tech", "cat", "hex", "len", "entropy")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for col, title, width in (
            ("tech", "Technique", 130),
            ("cat", "Category", 120),
            ("hex", "Encoded bytes (hex prefix)", 360),
            ("len", "Len", 60),
            ("entropy", "Entropy", 70),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="x", padx=4, pady=4)
        for v in self.variants:
            self.tree.insert(
                "", "end",
                values=(v["technique"], v["category"], v["encoded_hex"],
                        v["encoded_len"], v["entropy"]),
            )

        row2 = ttk.Frame(self)
        row2.pack(fill="x", pady=(10, 0))
        row2.columnconfigure(0, weight=1)
        self.score_label = ttk.Label(row2, text="Detection score: -", style="Title.TLabel",
                                     font=("Segoe UI", 13, "bold"))
        self.score_label.grid(row=0, column=0, sticky="w")
        ttk.Button(row2, text="Analyse Selected Sample", command=self.analyze).grid(
            row=0, column=1, sticky="e"
        )
        cfg = ttk.Frame(self, style="Card.TFrame")
        cfg.pack(fill="x", pady=(10, 0))
        inner = ttk.Frame(cfg)
        inner.pack(fill="x", padx=14, pady=10)
        self.beacon_cv = ttk.Label(
            inner, text="Beacon regularity (from Beacon Lab): not yet run",
            style="Sub.TLabel",
        )
        self.beacon_cv.pack(anchor="w")
        ttk.Button(inner, text="Reuse Beacon Lab results", style="Ghost.TButton",
                   command=self.reuse_beacon).pack(anchor="w", pady=(8, 0))

        self.findings = tk.Text(self, height=12, bg=PANEL, fg=FG, insertbackground=FG,
                                relief="flat", wrap="word", font=("Consolas", 9))
        self.findings.pack(fill="both", expand=True, pady=(10, 0))

    def selected_bytes(self) -> bytes:
        cmd = b"GET /status?host=WS-0001&user=jsmith&ver=1.0.4"
        sel = self.tree.selection()
        if not sel:
            return DetectionEngine.build_sample_variants(7)[0]["plain"].encode()
        idx = self.tree.index(self.tree.selection()[0])
        return get_techniques(7)[idx].encode(cmd)

    def analyze(self) -> None:
        data = self.selected_bytes()
        det = DetectionEngine.analyze_payload(data, "POST /api/data HTTP/1.1\\r\\n")
        self.app.session["detection"] = det.to_dict()
        color = {"HIGH": BAD, "MEDIUM": WARN, "LOW": OK}.get(det.risk_level, OK)
        self.score_label.configure(
            text=f"Detection score: {det.risk_score}/100 ({det.risk_level})",
            foreground=color,
        )
        lines = ["FINDINGS"]
        lines.append("-" * 60)
        for f in det.sections:
            lines.append(f"[{f['weight']:>2}] {f['finding']:26s} {f['comment']}")
        lines.append("")
        lines.append("SIGNATURE MATCHES")
        lines.append("-" * 60)
        lines += det.signature_hits or ["none"]
        lines.append("")
        lines.append(f"entropy={det.entropy:.3f}  printable_ratio={det.printable_ratio:.3f}")
        self.findings.configure(state="normal")
        self.findings.delete("1.0", "end")
        self.findings.insert("end", "\n".join(lines))
        self.findings.configure(state="disabled")

    def reuse_beacon(self) -> None:
        beacon = self.app.session.get("beacon")
        if not beacon:
            messagebox.showinfo("Detection Lab", "Run the Beacon Lab simulation first.")
            return
        cv = beacon["stats"]["coefficient_of_variation"]
        self.beacon_cv.configure(
            text=(
                f"Beacon CoV={cv:.4f} -> severity {beacon['verdict']['severity']}. "
                "This signal will be merged into the payload score in the report."
            ),
            foreground=WARN,
        )
        self.app.session["beacon_merged"] = True


class ReportTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "LabApp") -> None:
        super().__init__(parent)
        self.app = app
        self.name = tk.StringVar(value="C2 Traffic Obfuscation - Lab Session")
        self.path = tk.StringVar()

        ctl = ttk.Frame(self, style="Card.TFrame")
        ctl.pack(fill="x")
        inner = ttk.Frame(ctl)
        inner.pack(fill="x", padx=14, pady=14)
        ttk.Label(inner, text="Report title:").grid(row=0, column=0, sticky="w")
        ttk.Entry(inner, textvariable=self.name, width=64).grid(
            row=0, column=1, padx=8, pady=3, sticky="ew"
        )
        ttk.Label(inner, text="Save path:").grid(row=1, column=0, sticky="w")
        self.path_entry = ttk.Entry(inner, textvariable=self.path, width=64)
        self.path_entry.grid(row=1, column=1, padx=8, pady=3, sticky="ew")
        ttk.Button(inner, text="Browse", style="Ghost.TButton",
                   command=self.browse).grid(row=1, column=2, padx=(8, 0))
        ttk.Button(inner, text="Generate HTML Report", command=self.generate).grid(
            row=2, column=1, sticky="w", padx=8, pady=(10, 0)
        )
        inner.columnconfigure(1, weight=1)

        self.status = tk.Text(self, height=18, bg=PANEL, fg=FG, insertbackground=FG,
                              relief="flat", wrap="word", font=("Consolas", 9))
        self.status.pack(fill="both", expand=True, pady=(10, 0))

    def browse(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile="c2-obfuscation-report.html",
            filetypes=[("HTML report", "*.html")],
        )
        if path:
            self.path.set(path)

    def generate(self) -> None:
        s = self.app.session
        if not s.get("beacon"):
            messagebox.showwarning(
                "Missing data", "Run Beacon Lab first so the report includes a schedule."
            )
            s["beacon"] = {
                "stats": {
                    "count": 0, "interval_target": 60, "interval_mean": 0,
                    "interval_std": 0, "coefficient_of_variation": 0,
                    "min": 0, "max": 0, "jitter_pct_requested": 0,
                },
                "verdict": {"severity": "INFO", "label": "No simulation run", "cv": 0},
                "rows": [{"beacon": 1, "timestamp": 0.0, "utc": "n/a"}],
                "times": [0.0],
            }

        beacon = s["beacon"]
        summary = {
            "badges": [
                {"level": beacon["verdict"]["severity"], "label": f"Beacon: {beacon['verdict']['label']}"},
                {"level": s.get("detection", {}).get("risk_level", "INFO"),
                 "label": f"Sample risk: {s.get('detection', {}).get('risk_level', 'n/a')}"},
                {"level": "MEDIUM" if s.get("fronting", {}).get("risk_score", 0) >= 40 else "GOOD",
                 "label": "Fronting concept shown"},
            ]
        }
        techniques = [
            {"name": t.name, "category": t.category, "description": t.description}
            for t in get_techniques(7)
        ]
        env_variants = DetectionEngine.build_sample_variants(7)
        beacon_stats = beacon["stats"]
        beacon_verdict = beacon["verdict"]
        beacon_rows = beacon["rows"]
        fronting = s.get("fronting", {})
        detection = s.get("detection", {
            "sections": [], "signature_hits": [], "risk_score": 0, "risk_level": "LOW",
        })

        report = build_html_report(
            self.name.get(),
            summary,
            techniques,
            env_variants,
            beacon_stats,
            beacon_verdict,
            beacon_rows,
            fronting,
            detection,
        )

        save_path = self.path.get() or "c2-obfuscation-report.html"
        with open(save_path, "w", encoding="utf-8") as fh:
            fh.write(report)

        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.insert(
            "end",
            f"Report written to:\n  {save_path}\n\n"
            f"{len(report):,} bytes | HTML sections: session, techniques, "
            "encoded payloads, beacon schedule, domain fronting, detection findings.\n",
        )
        self.status.configure(state="disabled")
        messagebox.showinfo("HTML Report", f"Report saved to:\n{save_path}")


class LabApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1180x760")
        self.minsize(960, 640)
        self.configure(bg=BG)
        StyleBuilder().apply(self)
        self.session: dict = {}

        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(
            header, text=f"v{__version__}  |  domain fronting concepts - detection focused",
            style="Sub.TLabel",
        ).pack(side="right", pady=(10, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(2, 12))
        self.tabs: dict[str, ttk.Frame] = {}
        tabs = (
            ("dashboard", "Dashboard", DashboardTab),
            ("techniques", "Techniques", TechniquesTab),
            ("beacon", "Beacon Lab", BeaconTab),
            ("fronting", "Domain Fronting", FrontingTab),
            ("detection", "Detection Lab", DetectionTab),
            ("report", "HTML Report", ReportTab),
        )
        for key, label, cls in tabs:
            tab = cls(self.notebook, self)
            self.notebook.add(tab, text=label)
            self.tabs[key] = tab

        footer = ttk.Label(
            self, text="Educational / defensive tool - simulates synthetic C2 patterns.",
            style="Sub.TLabel",
        )
        footer.pack(side="bottom", pady=(0, 6))


def launch() -> None:
    app = LabApp()
    app.mainloop()


if __name__ == "__main__":
    launch()