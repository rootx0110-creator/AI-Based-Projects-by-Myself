"""tkinter desktop GUI for the purple team lab.

Five tabs: Dashboard, Red Build, Blue Detect, MITRE Coverage, Report/Export.
The heavy work (red build, blue scan, HTML render) runs in worker threads so
the UI stays responsive; results are marshalled back via a queue.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, Tk, StringVar, BooleanVar
from tkinter import font as tkfont

from . import APP_NAME, APP_SLUG, __version__
from .config import REPORTS_DIR, ensure_dirs
from .exercise import (Session, blue_detect, new_exercise, red_build,
                       save_session, load_last_session)
from .mitre import BLUE_RULES, RED_TECHNIQUES, TECH_BY_ID, RULE_BY_ID
from .report import open_report, save_report
from .util import now_iso, pct

BG = "#0f1420"
PANEL = "#171e2e"
PANEL2 = "#1d2638"
INK = "#dfe6f3"
MUT = "#8b96b0"
ACC = "#7aa2ff"
RED = "#ff6b81"
BLUE = "#4fc3f7"
GREEN = "#38d9a9"
YELLOW = "#ffd166"

CELL_HIT = "\u25cf"     # filled dot  - rule fired
CELL_MISS = "\u25cb"    # hollow dot  - rule ran, did not fire
CELL_NA = "\u00b7"      # middle dot  - technique not mapped to rule

RULE_ORDER = tuple(r.id for r in BLUE_RULES)
RULE_SHORT = {
    "RULE-SCHTASK": "SCHTASK",
    "RULE-DL-ATTACHMENT": "DL-ATMNT",
    "RULE-AUTOSTART": "AUTOSTART",
    "RULE-PS-OBFUSC": "PS-OBFUSC",
    "RULE-DISCOVERY": "DISCOVERY",
    "RULE-TOOL-DROP": "TOOLDROP",
    "RULE-EXFIL": "EXFIL",
    "RULE-API-CALL": "API-CALL",
    "RULE-CHANGE": "CATCH-ALL",
}

_sentinel = object()


class PurpleApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1240x800")
        self.minsize(1000, 660)
        self.configure(bg=BG)
        self._set_style()

        self.work = queue.Queue()
        self.session: Session | None = None
        self.last_report: Path | None = None
        self.selected: dict[str, BooleanVar] = {}

        screen_w = self.winfo_screenwidth()
        try:
            if screen_w >= 1500:
                self.state("zoomed")
        except Exception:
            pass

        self._build_layout()
        self._restore_last()
        self.after(120, self._drain_work)

    # ---------- styling ----------
    def _set_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=BG, foreground=INK, fieldbackground=PANEL2,
                        font=("Segoe UI", 10), borderwidth=0)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUT,
                        padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACC)],
                  foreground=[("selected", "#0b1020")])
        style.configure("TCheckbutton", background=BG, foreground=INK)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TButton", background=PANEL2, foreground=INK, padding=(10, 6))
        style.map("TButton", background=[("active", "#2a3754")])
        style.configure("Accent.TButton", background=ACC, foreground="#0b1020", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#9cc0ff")])
        style.configure("Red.TButton", background="#5e1e2e", foreground="#fff")
        style.map("Red.TButton", background=[("active", "#8a2f43")])
        style.configure("Blue.TButton", background="#123b52", foreground="#fff")
        style.map("Blue.TButton", background=[("active", "#1c5875")])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=INK, rowheight=26, borderwidth=0)
        style.configure("Matrix.Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=INK, rowheight=46, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL2, foreground=ACC,
                        font=("Segoe UI", 9, "bold"), padding=6)
        style.map("Treeview", background=[("selected", "#2a3754")])
        style.configure("TProgressbar", background=ACC, troughcolor=PANEL2)
        style.configure("TLabelframe", background=BG, foreground=INK)
        style.configure("TLabelframe.Label", background=BG, foreground=ACC,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background=PANEL, foreground=MUT, padding=6)

    # ---------- layout ----------
    def _build_layout(self) -> None:
        head = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(header, text=APP_NAME, foreground=ACC, style="TLabel",
                  font=head).pack(side="left")
        ttk.Label(header,
                  text="red builds \u2022 blue detects \u2022 both document MITRE ATT&CK",
                  foreground=MUT).pack(side="left", padx=14, pady=(6, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 2))
        self.tab_dash = ttk.Frame(self.notebook)
        self.tab_red = ttk.Frame(self.notebook)
        self.tab_blue = ttk.Frame(self.notebook)
        self.tab_mitre = ttk.Frame(self.notebook)
        self.tab_report = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dash, text="  Dashboard  ")
        self.notebook.add(self.tab_red, text="  Red Build  ")
        self.notebook.add(self.tab_blue, text="  Blue Detect  ")
        self.notebook.add(self.tab_mitre, text="  MITRE Coverage  ")
        self.notebook.add(self.tab_report, text="  Report / Export  ")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_dashboard()
        self._build_red()
        self._build_blue()
        self._build_mitre()
        self._build_report()

        self.status = ttk.Label(self, text="Ready \u2022 lab sandbox: "
                                           "outputs/lab_target", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom")

    def _build_dashboard(self) -> None:
        f = self.tab_dash
        left = ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(4, 8), pady=8)
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)

        box = ttk.Labelframe(left, text="Techniques for red to build")
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Check techniques, then run the exercise below.",
                  foreground=MUT).pack(anchor="w", padx=8, pady=(4, 2))
        for t in RED_TECHNIQUES:
            var = BooleanVar(value=True)
            self.selected[t.id] = var
            label = f"{t.id}  {t.name}"
            cb = ttk.Checkbutton(box, text=label, variable=var)
            cb.pack(anchor="w", padx=10, pady=1)
        cb_all_none = ttk.Frame(left)
        cb_all_none.pack(fill="x", pady=(6, 0))
        ttk.Button(cb_all_none, text="All", command=self._select_all).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(cb_all_none, text="None", command=self._select_none).pack(side="left", expand=True, fill="x", padx=2)

        ctrl = ttk.Labelframe(left, text="Exercise controls")
        ctrl.pack(fill="x", pady=8)
        ttk.Button(ctrl, text="Reset lab to baseline", command=self._do_reset).pack(
            fill="x", padx=8, pady=(6, 2))
        self.btn_red = ttk.Button(ctrl, text="1 \u25b6 Build  (RED)", style="Red.TButton",
                                  command=self._do_red_build)
        self.btn_red.pack(fill="x", padx=8, pady=4)
        self.btn_blue = ttk.Button(ctrl, text="2 \u25b6 Detect  (BLUE)", style="Blue.TButton",
                                   command=self._do_blue_detect)
        self.btn_blue.pack(fill="x", padx=8, pady=(4, 8))

        scorebox = ttk.Labelframe(right, text="Score dashboard")
        scorebox.pack(fill="both", expand=True)
        self.score_text = tk_text(scorebox, height=14)
        self.score_text.pack(fill="both", expand=True, padx=6, pady=6)

        logbox = ttk.Labelframe(right, text="Live timeline")
        logbox.pack(fill="both", expand=True, pady=(8, 0))
        self.log_text = tk_text(logbox, height=9)
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_red(self) -> None:
        top = ttk.Frame(self.tab_red)
        top.pack(fill="x", padx=6, pady=8)
        ttk.Label(top, text="Artifacts the red side built against the lab target.",
                  foreground=MUT).pack(side="left")
        self.red_btn = ttk.Button(top, text="Build selected techniques (RED)",
                                  style="Red.TButton", command=self._do_red_build)
        self.red_btn.pack(side="right")

        frame = ttk.Frame(self.tab_red)
        frame.pack(fill="both", expand=True, padx=6)
        cols = ("tech", "tactic", "file", "event", "ts")
        self.red_tree = tk_tree(frame, cols, widths=(90, 90, 300, 480, 150),
                                stretch=("event",))
        self.red_tree.pack(fill="both", expand=True)
        self.red_tree.heading("tech", text="Technique")
        self.red_tree.heading("tactic", text="Tactic")
        self.red_tree.heading("file", text="Artifact")
        self.red_tree.heading("event", text="What the attacker did")
        self.red_tree.heading("ts", text="Timestamp")
        self.red_tree.tag_configure("red", foreground=RED)

    def _build_blue(self) -> None:
        top = ttk.Frame(self.tab_blue)
        top.pack(fill="x", padx=6, pady=8)
        ttk.Label(top, text="Detection findings after scanning the lab target.",
                  foreground=MUT).pack(side="left")
        self.blue_btn = ttk.Button(top, text="Run detection pass (BLUE)",
                                   style="Blue.TButton", command=self._do_blue_detect)
        self.blue_btn.pack(side="right")

        frame = ttk.Frame(self.tab_blue)
        frame.pack(fill="both", expand=True, padx=6)
        cols = ("rule", "tech", "sev", "fid", "file", "event")
        self.f_tree = tk_tree(frame, cols, widths=(90, 90, 70, 70, 240, 480),
                              stretch=("event",))
        self.f_tree.pack(fill="both", expand=True)
        self.f_tree.heading("rule", text="Rule")
        self.f_tree.heading("tech", text="Technique")
        self.f_tree.heading("sev", text="Severity")
        self.f_tree.heading("fid", text="Fidelity")
        self.f_tree.heading("file", text="Artifact")
        self.f_tree.heading("event", text="Finding")
        self.f_tree.tag_configure("sev_high", foreground=RED)
        self.f_tree.tag_configure("sev_medium", foreground=YELLOW)
        self.f_tree.tag_configure("sev_low", foreground=ACC)
        self.f_tree.tag_configure("fid_high", foreground=GREEN)

    def _build_mitre(self) -> None:
        top = ttk.Frame(self.tab_mitre)
        top.pack(fill="x", padx=6, pady=(8, 2))
        ttk.Label(top,
                  text="MITRE ATT&CK coverage matrix \u2022 rows = techniques red built, "
                       "columns = blue detection rules. Click a row for its detection story.",
                  foreground=MUT).pack(side="left")

        self.mitre_stats = ttk.Label(self.tab_mitre, text="", foreground=ACC)
        self.mitre_stats.pack(fill="x", padx=8, pady=(0, 2))

        frame = ttk.Frame(self.tab_mitre)
        frame.pack(fill="both", expand=True, padx=6, pady=(2, 0))
        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")
        cols = ("tech",) + RULE_ORDER + ("det",)
        self.matrix_tree = tk_tree(frame, cols,
                                   widths=(260,) + (86,) * len(RULE_ORDER) + (80,),
                                   stretch=("tech",),
                                   style="Matrix.Treeview")
        self.matrix_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.matrix_tree.yview)
        hsb.config(command=self.matrix_tree.xview)
        self.matrix_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.matrix_tree.heading("tech", text="Technique built by RED")
        for r in BLUE_RULES:
            self.matrix_tree.heading(r.id, text=RULE_SHORT[r.id])
        self.matrix_tree.heading("det", text="Detected")
        self.matrix_tree.tag_configure("state_good", background="#0f2b1d", foreground=GREEN)
        self.matrix_tree.tag_configure("state_mid", background="#3a2f12", foreground=YELLOW)
        self.matrix_tree.tag_configure("state_bad", background="#40131f", foreground=RED)
        self.matrix_tree.tag_configure("state_hint", background=PANEL, foreground=MUT)
        self.matrix_tree.bind("<<TreeviewSelect>>", self._on_matrix_select)
        self.matrix_tree.bind("<Motion>", self._on_matrix_hover)

        legend = ttk.Frame(self.tab_mitre)
        legend.pack(fill="x", padx=6, pady=(4, 2))
        ttk.Label(legend, text=f"{CELL_HIT} = rule fired for this technique",
                  foreground=GREEN).pack(side="left", padx=(0, 14))
        ttk.Label(legend, text=f"{CELL_MISS} = rule ran but did not fire",
                  foreground=MUT).pack(side="left", padx=(0, 14))
        ttk.Label(legend, text=f"{CELL_NA} = technique not mapped to that rule",
                  foreground="#3a4254").pack(side="left", padx=(0, 14))
        ttk.Label(legend, text="row colour = verdict",
                  foreground=ACC).pack(side="left", padx=(0, 14))
        ttk.Label(legend, text="\u2714 detected / \u2718 undetected",
                  foreground=INK).pack(side="left")

        self.mitre_hint = ttk.Label(self.tab_mitre, text="Hover a cell to see the rule; click a "
                                                          "technique row for its full detection story.",
                                     foreground=MUT)
        self.mitre_hint.pack(fill="x", padx=8, pady=(0, 4))

        bottom = ttk.Frame(self.tab_mitre)
        bottom.pack(fill="x", padx=6, pady=(0, 6))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)

        rulebox = ttk.Labelframe(bottom, text="Rule performance (this run)")
        rulebox.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        rc = ("rule", "mapped", "fired", "rate")
        self.rule_tree = tk_tree(rulebox, rc, widths=(150, 84, 70, 70))
        self.rule_tree.heading("rule", text="Rule")
        self.rule_tree.heading("mapped", text="Can detect")
        self.rule_tree.heading("fired", text="Fired on")
        self.rule_tree.heading("rate", text="Coverage")
        self.rule_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.rule_tree.tag_configure("p_good", foreground=GREEN)
        self.rule_tree.tag_configure("p_mid", foreground=YELLOW)
        self.rule_tree.tag_configure("p_bad", foreground=RED)
        self.rule_tree.tag_configure("p_hint", foreground=MUT)

        detailbox = ttk.Labelframe(bottom, text="Detection story \u2022 select a technique")
        detailbox.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.mitre_detail = tk_text(detailbox, height=8)
        self.mitre_detail.pack(fill="both", expand=True, padx=4, pady=4)
        self.mitre_detail.tag_configure("hdr", foreground=ACC, font=("Segoe UI", 11, "bold"))
        self.mitre_detail.tag_configure("ex_ok", foreground=GREEN)
        self.mitre_detail.tag_configure("ex_bad", foreground=RED)

    def _build_report(self) -> None:
        top = ttk.Frame(self.tab_report)
        top.pack(fill="x", padx=6, pady=8)
        ttk.Label(top, text="Exercise reports are self-contained HTML (no network, printable).",
                  foreground=MUT).pack(side="left")

        body = ttk.Frame(self.tab_report)
        body.pack(fill="both", expand=True, padx=6)
        self.report_text = tk_text(body, height=18)
        self.report_text.pack(fill="both", expand=True, pady=(0, 6))

        bar = ttk.Frame(body)
        bar.pack(fill="x")
        self.btn_dl = ttk.Button(bar, text="Download HTML report...", style="Accent.TButton",
                                 command=self._download_report)
        self.btn_dl.pack(side="left", padx=(0, 8))
        self.btn_open = ttk.Button(bar, text="Open last report", command=self._open_report)
        self.btn_open.pack(side="left", padx=(0, 8))
        self.btn_folder = ttk.Button(bar, text="Open reports folder",
                                     command=lambda: _open_folder(REPORTS_DIR))
        self.btn_folder.pack(side="left")

    # ---------- helpers ----------
    def _busy(self, label: str, on: bool) -> None:
        state = "disabled" if on else "normal"
        self.status.config(text=label if on else "Ready")
        for b in (self.btn_red, self.btn_blue, self.red_btn, self.blue_btn, self.btn_dl):
            try:
                b.config(state=state)
            except Exception:
                pass

    def _run_worker(self, job: str, payload=None) -> None:
        def worker() -> None:
            try:
                result = self._dispatch(job, payload)
                self.work.put(("done", job, result))
            except Exception as exc:  # pragma: no cover - UI path
                self.work.put(("error", job, str(exc)))

        self._busy(f"{job} running \u2026", True)
        threading.Thread(target=worker, daemon=True).start()

    def _dispatch(self, job: str, payload):
        if job == "red":
            return self._build_sync(payload)
        if job == "blue":
            s = self.session
            if s is None:
                raise RuntimeError("No exercise started")
            return blue_detect(s)
        if job == "report":
            return save_report(self.session, payload)
        if job == "reset":
            self.session = new_exercise(reset=True)
            save_session(self.session)
            return None
        raise RuntimeError(f"unknown job {job}")

    def _drain_work(self) -> None:
        try:
            while True:
                kind, job, payload = self.work.get_nowait()
                if kind == "done":
                    self._on_job_done(job, payload)
                elif kind == "error":
                    self._busy("Ready", False)
                    messagebox.showerror(f"{job} failed", payload)
        except queue.Empty:
            pass
        self.after(150, self._drain_work)

    def _on_job_done(self, job: str, payload) -> None:
        self._busy("Ready", False)
        if job == "red":
            self.session = payload
            self._refresh_all()
            n = len(self.session.artifacts)
            if n:
                messagebox.showinfo("Red build",
                                    f"Built {n} artifact(s) on the lab target.")
            else:
                messagebox.showinfo("Red build",
                                    "The selected techniques are already built this exercise. "
                                    "Use Reset lab to rebuild from scratch.")
        elif job == "blue":
            self.session = payload
            save_session(self.session)
            self._refresh_all()
            messagebox.showinfo("Blue detect",
                                f"{len(self.session.findings)} finding(s). "
                                f"Detection rate {self.session.score['detection_rate']}%.")
        elif job == "report":
            self.last_report = Path(payload)
            self.status.config(text=f"Report saved: {self.last_report}")
            messagebox.showinfo("Report", f"HTML report saved to\n{self.last_report}")
        elif job == "reset":
            self._refresh_all()
            self.status.config(text="Lab reset to clean baseline")
            self._scroll_tab("Dashboard")

    # ---------- sync jobs called from worker thread ----------
    def _build_sync(self, ids: list[str]):
        from .exercise import score_exercise
        s = self.session or new_exercise(reset=True)
        red_build(s, ids)
        s.score = score_exercise(s)
        save_session(s)
        return s

    def _on_tab_changed(self, event=None) -> None:
        tab = self.notebook.index(self.notebook.select())
        if tab == 3:      # MITRE Coverage
            self._refresh_matrix()
        elif tab == 4:    # Report / Export
            self._refresh_report()

    def _select_all(self) -> None:
        for v in self.selected.values():
            v.set(True)

    def _select_none(self) -> None:
        for v in self.selected.values():
            v.set(False)

    def _do_reset(self) -> None:
        if not messagebox.askyesno("Reset lab",
                                   "Wipe the lab target back to baseline and start a new exercise?"):
            return
        self._run_worker("reset")

    def _do_red_build(self) -> None:
        ids = [tid for tid, var in self.selected.items() if var.get()]
        if not ids:
            messagebox.showwarning("Build", "Select at least one technique to build.")
            return
        self._run_worker("red", ids)

    def _do_blue_detect(self) -> None:
        if self.session is None or not self.session.techniques_executed:
            messagebox.showwarning("Detect", "Build red techniques first.")
            return
        self._run_worker("blue")

    # ---------- refresh ----------
    def _refresh_all(self) -> None:
        self._refresh_score()
        self._refresh_red()
        self._refresh_blue()
        self._refresh_matrix()
        self._refresh_report()

    def _refresh_score(self) -> None:
        s = self.session
        t = self.score_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        if s is None or not s.techniques_executed:
            t.insert("end", "No exercise run yet.\n\nSelect techniques on the left, then click ")
            t.insert("end", "1 \u25b6 Build (RED)", "red")
            t.insert("end", " and ")
            t.insert("end", "2 \u25b6 Detect (BLUE)", "blue")
            t.insert("end", " to get started.")
        else:
            sc = s.score or {}
            t.insert("end", f"Exercise {s.run_id}\n", "acc")
            t.insert("end", f"created {s.created}\n\n", "mut")
            t.insert("end", f"Techniques executed (red):   {sc.get('techniques_executed', 0)}\n", "red")
            t.insert("end", f"Techniques detected (blue):  {sc.get('techniques_detected', 0)}\n", "blue")
            t.insert("end", f"High-fidelity detections:    {sc.get('techniques_high_fidelity', 0)}\n", "acc")
            t.insert("end", f"ATT&CK detection rate:       {sc.get('detection_rate', 0)}%\n", "green")
            t.insert("end", f"Dedicated coverage:          {sc.get('high_fidelity_coverage', 0)}%\n\n", "green")
            t.insert("end", f"Findings: {sc.get('findings_count', 0)}   "
                            f"Artifacts: {sc.get('artifacts_count', 0)}\n"
                            f"Rules fired: {len(sc.get('rules_fired', []))}/{len(BLUE_RULES)}\n", "mut")
            if sc.get("gaps"):
                t.insert("end", "\nFully undetected: ", "red")
                t.insert("end", ", ".join(sc["gaps"]), "red")
            else:
                t.insert("end", "\nNo fully undetected techniques this run.", "green")
        t.configure(state="disabled")

    def _refresh_red(self) -> None:
        tree = self.red_tree
        tree.delete(*tree.get_children())
        for a in self.session.artifacts if self.session else []:
            tech = TECH_BY_ID.get(a.get("technique_id", ""))
            tree.insert("", "end", values=(
                a.get("technique_id", ""),
                tech.tactic if tech else "",
                a.get("file", ""),
                a.get("event", ""),
                (a.get("ts") or "")[:19],
            ), tags=("red",))

    def _refresh_blue(self) -> None:
        tree = self.f_tree
        tree.delete(*tree.get_children())
        for f in self.session.findings if self.session else []:
            sev = f.get("severity", "")
            tree.insert("", "end", values=(
                f.get("rule_name", ""),
                f.get("technique_id", ""),
                sev, f.get("fidelity", ""),
                f.get("file", ""), f.get("event", ""),
            ), tags=(f"sev_{sev}", "fid_high" if f.get("fidelity") == "high" else ""))

    def _refresh_matrix(self) -> None:
        tree = self.matrix_tree
        tree.delete(*tree.get_children())
        self._row_id_by_tid: dict[str, str] = {}
        s = self.session
        matrix = (s.score or {}).get("matrix", {}) if s else {}
        fid = (s.score or {}).get("fidelity_by", {}) if s else {}
        detected_by = (s.score or {}).get("detected_by", {}) if s else {}

        if not matrix:
            tree.insert("", "end", values=(
                "Run Red Build, then Blue Detect to fill the matrix.",) +
                ("",) * (len(RULE_ORDER) + 1), tags=("state_hint",))
            self.mitre_stats.config(text="No exercise data yet.")
            self.rule_tree.delete(*self.rule_tree.get_children())
            self._write_detail("")
            return

        for tid, row in matrix.items():
            tech = TECH_BY_ID.get(tid)
            label = (f"{tid}\n{tech.name if tech else ''}\n{tech.tactic if tech else ''}"
                     if tech else f"{tid}\n?")
            vals = [label]
            for r in BLUE_RULES:
                if tid in r.detects:
                    vals.append(CELL_HIT if row.get(r.id) else CELL_MISS)
                else:
                    vals.append(CELL_NA)
            detected = bool(detected_by.get(tid))
            vals.append("\u2714" if detected else "\u2718")

            state = fid.get(tid, "none")
            tag = "state_good" if state == "high" else ("state_mid" if state == "low"
                                                        else "state_bad")
            iid = tree.insert("", "end", values=tuple(vals), tags=(tag,))
            self._row_id_by_tid[tid] = iid

        self._refresh_mitre_stats(matrix, fid)
        self._refresh_rule_performance(matrix)
        sel = tree.selection()
        if sel:
            self._show_detail(sel[0])
        elif tree.get_children():
            self._show_detail(tree.get_children()[0])

    def _refresh_mitre_stats(self, matrix: dict[str, dict[str, bool]], fid: dict) -> None:
        n = len(matrix)
        detected = sum(1 for t in matrix if fid.get(t) in ("high", "low"))
        hi = sum(1 for t in matrix if fid.get(t) == "high")
        undet = n - detected
        fired = sum(1 for row in matrix.values() if any(row.values()))
        rate = pct(fired, n)
        label = (f"{n} techniques built  \u2022  {detected} detected ({rate}%)  \u2022  "
                 f"{hi} with dedicated high-fidelity rules  \u2022  {undet} undetected")
        self.mitre_stats.config(text=label)

    def _refresh_rule_performance(self, matrix: dict[str, dict[str, bool]]) -> None:
        t = self.rule_tree
        t.delete(*t.get_children())
        for r in BLUE_RULES:
            possible = [tid for tid, row in matrix.items() if tid in r.detects]
            fired = [tid for tid in possible if matrix[tid].get(r.id)]
            rate = pct(len(fired), len(possible))
            tag = "p_good" if fired == possible else ("p_mid" if fired else "p_bad")
            t.insert("", "end", values=(RULE_SHORT[r.id], len(possible), len(fired),
                                        f"{rate}%"), tags=(tag,))
        # overview row
        detected = sum(1 for tid, row in matrix.items() if any(row.values()))
        t.insert("", "end", values=("Any rule (coverage)", len(matrix), detected,
                                    f"{pct(detected, len(matrix))}%"), tags=("p_hint",))

    def _on_matrix_select(self, event=None) -> None:
        sel = self.matrix_tree.selection()
        if sel:
            self._show_detail(sel[0])

    def _on_matrix_hover(self, event) -> None:
        tree = self.matrix_tree
        row_id = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not row_id or col in ("", "#0"):
            return
        idx = int(col[1:]) - 1
        values = tree.item(row_id, "values")
        if not values or idx >= len(values):
            return
        label = str(values[0]).split("\n")[0]
        if idx == 0:
            tech = TECH_BY_ID.get(label)
            self.mitre_hint.config(text=f"{label} - {tech.name if tech else ''} "
                                        f"({tech.tactic if tech else ''})")
        elif idx <= len(RULE_ORDER):
            rule = RULE_BY_ID.get(RULE_ORDER[idx - 1])
            if rule:
                fired = str(values[idx]) == CELL_HIT
                text = f"{rule.id} - {rule.name}  \u2022  {rule.data_source}" + \
                       ("  [FIRED for this technique]" if fired else "  [no signal here]")
                self.mitre_hint.config(text=text)
        else:
            self.mitre_hint.config(text="\u2714 = detected (at least one rule fired)")

    def _show_detail(self, row_id: str) -> None:
        s = self.session
        if s is None:
            return
        values = self.matrix_tree.item(row_id, "values")
        if not values:
            return
        tid = str(values[0]).split("\n")[0]
        tech = TECH_BY_ID.get(tid)
        findings = [f for f in s.findings if f.get("technique_id") == tid]
        row = (s.score or {}).get("matrix", {}).get(tid, {})
        fid = (s.score or {}).get("fidelity_by", {}).get(tid, "none")

        out = []
        verdict = ("\u2714 DETECTED" if fid in ("high", "low")
                   else "\u2718 NOT DETECTED")
        tag = "ex_ok" if fid in ("high", "low") else "ex_bad"
        hdr = f"{tech.id} - {tech.name}" if tech else tid
        out.append((hdr + "\n", "hdr"))
        if tech:
            out.append((f"Tactic: {', '.join(tech.tactic_list)}  \u2022  {tech.platform}\n", "mut"))
        out.append((f"Verdict: {verdict} (fidelity: {fid})\n", tag))
        out.append(("\nFindings firing on this technique:", "mut"))
        if not findings and verdict.startswith("\u2718"):
            out.append(("  (none - blind spot)\n", "mut"))
        for f in findings:
            out.append((f"  {CELL_HIT} [{f['rule_id']}] {f['rule_name']}  "
                        f"(sev {f['severity']} / {f['fidelity']})\n", "ex_ok"))
            event = str(f.get("event", ""))[:120]
            out.append((f"      {event}\n", "mut"))
        mapped_not_fired = [r.id for r in BLUE_RULES if tid in r.detects and not row.get(r.id)]
        if mapped_not_fired:
            out.append(("\nMapped but did not fire: " + ", ".join(mapped_not_fired) + "\n", "mut"))
        if tech:
            out.append(("\n" + tech.description, "mut"))
        self._write_detail(out)

    def _write_detail(self, content) -> None:
        t = self.mitre_detail
        t.configure(state="normal")
        t.delete("1.0", "end")
        if content:
            if isinstance(content, str):
                t.insert("end", content)
            elif isinstance(content, list):
                for text, tag in content:
                    t.insert("end", text, tag)
                t.insert("end", "\n")
        t.configure(state="disabled")

    def _refresh_report(self) -> None:
        s = self.session
        t = self.report_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        if s is None or not s.techniques_executed:
            t.insert("end", "No report yet. Run an exercise, then download the HTML report.\n")
        else:
            sc = s.score or {}
            t.insert("end", "What the HTML report contains:\n\n", "acc")
            t.insert("end", "\u2022 Executive summary + scoreboard (detection rate, dedicated coverage)\n", "mut")
            t.insert("end", "\u2022 Exercise timeline (red build + blue detect)\n", "mut")
            t.insert("end", "\u2022 Red build: every technique + artifact executed\n", "mut")
            t.insert("end", "\u2022 Blue detect: findings with severity + fidelity\n", "mut")
            t.insert("end", "\u2022 MITRE ATT&CK coverage matrix (technique \u00d7 rule)\n", "mut")
            t.insert("end", "\u2022 Detection blueprints, gap analysis, recommendations\n", "mut")
            t.insert("end", "\u2022 Full technique library reference\n\n", "mut")
            t.insert("end", f"Last run: {s.run_id}  \u2022  detection rate {sc.get('detection_rate', 0)}%\n",
                     "blue")
        t.configure(state="disabled")

    def _restore_last(self) -> None:
        s = load_last_session()
        if s is not None and s.techniques_executed:
            self.session = s
            self._refresh_all()
            self.status.config(text=f"Restored last session {s.run_id}"
                                    f" \u2022 detection rate {s.score.get('detection_rate')}%")

    # ---------- report actions ----------
    def _download_report(self) -> None:
        if self.session is None or not self.session.techniques_executed:
            messagebox.showwarning("Report", "Run an exercise first, then download the report.")
            return
        ensure_dirs()
        default = REPORTS_DIR / f"{APP_SLUG}_report_{now_iso().replace(':', '-')}.html"
        path = filedialog.asksaveasfilename(
            title="Save HTML report",
            initialdir=REPORTS_DIR,
            initialfile=default.name,
            defaultextension=".html",
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")])
        if not path:
            return
        self._run_worker("report", path)

    def _open_report(self) -> None:
        if self.last_report and self.last_report.exists():
            open_report(self.last_report)
            return
        newest = sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        if newest:
            open_report(newest[0])
            return
        messagebox.showwarning("Report", "No report exists yet. Download one first.")

    def _scroll_tab(self, name: str) -> None:
        mapping = {"Dashboard": 0, "Red Build": 1, "Blue Detect": 2,
                   "MITRE Coverage": 3, "Report / Export": 4}
        self.notebook.select(mapping[name])


def tk_text(parent, height: int):
    from tkinter import Text
    t = Text(parent, height=height, bg=PANEL, fg=INK, insertbackground=INK,
             relief="flat", wrap="word", font=("Consolas", 9),
             state="disabled", padx=8, pady=6)
    t.tag_configure("red", foreground=RED)
    t.tag_configure("blue", foreground=BLUE)
    t.tag_configure("acc", foreground=ACC)
    t.tag_configure("green", foreground=GREEN)
    t.tag_configure("mut", foreground=MUT)
    return t


def tk_tree(parent, cols: tuple, widths: tuple, stretch: tuple = (), style: str = "Treeview"):
    tree = ttk.Treeview(parent, columns=cols, show="headings", style=style)
    for col, w in zip(cols, widths):
        tree.column(col, width=w, anchor="w", stretch=(col in stretch))
    return tree


def _open_folder(path: Path) -> None:
    import os
    os.startfile(str(path))  # noqa: S606  (Windows desktop app; opening its own folder)


def run_gui() -> int:
    ensure_dirs()
    app = PurpleApp()
    app.mainloop()
    return 0