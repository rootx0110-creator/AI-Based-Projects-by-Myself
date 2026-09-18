"""Colorful tkinter GUI for the Red Team Engagement Report Generator."""

import os
import uuid
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import cvss, report
from .data import SEVERITIES, ReportStore, Finding, data_file, slugify
from .sample_data import SAMPLE_ENGAGEMENT, SAMPLE_FINDINGS

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG = "#12122b"
BG2 = "#1b1b38"
CARD = "#232348"
CARD2 = "#2a2a55"
TEXT = "#e8e8f5"
MUTED = "#9d9dc4"
ACCENT = "#8b7cf6"
ACCENT2 = "#22d3ee"
DANGER = "#ff5c5c"

SEV_COLORS = {
    "Critical": "#ff5c5c",
    "High": "#ff9933",
    "Medium": "#ffcf33",
    "Low": "#5ce08a",
    "None": "#8a8aa8",
}
SEV_BG = {
    "Critical": "#3a1a2e",
    "High": "#3a2a1a",
    "Medium": "#3a3320",
    "Low": "#1d3a2c",
    "None": "#25253f",
}

FONT = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI Semibold", 22)
FONT_BIG = ("Segoe UI", 28, "bold")


def color_button(parent, text, command, bg, fg="#ffffff", hover=None, width=None,
                 padx=14, pady=7, font=FONT_BOLD, image=None):
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                  activebackground=hover or bg, activeforeground=fg,
                  relief="flat", bd=0, font=font, cursor="hand2",
                  padx=padx, pady=pady, takefocus=0)
    if width:
        b.config(width=width)
    if image:
        b.config(image=image, compound="left")
    return b


class VScrollFrame(ttk.Frame):
    """A scrollable frame with an internal canvas."""

    def __init__(self, parent, bg=BG2):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _on_wheel(self, event):
        if self.canvas.winfo_containing(event.x_root, event.y_root):
            self.canvas.yview_scroll(int(-event.delta / 120) * 2, "units")


def labeled_entry(parent, label, textvariable, row_span=1, line=True):
    frame = tk.Frame(parent, bg=CARD, highlightthickness=1,
                     highlightbackground="#3a3a6e")
    frame.grid(sticky="nsew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)
    tk.Label(frame, text=label, bg=CARD, fg=MUTED, font=FONT_SM,
             anchor="w").grid(row=0, column=0, sticky="nsew", padx=14, pady=(9, 2))
    e = tk.Entry(frame, textvariable=textvariable, bg=BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=FONT)
    e.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 9), ipady=3)
    return frame


def labeled_text(parent, label, height, row_span=1):
    frame = tk.Frame(parent, bg=CARD, highlightthickness=1,
                     highlightbackground="#3a3a6e")
    frame.grid(sticky="nsew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    tk.Label(frame, text=label, bg=CARD, fg=MUTED, font=FONT_SM,
             anchor="w").grid(row=0, column=0, sticky="nsew", padx=14, pady=(9, 2))
    t = tk.Text(frame, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                font=FONT, height=height, undo=True, wrap="word")
    t.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 9), ipady=3)
    sb = tk.Scrollbar(frame, orient="vertical", command=t.yview)
    sb.grid(row=1, column=1, sticky="ns", pady=(0, 9))
    t.config(yscrollcommand=sb.set)
    return t


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Red Team Engagement Report Generator")
        self.configure(bg=BG)
        self.geometry("1240x800")
        self.minsize(1050, 700)

        self.store = ReportStore()
        self.selected_id = None
        self.silent = False

        self._build_header()
        self._build_notebook()
        self._build_statusbar()
        self._populate_findings_list()
        self._load_engagement_fields()
        self._refresh_summary_preview()

        if not self.store.findings and not self.store.engagement.get("engagement_title"):
            self.silent = True
            self.load_sample_data()
            self.silent = False

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=CARD)
        header.pack(fill="x")
        tk.Label(header, text="\U0001F6A8", font=("Segoe UI Emoji", 20),
                 bg=CARD, fg=ACCENT2).pack(side="left", padx=(22, 8), pady=12)
        bloc = tk.Frame(header, bg=CARD)
        bloc.pack(side="left")
        tk.Label(bloc, text="Red Team Engagement Report Generator",
                 font=FONT_TITLE, bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(bloc, text="findings \u2192 CVSS v3.1 \u2192 executive summary \u2192 HTML report",
                 font=FONT_SM, bg=CARD, fg=ACCENT).pack(anchor="w")
        tk.Frame(self, bg=ACCENT2, height=3).pack(fill="x")

    def _build_notebook(self):
        nb_style = ttk.Style()
        nb_style.theme_use("clam")
        nb_style.configure("TNotebook", background=BG, borderwidth=0)
        nb_style.configure("TNotebook.Tab",
                           background=CARD, foreground=MUTED, padding=(26, 9),
                           font=FONT_BOLD, borderwidth=0)
        nb_style.map("TNotebook.Tab",
                     background=[("selected", BG2)],
                     foreground=[("selected", ACCENT2)])
        nb_style.configure("Panel.TFrame", background=BG)
        nb_style.configure("Vertical.TScrollbar", background=CARD,
                           troughcolor=BG, arrowcolor=TEXT)

        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(10, 0))

        self.tab_findings = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_cvss = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_exec = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_report = ttk.Frame(self.notebook, style="Panel.TFrame")

        self.notebook.add(self.tab_findings, text="  Findings  ")
        self.notebook.add(self.tab_cvss, text="  CVSS Calculator  ")
        self.notebook.add(self.tab_exec, text="  Executive Summary  ")
        self.notebook.add(self.tab_report, text="  HTML Report  ")

        self._build_findings_tab()
        self._build_cvss_tab()
        self._build_exec_tab()
        self._build_report_tab()

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG2)
        bar.pack(fill="x", side="bottom")
        self.status_label = tk.Label(bar, text="", bg=BG2, fg=MUTED,
                                     font=FONT_SM, anchor="w", padx=14, pady=5)
        self.status_label.pack(side="left")
        self.update_status()

    # ------------------------------------------------------------------
    # Findings tab
    # ------------------------------------------------------------------
    def _build_findings_tab(self):
        t = self.tab_findings

        outer = tk.Frame(t, bg=BG)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=0, minsize=340)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        # Left: list + buttons
        left = tk.Frame(outer, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        btns = tk.Frame(left, bg=BG)
        btns.pack(fill="x", pady=(0, 8))
        self.btn_new = color_button(btns, "\u002B  New", self.new_finding, ACCENT)
        self.btn_new.pack(side="left", fill="x", expand=True)
        self.btn_dup = color_button(btns, "\u2398  Duplicate", self.duplicate_finding, ACCENT2, hover="#1fc8e2")
        self.btn_dup.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.btn_del = color_button(btns, "\u2716  Delete", self.delete_finding, DANGER)
        self.btn_del.pack(side="left", fill="x", expand=True)

        list_card = tk.Frame(left, bg=CARD, highlightthickness=1, highlightbackground="#3a3a6e")
        list_card.pack(fill="both", expand=True)
        tk.Label(list_card, text="FINDINGS", bg=CARD, fg=ACCENT2, font=FONT_SM,
                 anchor="w").pack(fill="x", padx=12, pady=(9, 3))
        self.listbox = tk.Listbox(list_card, bg=BG, fg=TEXT, selectbackground="#3a3a7a",
                                  selectforeground=TEXT, relief="flat", font=FONT,
                                  highlightthickness=0, bd=0, activestyle="none")
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        self.btn_sample = color_button(left, "\U0001F4CA  Load Sample Data",
                                       self.load_sample_data, "#37b24d")
        self.btn_sample.pack(fill="x", pady=(8, 0))

        # Right: form
        right = tk.Frame(outer, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        form_wrap = VScrollFrame(right)
        form_wrap.pack(fill="both", expand=True)
        form = form_wrap.inner
        form.columnconfigure(0, weight=1)

        # header row: title + severity badge
        head = tk.Frame(form, bg=CARD)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        head.columnconfigure(0, weight=1)
        tk.Label(head, text="FINDING DETAILS", bg=CARD, fg=ACCENT2,
                 font=FONT_BOLD).grid(row=0, column=0, sticky="w", padx=14, pady=10)
        self.badge = tk.Label(head, text="No finding selected", bg="#25253f",
                              fg=MUTED, font=FONT_BOLD, padx=18, pady=5)
        self.badge.grid(row=0, column=1, sticky="e", padx=14)

        self.var_title = tk.StringVar()
        self.var_vector = tk.StringVar()
        self.var_assets = tk.StringVar()
        self.var_status = tk.StringVar(value="Open")

        row = 1
        labeled_entry(form, "Title *", self.var_title).grid(row=row, column=0, sticky="ew")
        row += 1

        vec = labeled_entry(form, "CVSS v3.1 Vector  (e.g. CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)", self.var_vector)
        vec.grid(row=row, column=0, sticky="ew")
        row += 1
        self.vector_hint = tk.Label(form, text="", bg=BG, fg=MUTED, font=FONT_SM, anchor="w")
        self.vector_hint.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1
        self.var_vector.trace_add("write", lambda *a: self._update_vector_hint())

        assets = labeled_entry(form, "Affected Assets (comma separated)", self.var_assets)
        assets.grid(row=row, column=0, sticky="ew")
        row += 1

        st = labeled_entry(form, "Status", self.var_status)
        st.grid(row=row, column=0, sticky="ew")
        row += 1

        self.txt_desc = labeled_text(form, "Description / Root Cause", 4)
        self.txt_desc.grid(row=row, column=0, sticky="ew")
        row += 1
        self.txt_impact = labeled_text(form, "Impact", 3)
        self.txt_impact.grid(row=row, column=0, sticky="ew")
        row += 1
        self.txt_evidence = labeled_text(form, "Evidence / Reproduction Steps", 4)
        self.txt_evidence.grid(row=row, column=0, sticky="ew")
        row += 1
        self.txt_remedi = labeled_text(form, "Recommendation / Remediation", 4)
        self.txt_remedi.grid(row=row, column=0, sticky="ew")
        row += 1
        self.txt_refs = labeled_text(form, "References (CWE, links, IDs)", 2)
        self.txt_refs.grid(row=row, column=0, sticky="ew")
        row += 1

        save_row = tk.Frame(form, bg=BG)
        save_row.grid(row=row, column=0, sticky="ew", pady=(4, 20))
        self.btn_save = color_button(save_row, "Save Finding", self.save_finding, ACCENT, width=14)
        self.btn_save.pack(side="left")
        self.btn_use_cvss = color_button(save_row, "Open in CVSS Calculator", self.open_in_calculator, ACCENT2, hover="#1fc8e2", width=18)
        self.btn_use_cvss.pack(side="left", padx=10)
        tk.Label(save_row, text="* Save persists a valid or blank vector — invalid vectors score 0.",
                 bg=BG, fg=MUTED, font=FONT_SM).pack(side="left", padx=8)

    def _on_list_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        finding = self.store.sorted_findings()[idx]
        self.selected_id = finding.id
        self._load_finding(finding)

    def _load_finding(self, f):
        self.var_title.set(f.title)
        self.var_vector.set(f.cvss_vector)
        self.var_assets.set(f.affected_assets)
        self.var_status.set(f.status)
        for widget, val in ((self.txt_desc, f.description), (self.txt_impact, f.impact),
                            (self.txt_evidence, f.evidence), (self.txt_remedi, f.remediation),
                            (self.txt_refs, f.references)):
            widget.delete("1.0", "end")
            widget.insert("1.0", val)
        self._set_badge(f.severity, f.score)
        self._update_vector_hint()

    def _set_badge(self, severity, score):
        color = SEV_COLORS[severity]
        bg = SEV_BG[severity]
        score = score if score > 0 else 0.0
        self.badge.config(text=f"{severity}   |   CVSS {score:.1f}", bg=bg, fg=color)

    def _update_vector_hint(self):
        vector = self.var_vector.get()
        if not vector.strip():
            self.vector_hint.config(text="")
            return
        _, score, sev, error = cvss.calculate_base(vector)
        if error:
            self.vector_hint.config(text=error, fg=DANGER)
        else:
            self.vector_hint.config(
                text=f"Scalable to CVSS {score:.1f}  {sev}", fg=SEV_COLORS[sev])
        self._set_badge(sev, score)

    def _current_form_finding(self):
        f = Finding()
        f.title = self.var_title.get().strip()
        f.cvss_vector = self.var_vector.get().strip()
        f.affected_assets = self.var_assets.get().strip()
        f.status = self.var_status.get().strip() or "Open"
        f.description = self.txt_desc.get("1.0", "end").strip()
        f.impact = self.txt_impact.get("1.0", "end").strip()
        f.evidence = self.txt_evidence.get("1.0", "end").strip()
        f.remediation = self.txt_remedi.get("1.0", "end").strip()
        f.references = self.txt_refs.get("1.0", "end").strip()
        return f

    def new_finding(self):
        if self._confirm_discard():
            self.selected_id = None
            self._clear_form()
            self._set_badge("None", 0)
            self.listbox.selection_clear(0, "end")

    def _confirm_discard(self):
        if self.var_title.get().strip():
            return messagebox.askyesno("New finding",
                                       "Clear the current form? Unsaved data will be lost.")
        return True

    def _clear_form(self):
        self.var_title.set("")
        self.var_vector.set("")
        self.var_assets.set("")
        self.var_status.set("Open")
        for widget in (self.txt_desc, self.txt_impact, self.txt_evidence,
                       self.txt_remedi, self.txt_refs):
            widget.delete("1.0", "end")
        self._update_vector_hint()

    def save_finding(self):
        f = self._current_form_finding()
        if not f.title:
            messagebox.showwarning("Missing title", "A finding title is required.")
            return

        if self.selected_id:
            existing = next((x for x in self.store.findings if x.id == self.selected_id), None)
            if existing:
                f.id = existing.id
                self.store.findings[self.store.findings.index(existing)] = f
            else:
                self.store.findings.append(f)
        else:
            self.store.findings.append(f)
        self.store.save()
        self.selected_id = f.id
        self._populate_findings_list(f.id)
        self._refresh_all()
        self.update_status()

    def duplicate_finding(self):
        if not self.selected_id:
            messagebox.showinfo("Duplicate", "Select a finding to duplicate first.")
            return
        src = next((x for x in self.store.findings if x.id == self.selected_id), None)
        if not src:
            return
        f = Finding.from_dict(src.to_dict())
        f.id = uuid.uuid4().hex[:12]
        f.title = src.title + " (copy)"
        self.store.add(f)
        self._populate_findings_list(f.id)
        self._refresh_all()

    def delete_finding(self):
        if not self.selected_id:
            messagebox.showinfo("Delete", "Select a finding to delete first.")
            return
        existing = next((x for x in self.store.findings if x.id == self.selected_id), None)
        if not existing:
            return
        if messagebox.askyesno("Delete finding", f'Delete "{existing.title}"?'):
            self.store.remove(existing)
            self.selected_id = None
            self._populate_findings_list()
            self._clear_form()
            self._refresh_all()

    def open_in_calculator(self):
        self.var_vector.get()
        self.notebook.select(self.tab_cvss)
        self._sync_cvss_from_vector()

    def load_sample_data(self):
        if (self.store.findings or self.var_eng_title.get().strip()
                and not self.silent and not messagebox.askyesno(
                    "Load Sample Data",
                    "This replaces the current engagement with the built-in sample "
                    "dataset. Continue?", parent=self)):
            return
        self.store.engagement = dict(SAMPLE_ENGAGEMENT)
        self.store.findings = [Finding.from_dict(d) for d in SAMPLE_FINDINGS]
        self.store.save()
        self.selected_id = None
        self._load_engagement_fields()
        self._populate_findings_list()
        self._clear_form()
        self._refresh_all()
        if not self.silent:
            messagebox.showinfo(
                "Sample data loaded",
                f"Loaded the Acme Corporation sample engagement with "
                f"{len(self.store.findings)} findings.\n\nQuick tour:\n"
                f"  1. Findings tab  - select each colour-coded finding.\n"
                f"  2. CVSS Calculator - change a metric, then 'Apply to Selected Finding'.\n"
                f"  3. Executive Summary - hit 'Regenerate Summary'.\n"
                f"  4. HTML Report - 'Generate Report', then 'Save HTML...' or 'Open in Browser'.",
                parent=self)

    def _populate_findings_list(self, select_id=None):
        self.listbox.delete(0, "end")
        for f in self.store.sorted_findings():
            score = f.score
            sev = f.severity
            label = f"[\u25CF] {sev.upper():8s} | {f.title}  ({score:.1f})"
            self.listbox.insert("end", label)
            idx = self.listbox.size() - 1
            self.listbox.itemconfig(idx, foreground=SEV_COLORS[sev])
        if select_id:
            for i, f in enumerate(self.store.sorted_findings()):
                if f.id == select_id:
                    self.listbox.selection_set(i)
                    self.listbox.see(i)
                    self.selected_id = select_id
                    self._load_finding(f)
                    break
        self.update_status()

    # ------------------------------------------------------------------
    # CVSS calculator tab
    # ------------------------------------------------------------------
    def _build_cvss_tab(self):
        t = self.tab_cvss
        wrapper = tk.Frame(t, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=30, pady=20)
        wrapper.columnconfigure(0, weight=0, minsize=560)
        wrapper.columnconfigure(1, weight=1)

        left = tk.Frame(wrapper, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 24))

        tk.Label(left, text="CVSS v3.1 METRICS", bg=BG, fg=ACCENT2,
                 font=FONT_BOLD).pack(anchor="w", pady=(0, 10))

        self.metric_vars = {}
        order = [["AV", ["N", "A", "L", "P"], ["Network", "Adjacent", "Local", "Physical"]],
                 ["AC", ["L", "H"], ["Low", "High"]],
                 ["PR", ["N", "L", "H"], ["None", "Low", "High"]],
                 ["UI", ["N", "R"], ["None", "Required"]],
                 ["S", ["U", "C"], ["Unchanged", "Changed"]],
                 ["C", ["H", "L", "N"], ["High", "Low", "None"]],
                 ["I", ["H", "L", "N"], ["High", "Low", "None"]],
                 ["A", ["H", "L", "N"], ["High", "Low", "None"]]]
        for metric, values, labels in order:
            card = tk.Frame(left, bg=CARD, highlightthickness=1, highlightbackground="#3a3a6e")
            card.pack(fill="x", pady=4)
            tk.Label(card, text=f"{metric}  —  {cvss.METRIC_NAMES[metric]}",
                     bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor="w", padx=12, pady=(8, 2))
            tk.Label(card, text=cvss.METRIC_HELP[metric].splitlines()[0],
                     bg=CARD, fg=MUTED, font=FONT_SM).pack(anchor="w", padx=12)
            combo_card = tk.Frame(card, bg=CARD)
            combo_card.pack(fill="x", padx=12, pady=(4, 10))
            self.metric_vars[metric] = (var := tk.StringVar(value="N" if metric not in ("S", "AC") else "U" if metric == "S" else "L"))
            combo = ttk.Combobox(combo_card, textvariable=var, state="readonly",
                                 values=labels, font=FONT)
            combo.pack(fill="x")
            combo.bind("<<ComboboxSelected>>",
                       lambda e, m=metric, ls=labels: self._on_metric_change(m, ls))
            style = ttk.Style()
            style.configure("Metric.TCombobox", fieldbackground=BG,
                            background=CARD2, foreground=TEXT)
            style.map("Metric.TCombobox",
                      fieldbackground=[("readonly", BG)],
                      selectbackground=[("readonly", BG)],
                      selectforeground=[("readonly", ACCENT2)],
                      foreground=[("readonly", TEXT)])
            combo.configure(style="Metric.TCombobox")

        # Right: big score display
        right = tk.Frame(wrapper, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        score_card = tk.Frame(right, bg=CARD, highlightthickness=1,
                              highlightbackground="#3a3a6e")
        score_card.pack(fill="x", pady=(0, 12))
        tk.Label(score_card, text="LIVE BASE SCORE", bg=CARD, fg=MUTED,
                 font=FONT_SM).pack(pady=(16, 2))
        self.score_label = tk.Label(score_card, text="0.0", bg=CARD, fg=SEV_COLORS["None"],
                                    font=FONT_BIG)
        self.score_label.pack(pady=(0, 0))
        self.sev_label = tk.Label(score_card, text="None", bg=CARD, fg=MUTED, font=FONT_BOLD)
        self.sev_label.pack(pady=(0, 4))
        self.score_bar = tk.Canvas(score_card, height=14, bg=BG, highlightthickness=0)
        self.score_bar.pack(fill="x", padx=24, pady=(4, 18))
        tk.Label(score_card, text="0                   2.5                   5                   7.5                   10",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(fill="x", padx=28, pady=(0, 12))

        vector_card = tk.Frame(right, bg=CARD, highlightthickness=1,
                               highlightbackground="#3a3a6e")
        vector_card.pack(fill="x")
        tk.Label(vector_card, text="VECTOR", bg=CARD, fg=MUTED,
                 font=FONT_SM).pack(anchor="w", padx=12, pady=(10, 2))
        self.vector_readout = tk.Label(vector_card, text="", bg=CARD, fg=ACCENT2,
                                       font=("Consolas", 11), anchor="w", justify="left")
        self.vector_readout.pack(fill="x", padx=12, pady=(0, 10))

        btns = tk.Frame(right, bg=BG)
        btns.pack(fill="x", pady=14)
        self.btn_apply_cvss = color_button(btns, "Apply to Selected Finding",
                                           self.apply_cvss_to_finding, ACCENT2, hover="#1fc8e2")
        self.btn_apply_cvss.pack(fill="x")

        self._sync_cvss_from_vector()

    def _metrics_spec(self):
        return [["AV", ["N", "A", "L", "P"], ["Network", "Adjacent", "Local", "Physical"]],
                ["AC", ["L", "H"], ["Low", "High"]],
                ["PR", ["N", "L", "H"], ["None", "Low", "High"]],
                ["UI", ["N", "R"], ["None", "Required"]],
                ["S", ["U", "C"], ["Unchanged", "Changed"]],
                ["C", ["H", "L", "N"], ["High", "Low", "None"]],
                ["I", ["H", "L", "N"], ["High", "Low", "None"]],
                ["A", ["H", "L", "N"], ["High", "Low", "None"]]]

    def _on_metric_change(self, metric, labels):
        self.var_vector.set(self._build_vector_from_cvss())
        self._update_cvss_display()

    def _build_vector_from_cvss(self):
        values = {}
        spec = {m: ls for m, _, ls in self._metrics_spec()}
        for m, labels in spec.items():
            var = self.metric_vars[m].get()
            idx = labels.index(var) if var in labels else 0
            values[m] = cvss.METRIC_OPTIONS[m][idx]
        return "CVSS:3.1/" + "/".join(f"{m}:{values[m]}" for m in cvss.METRIC_ORDER)

    def _sync_cvss_from_vector(self):
        vector = self.var_vector.get() or (self.selected_id and
                                           next((f.cvss_vector for f in self.store.findings
                                                 if f.id == self.selected_id), "")) or ""
        metrics, _ = cvss.parse_vector(vector)
        spec = {m: ls for m, _, ls in self._metrics_spec()}
        if metrics:
            for m, labels in spec.items():
                val = metrics.get(m, "N")
                if val in cvss.METRIC_OPTIONS[m]:
                    label = cvss.METRIC_VALUE_NAMES[m][val]
                    self.metric_vars[m].set(label)
        self.var_vector.set(vector)
        self._update_cvss_display()

    def _update_cvss_display(self):
        vector = self._build_vector_from_cvss()
        self.var_vector.set(vector)
        _, score, sev, err = cvss.calculate_base(vector)
        if err:
            score, sev = 0.0, "None"
        self.score_label.config(text=f"{score:.1f}", fg=SEV_COLORS[sev])
        self.sev_label.config(text=sev, fg=SEV_COLORS[sev])
        self.vector_readout.config(text=vector)
        self.score_bar.delete("all")
        colors = [SEV_COLORS["Critical"], SEV_COLORS["High"], SEV_COLORS["Medium"],
                  SEV_COLORS["Low"]]
        width = self.score_bar.winfo_width() or 800
        seg = width / 4.0
        for i in range(4):
            x0 = i * seg
            self.score_bar.create_rectangle(x0, 0, x0 + seg, 14, fill=colors[i], outline="")
        pos = min(score, 10.0) / 10.0 * width
        self.score_bar.create_oval(pos - 6, 2, pos + 6, 12, fill="#ffffff", outline="")

    def apply_cvss_to_finding(self):
        if not self.selected_id:
            messagebox.showinfo("Apply vector", "Select a finding on the Findings tab first.")
            return
        f = next((x for x in self.store.findings if x.id == self.selected_id), None)
        if not f:
            return
        f.cvss_vector = self._build_vector_from_cvss()
        self.store.update()
        self.var_vector.set(f.cvss_vector)
        self._populate_findings_list(f.id)
        self._refresh_all()
        self.notebook.select(self.tab_findings)

    # ------------------------------------------------------------------
    # Executive summary tab
    # ------------------------------------------------------------------
    def _build_exec_tab(self):
        t = self.tab_exec
        wrapper = tk.Frame(t, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=30, pady=20)
        wrapper.columnconfigure(0, weight=0, minsize=460)
        wrapper.columnconfigure(1, weight=1)
        wrapper.rowconfigure(0, weight=1)

        left = tk.Frame(wrapper, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        left.columnconfigure(0, weight=1)

        tk.Label(left, text="ENGAGEMENT DETAILS", bg=BG, fg=ACCENT2,
                 font=FONT_BOLD).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.var_eng_title = tk.StringVar()
        self.var_client = tk.StringVar()
        self.var_assessor = tk.StringVar()
        self.var_start = tk.StringVar()
        self.var_end = tk.StringVar()
        self.var_scope = tk.StringVar()

        fields = [("Engagement Title", self.var_eng_title),
                  ("Client Name", self.var_client),
                  ("Assessor / Team", self.var_assessor),
                  ("Start Date (YYYY-MM-DD)", self.var_start),
                  ("End Date (YYYY-MM-DD)", self.var_end),
                  ("Scope / Targets", self.var_scope)]
        r = 1
        for label, var in fields:
            labeled_entry(left, label, var).grid(row=r, column=0, sticky="ew")
            r += 1

        tk.Label(left, text="Summary Notes (optional context)", bg=BG, fg=MUTED,
                 font=FONT_SM).grid(row=r, column=0, sticky="w", pady=(4, 4))
        r += 1
        self.txt_notes = tk.Text(left, bg=CARD, fg=TEXT, insertbackground=TEXT,
                                 relief="flat", font=FONT, height=5, wrap="word",
                                 highlightthickness=1, highlightbackground="#3a3a6e")
        self.txt_notes.grid(row=r, column=0, sticky="nsew", pady=(0, 12))
        r += 1

        btns = tk.Frame(left, bg=BG)
        btns.grid(row=r, column=0, sticky="ew")
        color_button(btns, "Save Engagement Details", self.save_engagement,
                     ACCENT).pack(side="left")
        color_button(btns, "Regenerate Summary", self.regenerate_summary,
                     ACCENT2, hover="#1fc8e2").pack(side="left", padx=10)

        right = tk.Frame(wrapper, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        preview_card = tk.Frame(right, bg=CARD, highlightthickness=1,
                                highlightbackground="#3a3a6e")
        preview_card.pack(fill="both", expand=True)
        tk.Label(preview_card, text="AUTO-GENERATED EXECUTIVE SUMMARY  (regenerated when findings / details change)",
                 bg=CARD, fg=MUTED, font=FONT_SM).pack(anchor="w", padx=14, pady=(10, 4))
        self.summary_text = tk.Text(preview_card, bg=BG, fg=TEXT, insertbackground=TEXT,
                                    relief="flat", font=FONT, wrap="word", state="disabled",
                                    padx=12, pady=12)
        self.summary_text.pack(fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(preview_card, command=self.summary_text.yview)
        self.summary_text.config(yscrollcommand=sb.set)
        sb.pack_forget()

    def _load_engagement_fields(self):
        self.var_eng_title.set(self.store.engagement["engagement_title"])
        self.var_client.set(self.store.engagement["client_name"])
        self.var_assessor.set(self.store.engagement["assessor"])
        self.var_start.set(self.store.engagement["start_date"])
        self.var_end.set(self.store.engagement["end_date"])
        self.var_scope.set(self.store.engagement["scope"])
        self.txt_notes.delete("1.0", "end")
        self.txt_notes.insert("1.0", self.store.engagement["summary_notes"])

    def save_engagement(self, notify=True):
        self.store.engagement.update({
            "engagement_title": self.var_eng_title.get().strip(),
            "client_name": self.var_client.get().strip(),
            "assessor": self.var_assessor.get().strip(),
            "start_date": self.var_start.get().strip(),
            "end_date": self.var_end.get().strip(),
            "scope": self.var_scope.get().strip(),
            "summary_notes": self.txt_notes.get("1.0", "end").strip(),
        })
        self.store.save()
        self._refresh_summary_preview()
        if notify:
            messagebox.showinfo("Saved", "Engagement details saved.")

    def regenerate_summary(self):
        self.save_engagement(notify=False)

    def _sync_engagement_from_form(self):
        self.store.engagement.update({
            "engagement_title": self.var_eng_title.get().strip(),
            "client_name": self.var_client.get().strip(),
            "assessor": self.var_assessor.get().strip(),
            "start_date": self.var_start.get().strip(),
            "end_date": self.var_end.get().strip(),
            "scope": self.var_scope.get().strip(),
            "summary_notes": self.txt_notes.get("1.0", "end").strip(),
        })

    def _refresh_summary_preview(self):
        self._sync_engagement_from_form()
        paragraphs, counts = report.build_executive_summary(self.store)

        def set_text(txt, content):
            txt.config(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", content)
            txt.config(state="disabled")

        content = (
            "SEVERITY DISTRIBUTION\n"
            + "  ".join(f"{s}: {counts[s]}" for s in SEVERITIES) + "\n\n"
            + ("=" * 60) + "\n\n"
            + "\n\n".join(paragraphs)
        )
        if hasattr(self, "summary_text"):
            set_text(self.summary_text, content)

    # ------------------------------------------------------------------
    # HTML report tab
    # ------------------------------------------------------------------
    def _build_report_tab(self):
        t = self.tab_report
        wrapper = tk.Frame(t, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=30, pady=20)

        hero = tk.Frame(wrapper, bg=CARD, highlightthickness=1, highlightbackground="#3a3a6e")
        hero.pack(fill="x", pady=(0, 14))
        tk.Label(hero, text="\U0001F4C4  HTML Report", bg=CARD, fg=ACCENT2,
                 font=FONT_BOLD).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(hero, text="Generates a styled, self-contained HTML document with the executive "
                            "summary, CVSS scores and full findings detail.",
                 bg=CARD, fg=MUTED, font=FONT_SM).pack(anchor="w", padx=16, pady=(0, 12))

        actions = tk.Frame(wrapper, bg=BG)
        actions.pack(fill="x", pady=(0, 12))
        color_button(actions, "\U0001F5AB  Generate Report", self.generate_report,
                     ACCENT).pack(side="left")
        color_button(actions, "\U0001F4BE  Save HTML...", self.save_html_report,
                     ACCENT2, hover="#1fc8e2").pack(side="left", padx=10)
        color_button(actions, "\U0001F310  Open in Browser", self.open_in_browser,
                     "#37b24d").pack(side="left")

        preview_card = tk.Frame(wrapper, bg=CARD, highlightthickness=1,
                                highlightbackground="#3a3a6e")
        preview_card.pack(fill="both", expand=True)
        tk.Label(preview_card, text="REPORT PREVIEW", bg=CARD, fg=MUTED,
                 font=FONT_SM).pack(anchor="w", padx=14, pady=(10, 4))
        self.preview_text = tk.Text(preview_card, bg=BG, fg=TEXT, insertbackground=TEXT,
                                    relief="flat", font=FONT, wrap="word", state="disabled",
                                    padx=14, pady=12)
        self.preview_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._last_html = ""

    def generate_report(self):
        self._sync_engagement_from_form()
        self.store.save()
        self._last_html = report.build_html_report(self.store)

        def set_text(txt, content):
            txt.config(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", content)
            txt.config(state="disabled")

        preview = self._last_html
        # Plain-text-ish preview
        title = self.store.engagement["engagement_title"] or "Red Team Engagement Report"
        findings = self.store.sorted_findings()
        lines = [f"PREVIEW OF: {title}",
                 f"Findings: {len(findings)}",
                 "=" * 64, ""]
        for i, f in enumerate(findings, 1):
            lines.append(f"### {i}. {f.title}")
            lines.append(f"    Severity: {f.severity}   |   CVSS: {f.score:.1f}")
            lines.append(f"    Vector:  {f.cvss_vector or '-'}")
            lines.append(f"    Status:  {f.status}")
            if f.affected_assets:
                lines.append(f"    Assets:  {f.affected_assets}")
            if f.description:
                lines.append(f"    Desc:    {' '.join(f.description.splitlines())[:140]}...")
            lines.append("")
        set_text(self.preview_text, "\n".join(lines))
        self._refresh_summary_preview()

    def _suggest_path(self):
        title = slugify(self.store.engagement.get("engagement_title") or "red_team_report")
        return os.path.join(os.path.expanduser("~"), "Desktop",
                            f"{title}_{self.store.engagement.get('start_date') or 'report'}.html")

    def save_html_report(self):
        if not self._last_html:
            self.generate_report()
        path = filedialog.asksaveasfilename(
            title="Save HTML report",
            defaultextension=".html",
            initialfile=os.path.basename(self._suggest_path()),
            filetypes=[("HTML document", "*.html"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self._last_html)
        messagebox.showinfo("Saved", f"Report saved to:\n{path}")

    def open_in_browser(self):
        if not self._last_html:
            self.generate_report()
        path = os.path.join(data_file() and os.path.dirname(data_file()) or os.getcwd(),
                            "_preview_report.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self._last_html)
        webbrowser.open("file://" + path.replace("\\", "/"))

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _refresh_all(self):
        self._refresh_summary_preview()
        self.update_status()

    def update_status(self):
        counts = self.store.severity_counts()
        txt = (f"Findings: {len(self.store.findings)}   |   "
               + "  ".join(f"{s}: {counts[s]}" for s in SEVERITIES if counts[s]))
        self.status_label.config(
            text=txt + "      Data file: " + self.store.path)

    def run(self):
        self.mainloop()


def launch():
    App().run()