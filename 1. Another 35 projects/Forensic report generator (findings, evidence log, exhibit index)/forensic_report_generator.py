"""
Forensic Report Generator
=========================
Desktop application for building professional forensic / digital-investigation
reports. Maintains case information, findings, an evidence log (with chain of
custody records) and an exhibit index, and exports an industry-standard report
in HTML format.

The user interface uses a warm neutral palette (no dark mode, no white
backgrounds) for comfortable, professional use.
"""

import json
import os
import re
import sys
import webbrowser
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont

# --------------------------------------------------------------------------- #
#  Application constants
# --------------------------------------------------------------------------- #

APP_NAME = "Forensic Report Generator"
APP_VERSION = "1.0.0"

# ---- Warm neutral palette (no dark, no white) ---- #
CLR_BG          = "#EDE7DB"   # main window background - light greige
CLR_PANEL       = "#F5F0E6"   # panel / raised surface - parchment
CLR_PANEL_ALT   = "#E5DECC"   # alternate panel - slightly deeper beige
CLR_HEADER      = "#6A5B45"   # header bar - warm taupe
CLR_HEADER_TXT  = "#F5F0E6"
CLR_TEXT        = "#2F2A22"   # primary text - warm charcoal
CLR_TEXT_SUB    = "#6E6658"   # secondary text
CLR_BORDER      = "#C9BFAA"   # borders
CLR_ACCENT      = "#5F7169"   # primary accent - muted sage/moss
CLR_ACCENT_DK   = "#4A5B54"
CLR_BTN         = "#D8D0BD"   # standard button
CLR_BTN_TXT     = "#2F2A22"
CLR_BTN_PRIMARY = "#5F7169"
CLR_BTN_PRIMARY_TXT = "#F5F0E6"
CLR_ENTRY       = "#FAF6EC"   # input backgrounds - near paper, not white
CLR_ENTRY_DIS   = "#E9E3D5"
CLR_HDR_BG      = "#D8D0BD"   # table header


# =========================================================================== #
#  Data layer
# =========================================================================== #

SEVERITIES = [
    ("Critical", "critical"),
    ("High", "high"),
    ("Medium", "medium"),
    ("Low", "low"),
    ("Informational", "information"),
]

EVIDENCE_TYPES = [
    "Digital Device", "Storage Media", "Network / Traffic Data",
    "Document / Record", "Photograph / Image", "Audio / Video",
    "Physical Item", "Log File", "Cloud / Account Data", "Other",
]

EXHIBIT_TYPES = [
    "Original Evidence", "Forensic Copy", "Digital File / Image",
    "Photograph", "Report / Document", "Other",
]

EVIDENCE_STATUS = [
    "In Custody", "Under Examination", "Processed", "Released",
    "Returned", "Destroyed", "Pending",
]

FINDING_STATUS = [
    "Open", "Verified", "Partially Verified", "Disputed", "Closed",
]

CASE_TYPES = [
    "Digital Forensics", "Cyber Incident", "Fraud Investigation",
    "Data Breach", "Intellectual Property", "Employee Misconduct",
    "Criminal Investigation", "Civil Litigation", "Regulatory",
    "Internal Review", "Other",
]

HEADERS = ["Case Information", "Findings", "Evidence Log", "Exhibit Index", "Report"]

MINIMAL_CASE = {
    "case_number": "",
    "case_title": "",
    "agency": "",
    "case_type": "",
    "investigator": "",
    "assistants": "",
    "date_opened": "",
    "date_closed": "",
    "jurisdiction": "",
    "classification": "",
    "status": "",
    "summary": "",
    "description": "",
}

MINIMAL_FINDING = {
    "finding_id": "",
    "title": "",
    "category": "",
    "severity": "Medium",
    "date": "",
    "status": "Open",
    "location": "",
    "description": "",
    "recommendation": "",
}

MINIMAL_EVIDENCE = {
    "evidence_id": "",
    "description": "",
    "type": "Digital Device",
    "source_location": "",
    "seized_by": "",
    "datetime": "",
    "status": "In Custody",
    "hash": "",
    "notes": "",
    "custody": [],   # [{date, from, to, reason}]
}

MINIMAL_EXHIBIT = {
    "exhibit_id": "",
    "description": "",
    "type": "Original Evidence",
    "evidence_ref": "",
    "date": "",
    "location": "",
    "notes": "",
}


def new_project():
    """Return a clean project dictionary."""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "meta": {"created": datetime.now().isoformat(), "modified": datetime.now().isoformat()},
        "case": dict(MINIMAL_CASE),
        "findings": [],
        "evidence": [],
        "exhibits": [],
    }


def clone(obj):
    return json.loads(json.dumps(obj))


# =========================================================================== #
#  Wrapped text widget with date picker helpers
# =========================================================================== #

class WrappedLabel(tk.Label):
    """Label that wraps text to a given width."""

    def __init__(self, master, text="", width=60, **kw):
        kw.setdefault("background", CLR_PANEL)
        kw.setdefault("foreground", CLR_TEXT_SUB)
        kw.setdefault("justify", "left")
        kw.setdefault("anchor", "w")
        super().__init__(master, text=text, wraplength=width, **kw)


class ScrollableText(tk.Frame):
    """A labelled multiline text box with its own vertical scrollbar."""

    def __init__(self, master, label="", height=4, **kw):
        super().__init__(master, background=CLR_PANEL)
        self.col = 0
        self.row = 0
        if label:
            self.lbl = tk.Label(self, text=label, background=CLR_PANEL,
                                foreground=CLR_TEXT, font=("Segoe UI", 9, "bold"),
                                anchor="w")
            self.lbl.grid(row=0, column=0, sticky="w", pady=(0, 3))
            self.row = 1
        self.text = tk.Text(self, height=height, wrap=tk.WORD,
                            background=CLR_ENTRY, foreground=CLR_TEXT,
                            insertbackground=CLR_TEXT, relief="flat",
                            highlightthickness=1, highlightbackground=CLR_BORDER,
                            highlightcolor=CLR_ACCENT, undo=True, **kw)
        self.scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.grid(row=self.row, column=0, sticky="nsew")
        self.scroll.grid(row=self.row, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(self.row, weight=1)

    def get(self):
        return self.text.get("1.0", "end-1c").strip()

    def set(self, value):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value or "")

    def clear(self):
        self.set("")


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


# =========================================================================== #
#  Custom themed styles
# =========================================================================== #

def build_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=CLR_BG, foreground=CLR_TEXT,
                    font=("Segoe UI", 10))
    style.configure("TFrame", background=CLR_BG)
    style.configure("Panel.TFrame", background=CLR_PANEL)
    style.configure("TLabel", background=CLR_BG, foreground=CLR_TEXT,
                    font=("Segoe UI", 10))
    style.configure("Panel.TLabel", background=CLR_PANEL, foreground=CLR_TEXT)
    style.configure("Heading.TLabel", background=CLR_HEADER,
                    foreground=CLR_HEADER_TXT,
                    font=("Segoe UI", 16, "bold"))
    style.configure("SubHead.TLabel", background=CLR_BG, foreground=CLR_ACCENT_DK,
                    font=("Segoe UI", 11, "bold"))
    style.configure("SubHeadPanel.TLabel", background=CLR_PANEL,
                    foreground=CLR_ACCENT_DK, font=("Segoe UI", 11, "bold"))

    # Notebook
    style.configure("TNotebook", background=CLR_BG, borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=CLR_PANEL_ALT, foreground=CLR_TEXT,
                    padding=(16, 8), font=("Segoe UI", 10),
                    borderwidth=1, focusthickness=0)
    style.map("TNotebook.Tab",
              background=[("selected", CLR_PANEL), ("active", "#EAE3D2")],
              foreground=[("selected", CLR_ACCENT_DK)])

    # Buttons
    style.configure("TButton", background=CLR_BTN, foreground=CLR_BTN_TXT,
                    padding=(12, 6), relief="flat", borderwidth=1,
                    font=("Segoe UI", 10))
    style.map("TButton",
              background=[("active", "#CEC5AE"), ("pressed", "#C3B9A0")],
              foreground=[("disabled", CLR_TEXT_SUB)])
    style.configure("Primary.TButton", background=CLR_BTN_PRIMARY,
                    foreground=CLR_BTN_PRIMARY_TXT, font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton",
              background=[("active", CLR_ACCENT_DK), ("pressed", "#3C4C46")],
              foreground=[("disabled", CLR_BTN_PRIMARY_TXT)])
    style.configure("Tool.TButton", background=CLR_PANEL, padding=(8, 4))
    style.map("Tool.TButton",
              background=[("active", "#E6DFCB")], relief="flat")

    # Entries
    style.configure("TEntry", fieldbackground=CLR_ENTRY, foreground=CLR_TEXT,
                    insertcolor=CLR_TEXT, bordercolor=CLR_BORDER,
                    lightcolor=CLR_BORDER, darkcolor=CLR_BORDER)
    style.map("TEntry", fieldbackground=[("disabled", CLR_ENTRY_DIS)])
    style.configure("TCombobox", fieldbackground=CLR_ENTRY,
                    background=CLR_BTN, foreground=CLR_TEXT,
                    arrowcolor=CLR_ACCENT_DK)
    style.map("TCombobox",
              fieldbackground=[("readonly", CLR_ENTRY)],
              foreground=[("readonly", CLR_TEXT)])
    style.configure("TSpinbox", fieldbackground=CLR_ENTRY,
                    foreground=CLR_TEXT, background=CLR_BTN, arrowsize=14)

    # Treeview
    style.configure("Treeview", background=CLR_ENTRY, fieldbackground=CLR_ENTRY,
                    foreground=CLR_TEXT, rowheight=26,
                    bordercolor=CLR_BORDER, relief="flat")
    style.map("Treeview", background=[("selected", CLR_ACCENT)],
              foreground=[("selected", CLR_HEADER_TXT)])
    style.configure("Treeview.Heading", background=CLR_HDR_BG,
                    foreground=CLR_TEXT, font=("Segoe UI", 9, "bold"),
                    relief="flat", padding=(6, 5))
    style.map("Treeview.Heading", background=[("active", "#CCC3AD"),
                                              ("pressed", "#C3BAA3")])

    # Scrollbars
    style.configure("Vertical.TScrollbar", background=CLR_BTN,
                    troughcolor=CLR_BG, bordercolor=CLR_BG, arrowcolor=CLR_ACCENT_DK)
    style.configure("Horizontal.TScrollbar", background=CLR_BTN,
                    troughcolor=CLR_BG, bordercolor=CLR_BG, arrowcolor=CLR_ACCENT_DK)

    style.configure("TProgressbar", background=CLR_ACCENT, troughcolor=CLR_PANEL_ALT)

    # Separator
    style.configure("TSeparator", background=CLR_BORDER)


# =========================================================================== #
#  Simple form helpers
# =========================================================================== #

def make_row(parent, col_count=3):
    """Configure a grid so labeled widgets place nicely."""
    for i in range(col_count):
        parent.columnconfigure(i, weight=1)


class FieldRow(tk.Frame):
    """A labeled entry / combobox row for forms."""

    def __init__(self, master, label, kind="entry", values=None, width=28):
        super().__init__(master, background=CLR_PANEL)
        self.lbl = tk.Label(self, text=label, background=CLR_PANEL,
                            foreground=CLR_TEXT_SUB, font=("Segoe UI", 9),
                            anchor="e", width=16)
        self.lbl.pack(side="left", padx=(0, 6))
        if kind == "combobox":
            self.var = tk.StringVar()
            self.widget = ttk.Combobox(self, textvariable=self.var,
                                       values=values or [], width=width,
                                       state="readonly")
        else:
            self.var = tk.StringVar()
            self.widget = ttk.Entry(self, textvariable=self.var, width=width)
        self.widget.pack(side="left", fill="x", expand=True)

    @property
    def value(self):
        return self.var.get().strip()

    @value.setter
    def value(self, v):
        self.var.set(v or "")


class DateRow(FieldRow):
    """Entry plus a quick 'today' button."""

    def __init__(self, master, label, width=14):
        super().__init__(master, label, width=width)
        self.today_btn = ttk.Button(self, text="Today", width=6,
                                    command=self._set_today)
        self.today_btn.pack(side="left", padx=(6, 0))

    def _set_today(self):
        self.value = today_text()


def spacer(parent, height=6, bg=CLR_PANEL):
    f = tk.Frame(parent, background=bg, height=height)
    f.grid_propagate(False)
    f.pack(fill="x")
    return f


# =========================================================================== #
#  Findings dialog
# =========================================================================== #

class EntryDialog(tk.Toplevel):
    """Generic add / edit dialog for findings, evidence and exhibits."""

    def __init__(self, master, title, record=None, fields="finding"):
        super().__init__(master)
        self.title(title)
        self.configure(background=CLR_PANEL)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.record = record or {}
        self.fields = fields
        self.controls = {}
        self.result = None

        inner = tk.Frame(self, background=CLR_PANEL, padx=18, pady=14)
        inner.pack(fill="both", expand=True)

        self._build(inner)

        btns = tk.Frame(self, background=CLR_PANEL, pady=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="Save", style="Primary.TButton",
                   command=self._save).pack(side="right", padx=8)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._save())
        self.update_idletasks()
        self._center(master)

    def _center(self, master):
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    # -- field builders ------------------------------------------------ #
    def _entry(self, parent, key, label):
        row = FieldRow(parent, label)
        self.controls[key] = row.var
        row.pack(fill="x", pady=3)
        return row

    def _combobox(self, parent, key, label, values):
        row = FieldRow(parent, label, kind="combobox", values=values)
        self.controls[key] = row.var
        row.pack(fill="x", pady=3)
        return row

    def _date(self, parent, key, label):
        row = DateRow(parent, label)
        self.controls[key] = row.var
        row.pack(fill="x", pady=3)
        return row

    def _text(self, parent, key, label, height=4):
        box = ScrollableText(parent, label, height=height)
        box.pack(fill="both", expand=True, pady=(6, 2))
        self.controls[key] = box
        return box

    def _load(self):
        for key, ctrl in self.controls.items():
            val = self.record.get(key, "")
            if isinstance(ctrl, ScrollableText):
                ctrl.set(val)
            else:
                ctrl.set(val)

    def _save(self):
        record = dict(self.record)
        for key, ctrl in self.controls.items():
            record[key] = ctrl.get() if isinstance(ctrl, ScrollableText) else ctrl.get().strip()
        record = self._validate(record)
        if record is not None:
            self.result = record
            self.destroy()

    # -- overridable --------------------------------------------------- #
    def _build(self, parent):
        pass

    def _validate(self, record):
        return record


class FindingDialog(EntryDialog):
    def _build(self, parent):
        self._entry(parent, "finding_id", "Finding ID")
        self._entry(parent, "title", "Title")
        self._combobox(parent, "category", "Category",
                       ["Malware", "Unauthorized Access", "Data Exfiltration",
                        "Anomalous Activity", "Policy Violation", "Timeline Item",
                        "Artifact", "User Activity", "Other"])
        self._combobox(parent, "severity", "Severity", [s[0] for s in SEVERITIES])
        self._date(parent, "date", "Date")
        self._combobox(parent, "status", "Status", FINDING_STATUS)
        self._entry(parent, "location", "Evidence / Location")
        self._text(parent, "description", "Description", height=5)
        self._text(parent, "recommendation", "Recommendation", height=3)
        self._load()

    def _validate(self, r):
        if not r["title"]:
            messagebox.showwarning("Missing information", "A finding title is required.",
                                   parent=self)
            return None
        return r


class EvidenceDialog(EntryDialog):
    def __init__(self, master, record=None, used_ids=()):
        self._custody = list(record.get("custody", [])) if record else []
        super().__init__(master, "Evidence Record", record, "evidence")

    def _build(self, parent):
        top = tk.Frame(parent, background=CLR_PANEL)
        top.pack(fill="x")
        self._entry(top, "evidence_id", "Evidence ID").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._combobox(top, "type", "Type", EVIDENCE_TYPES).grid(row=0, column=1, sticky="ew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        self._entry(parent, "description", "Item / Evidence Description")
        r = tk.Frame(parent, background=CLR_PANEL); r.pack(fill="x")
        self._entry(r, "source_location", "Source / Seized Location").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._entry(r, "seized_by", "Seized / Collected By").grid(row=0, column=1, sticky="ew")
        r.columnconfigure(0, weight=1); r.columnconfigure(1, weight=1)
        self._date(parent, "datetime", "Date / Time")
        self._combobox(parent, "status", "Status", EVIDENCE_STATUS)
        self._entry(parent, "hash", "Hash Value (digital evidence)")
        self._text(parent, "notes", "Examination Notes", height=3)

        # chain of custody
        coc_frame = tk.LabelFrame(parent, text="Chain of Custody Records",
                                  background=CLR_PANEL, foreground=CLR_TEXT_SUB,
                                  font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        coc_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.coc_tree = ttk.Treeview(coc_frame, columns=("date", "from", "to", "reason"),
                                     show="headings", height=5)
        self.coc_tree.heading("date", text="Date / Time")
        self.coc_tree.heading("from", text="Released By")
        self.coc_tree.heading("to", text="Received By")
        self.coc_tree.heading("reason", text="Purpose / Reason")
        self.coc_tree.column("date", width=120)
        self.coc_tree.column("from", width=140)
        self.coc_tree.column("to", width=140)
        self.coc_tree.column("reason", width=220)
        self.coc_tree.pack(side="left", fill="both", expand=True)
        bar = ttk.Scrollbar(coc_frame, orient="vertical", command=self.coc_tree.yview)
        self.coc_tree.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        btns = tk.Frame(coc_frame, background=CLR_PANEL)
        btns.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Button(btns, text="Add Record", command=self._add_coc).pack(side="left", padx=2)
        ttk.Button(btns, text="Edit", command=self._edit_coc).pack(side="left", padx=2)
        ttk.Button(btns, text="Delete", command=self._del_coc).pack(side="left", padx=2)

        self._load()
        self._refresh_coc()

    def _load(self):
        super()._load()

    def _refresh_coc(self):
        self.coc_tree.delete(*self.coc_tree.get_children())
        for i, rec in enumerate(self._custody):
            self.coc_tree.insert("", "end", iid=str(i), values=(
                rec.get("date", ""), rec.get("from", ""),
                rec.get("to", ""), rec.get("reason", "")))

    def _coc_form(self, master, title, rec):
        win = tk.Toplevel(master)
        win.title(title)
        win.configure(background=CLR_PANEL)
        win.transient(master)
        win.grab_set()
        win.resizable(False, False)
        vars = {}
        frm = tk.Frame(win, background=CLR_PANEL, padx=14, pady=12)
        frm.pack(fill="both", expand=True)
        for i, (label, key) in enumerate([("Date / Time", "date"),
                                          ("Released / From", "from"),
                                          ("Received by / To", "to"),
                                          ("Purpose / Reason", "reason")]):
            row = FieldRow(frm, label)
            vars[key] = row.var
            row.grid(row=i, column=0, sticky="ew", pady=2)
            vars[key].set(rec.get(key, ""))
        btn = tk.Frame(win, background=CLR_PANEL, pady=8)
        btn.pack(fill="x")
        res = {"ok": False}
        def ok():
            res["ok"] = True
            res["rec"] = {k: v.get().strip() for k, v in vars.items()}
            win.destroy()
        ttk.Button(btn, text="Save", style="Primary.TButton", command=ok).pack(side="right", padx=6)
        ttk.Button(btn, text="Cancel", command=win.destroy).pack(side="right")
        self.wait_window(win)
        return res

    def _add_coc(self):
        res = self._coc_form(self, "New Custody Record", {})
        if res.get("ok"):
            self._custody.append(res["rec"])
            self._refresh_coc()

    def _edit_coc(self):
        sel = self.coc_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        res = self._coc_form(self, "Edit Custody Record", self._custody[idx])
        if res.get("ok"):
            self._custody[idx] = res["rec"]
            self._refresh_coc()

    def _del_coc(self):
        sel = self.coc_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self._custody[idx]
        self._refresh_coc()

    def _validate(self, r):
        if not r["description"]:
            messagebox.showwarning("Missing information",
                                   "A description of the evidence item is required.",
                                   parent=self)
            return None
        r["custody"] = self._custody
        return r


class ExhibitDialog(EntryDialog):
    def _build(self, parent):
        self._entry(parent, "exhibit_id", "Exhibit No.")
        self._entry(parent, "description", "Description")
        self._combobox(parent, "type", "Exhibit Type", EXHIBIT_TYPES)
        self._entry(parent, "evidence_ref", "Source Evidence Ref.")
        self._date(parent, "date", "Date")
        self._entry(parent, "location", "Exhibit Location")
        self._text(parent, "notes", "Notes", height=3)
        self._load()

    def _validate(self, r):
        if not r["description"]:
            messagebox.showwarning("Missing information",
                                   "An exhibit description is required.", parent=self)
            return None
        return r


# =========================================================================== #
#  Main application
# =========================================================================== #

class ForensicApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.configure(background=CLR_BG)
        self.geometry("1180x760")
        self.minsize(980, 640)

        build_styles(self)
        self.project = self._load_autosave()

        # ID counters (persist to survive edits)
        self._counters = {"F": 0, "EV": 0, "EX": 0}
        self._sync_counters()

        self._menubar()
        self._build_ui()
        self._bind_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._autosave_debounce)

        self.refresh_all()

    # ------------------------------------------------------------------ #
    #  Persistence helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _appdata_dir():
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "ForensicReportGenerator")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def _autosave_path(self):
        return os.path.join(self._appdata_dir(), "autosave.json")

    def _load_autosave(self):
        if os.path.exists(self._autosave_path):
            try:
                with open(self._autosave_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return new_project()

    def _autosave(self):
        try:
            self._sync_project_meta()
            with open(self._autosave_path, "w", encoding="utf-8") as fh:
                json.dump(self.project, fh, indent=2)
        except Exception:
            pass
        self.after(1500, self._autosave_debounce)

    def _autosave_debounce(self):
        self.after(1500, self._autosave)

    def _sync_project_meta(self):
        self.project["meta"]["modified"] = datetime.now().isoformat()

    def _sync_counters(self):
        for item in self.project.get("findings", []):
            self._absorb_counter(item.get("finding_id", ""), "F")
        for item in self.project.get("evidence", []):
            self._absorb_counter(item.get("evidence_id", ""), "EV")
        for item in self.project.get("exhibits", []):
            self._absorb_counter(item.get("exhibit_id", ""), "EX")

    def _absorb_counter(self, fid, prefix):
        m = re.search(rf"{re.escape(prefix)}-?(\d+)", fid.upper())
        if m:
            self._counters[prefix] = max(self._counters[prefix], int(m.group(1)))

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:03d}"

    # ------------------------------------------------------------------ #
    #  Menus
    # ------------------------------------------------------------------ #
    def _menubar(self):
        mbar = tk.Menu(self, background=CLR_BG, foreground=CLR_TEXT,
                       activebackground=CLR_ACCENT, activeforeground=CLR_HEADER_TXT,
                       relief="flat", bd=0, tearoff=0)

        fm = tk.Menu(mbar, tearoff=0, background=CLR_PANEL, foreground=CLR_TEXT,
                     activebackground=CLR_ACCENT, activeforeground=CLR_HEADER_TXT)
        fm.add_command(label="New Project", accelerator="Ctrl+N", command=self._new_project)
        fm.add_command(label="Open Project...", accelerator="Ctrl+O", command=self._open_project)
        fm.add_separator()
        fm.add_command(label="Save Project As...", accelerator="Ctrl+S", command=self._save_project_as)
        fm.add_separator()
        fm.add_command(label="Exit", command=self._on_close)
        mbar.add_cascade(label="File", menu=fm)

        rm = tk.Menu(mbar, tearoff=0, background=CLR_PANEL, foreground=CLR_TEXT,
                     activebackground=CLR_ACCENT, activeforeground=CLR_HEADER_TXT)
        rm.add_command(label="Preview Report in Browser", command=lambda: self.build_report(preview=True))
        rm.add_command(label="Download HTML Report...", command=lambda: self.build_report(preview=False))
        mbar.add_cascade(label="Report", menu=rm)

        hm = tk.Menu(mbar, tearoff=0, background=CLR_PANEL, foreground=CLR_TEXT,
                     activebackground=CLR_ACCENT, activeforeground=CLR_HEADER_TXT)
        hm.add_command(label="About", command=self._about)
        mbar.add_cascade(label="Help", menu=hm)

        self.config(menu=mbar)

    def _bind_shortcuts(self):
        self.bind_all("<Control-n>", lambda e: self._new_project())
        self.bind_all("<Control-o>", lambda e: self._open_project())
        self.bind_all("<Control-s>", lambda e: self._save_project_as())
        self.bind_all("<Control-w>", lambda e: self._on_close())

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # Header bar
        head = tk.Frame(self, background=CLR_HEADER, height=58)
        head.pack(side="top", fill="x")
        head.pack_propagate(False)
        tk.Label(head, text=APP_NAME, background=CLR_HEADER,
                 foreground=CLR_HEADER_TXT, font=("Segoe UI", 15, "bold")).pack(side="left", padx=16)
        self.case_badge = tk.Label(head, text="", background=CLR_HEADER,
                                   foreground="#CBBFA6", font=("Segoe UI", 10))
        self.case_badge.pack(side="left", padx=(4, 0))

        self.stat_label = tk.Label(head, text="No project loaded",
                                   background=CLR_HEADER, foreground="#CBBFA6",
                                   font=("Segoe UI", 9))
        self.stat_label.pack(side="right", padx=16)

        # Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self._tabs = {}
        for title in HEADERS:
            frame = ttk.Frame(self.notebook, style="Panel.TFrame")
            self.notebook.add(frame, text=title)
            self._tabs[title] = frame

        self._build_case_tab(self._tabs["Case Information"])
        self._build_findings_tab(self._tabs["Findings"])
        self._build_evidence_tab(self._tabs["Evidence Log"])
        self._build_exhibit_tab(self._tabs["Exhibit Index"])
        self._build_report_tab(self._tabs["Report"])

    # -- Case Information tab ------------------------------------------ #
    def _build_case_tab(self, parent):
        wrapper = tk.Frame(parent, background=CLR_PANEL)
        wrapper.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(wrapper, text="Case Information",
                 background=CLR_PANEL, foreground=CLR_ACCENT_DK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))

        form = tk.Frame(wrapper, background=CLR_PANEL)
        form.pack(fill="both", expand=True)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        left = tk.Frame(form, background=CLR_PANEL)
        right = tk.Frame(form, background=CLR_PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right.grid(row=0, column=1, sticky="nsew")

        self.case_fields = {}
        left_rows = [
            ("case_number", "Case Number"),
            ("case_title", "Case Title / Name"),
            ("agency", "Agency / Organization"),
            ("case_type", "Case Type"),
            ("investigator", "Primary Investigator"),
            ("assistants", "Assisting Examiners"),
        ]
        r = 0
        for key, label in left_rows:
            if key == "case_type":
                row = FieldRow(left, label, kind="combobox", values=CASE_TYPES)
            else:
                row = FieldRow(left, label)
            row.pack(fill="x", pady=3)
            self.case_fields[key] = row
            r += 1
        cls_row = FieldRow(right, "Classification", kind="combobox",
                           values=["Unclassified", "Confidential", "Restricted",
                                   "Privileged", "Attorney-Client Privileged"])
        self.case_fields["classification"] = cls_row
        cls_row.pack(fill="x", pady=3)
        date_op = DateRow(right, "Date Opened")
        date_op.pack(fill="x", pady=3)
        self.case_fields["date_opened"] = date_op
        date_cl = DateRow(right, "Date Closed")
        date_cl.pack(fill="x", pady=3)
        self.case_fields["date_closed"] = date_cl
        st_row = FieldRow(right, "Status", kind="combobox",
                          values=["Active", "Pending", "Complete", "On Hold", "Closed"])
        st_row.pack(fill="x", pady=3)
        self.case_fields["status"] = st_row
        jrow = FieldRow(right, "Jurisdiction / Court")
        jrow.pack(fill="x", pady=3)
        self.case_fields["jurisdiction"] = jrow

        s = ScrollableText(wrapper, "Executive Summary", height=5)
        s.pack(fill="x", pady=(10, 2))
        self.case_fields["summary"] = s

        d = ScrollableText(wrapper, "Case Description", height=7)
        d.pack(fill="x", pady=(2, 2))
        self.case_fields["description"] = d

        ttk.Button(wrapper, text="Apply Case Details", style="Primary.TButton",
                   command=self._apply_case).pack(anchor="e", pady=(8, 0))

    # -- Findings tab --------------------------------------------------- #
    def _build_findings_tab(self, parent):
        self._findings_tree, self._findings_toolbar = self._build_list_table(
            parent,
            columns=("ID", "Title", "Category", "Severity", "Date", "Status"),
            widths=(90, 240, 170, 110, 100, 130))
        self._wire_toolbar(self._findings_toolbar, "Findings",
                           self._add_finding, self._edit_finding,
                           self._delete_finding)
        for tag, color in [("critical", "#9B2D20"), ("high", "#B04A2F"),
                           ("medium", "#9A7B22"), ("low", "#4F7A4A"),
                           ("information", "#33608A")]:
            self._findings_tree.tag_configure(tag, foreground=color)
        self._findings_tree.bind("<Double-1>", lambda e: self._edit_finding())

    def _build_evidence_tab(self, parent):
        self._evidence_tree, self._evidence_toolbar = self._build_list_table(
            parent,
            columns=("ID", "Description", "Type", "Collected By", "Date/Time", "Status"),
            widths=(90, 250, 160, 150, 130, 120))
        self._wire_toolbar(self._evidence_toolbar, "Evidence",
                           self._add_evidence, self._edit_evidence,
                           self._delete_evidence)
        self._evidence_tree.bind("<Double-1>", lambda e: self._edit_evidence())

    def _build_exhibit_tab(self, parent):
        self._exhibit_tree, self._exhibit_toolbar = self._build_list_table(
            parent,
            columns=("Exhibit", "Description", "Type", "Evidence Ref", "Date", "Location"),
            widths=(90, 260, 150, 120, 100, 160))
        self._wire_toolbar(self._exhibit_toolbar, "Exhibit",
                           self._add_exhibit, self._edit_exhibit,
                           self._delete_exhibit)
        self._exhibit_tree.bind("<Double-1>", lambda e: self._edit_exhibit())

    @staticmethod
    def _build_list_table(parent, columns, widths):
        """Create a unified table+toolbar panel. Returns (treeview, toolbar)."""
        panel = tk.Frame(parent, background=CLR_PANEL)
        panel.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(panel, columns=columns, show="headings")
        for col, w in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(panel, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(panel, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        vsb.grid(row=0, column=1, sticky="ns", pady=(0, 6))
        hsb.grid(row=1, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        bar = tk.Frame(panel, background=CLR_PANEL)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        return tree, bar

    # -- Report tab ----------------------------------------------------- #
    def _build_report_tab(self, parent):
        panel = tk.Frame(parent, background=CLR_PANEL)
        panel.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(panel, background=CLR_PANEL)
        left.pack(side="left", fill="y", padx=(0, 12), pady=4)
        right = tk.Frame(panel, background=CLR_PANEL)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="Report Options",
                 background=CLR_PANEL, foreground=CLR_ACCENT_DK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        self.rep_fields = {}
        opts = [
            ("rep_title", "Report Title", "Forensic Examination Report"),
            ("rep_agency_title", "Agency / Authority Line", ""),
            ("rep_prepared_for", "Prepared For", ""),
            ("rep_header_text", "Header Text (top of report)", ""),
            ("rep_author", "Prepared By (printed name)", ""),
        ]
        for key, label, default in opts:
            row = FieldRow(left, label)
            row.value = default
            row.pack(fill="x", pady=3)
            self.rep_fields[key] = row

        tk.Label(left, text="Sections to Include",
                 background=CLR_PANEL, foreground=CLR_ACCENT_DK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 4))
        self.include_vars = {}
        for key, label in [("cover", "Executive / Cover Summary"),
                           ("case", "Case Information"),
                           ("findings", "Findings"),
                           ("evidence", "Evidence Log (Chain of Custody)"),
                           ("exhibits", "Exhibit Index"),
                           ("sign", "Certification / Signature Block")]:
            var = tk.BooleanVar(value=True)
            tk.Checkbutton(left, text=label, variable=var, background=CLR_PANEL,
                           foreground=CLR_TEXT, activebackground=CLR_PANEL,
                           selectcolor=CLR_ENTRY, anchor="w").pack(fill="x")
            self.include_vars[key] = var

        ttk.Button(left, text="Download HTML Report",
                   style="Primary.TButton",
                   command=lambda: self.build_report(preview=False)).pack(
            fill="x", pady=(12, 6))
        ttk.Button(left, text="Preview in Browser",
                   command=lambda: self.build_report(preview=True)).pack(fill="x", pady=(0, 6))
        ttk.Button(left, text="Refresh Case Data",
                   command=self.refresh_all).pack(fill="x")

        tk.Label(right, text="Report Preview",
                 background=CLR_PANEL, foreground=CLR_ACCENT_DK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))
        txt = tk.Frame(right, background=CLR_PANEL)
        txt.pack(fill="both", expand=True)
        self.rep_preview = tk.Text(txt, wrap=tk.NONE, background=CLR_ENTRY,
                                   foreground=CLR_TEXT, insertbackground=CLR_TEXT,
                                   relief="flat", highlightthickness=1,
                                   highlightbackground=CLR_BORDER,
                                   font=("Consolas", 9))
        self.rep_preview.pack(side="left", fill="both", expand=True)
        sp_scroll = ttk.Scrollbar(txt, command=self.rep_preview.yview)
        sp_scroll.pack(side="right", fill="y")
        self.rep_preview.configure(yscrollcommand=sp_scroll.set)
        hs_scroll = ttk.Scrollbar(txt, orient="horizontal",
                                  command=self.rep_preview.xview)
        hs_scroll.pack(side="bottom", fill="x")
        self.rep_preview.configure(xscrollcommand=hs_scroll.set)
        tk.Label(right, text="HTML source preview — the downloaded report is "
                             "fully print-ready.",
                 background=CLR_PANEL, foreground=CLR_TEXT_SUB,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------------ #
    #  Toolbar wiring
    # ------------------------------------------------------------------ #
    def _wire_toolbar(self, bar, noun, add, edit, delete):
        tk.Label(bar, text=f"{noun} Records:", background=CLR_PANEL,
                 foreground=CLR_TEXT_SUB, font=("Segoe UI", 9, "bold")
                 ).pack(side="left", padx=(4, 10))
        ttk.Button(bar, text="Add", style="Tool.TButton", command=add
                   ).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Edit", style="Tool.TButton", command=edit
                   ).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Delete", style="Tool.TButton", command=delete
                   ).pack(side="left")

    # ------------------------------------------------------------------ #
    #  Refresh methods
    # ------------------------------------------------------------------ #
    def refresh_all(self):
        self._load_case_fields()
        self._refresh_findings()
        self._refresh_evidence()
        self._refresh_exhibits()
        self._refresh_stats()

    def _load_case_fields(self):
        case = self.project.get("case", {})
        for key, ctrl in self.case_fields.items():
            ctrl.value = case.get(key, "") if not isinstance(ctrl, ScrollableText) else ""
        for key, ctrl in self.case_fields.items():
            if isinstance(ctrl, ScrollableText):
                ctrl.set(case.get(key, ""))

    def _apply_case(self):
        case = self.project.setdefault("case", {})
        for key, ctrl in self.case_fields.items():
            case[key] = ctrl.get() if isinstance(ctrl, ScrollableText) else ctrl.value
        self.project["case"] = {**MINIMAL_CASE, **case}
        self._refresh_stats()

    def _refresh_stats(self):
        case = self.project.get("case", {})
        num = case.get("case_number", "").strip()
        title = case.get("case_title", "").strip()
        badge = f"  |  {num} — {title}" if num or title else ""
        self.case_badge.configure(text=badge)
        counts = (f"{len(self.project.get('findings', []))} findings   ·   "
                  f"{len(self.project.get('evidence', []))} evidence items   ·   "
                  f"{len(self.project.get('exhibits', []))} exhibits")
        self.stat_label.configure(text=counts)

    def _refresh_findings(self):
        t = self._findings_tree
        t.delete(*t.get_children())
        for f in self.project.get("findings", []):
            sev_key = [s[1] for s in SEVERITIES if s[0] == f.get("severity")]
            tag = sev_key[0] if sev_key else "information"
            t.insert("", "end", values=(
                f.get("finding_id"), f.get("title"), f.get("category"),
                f.get("severity"), f.get("date"), f.get("status")), tags=(tag,))
        self._refresh_stats()

    def _refresh_evidence(self):
        t = self._evidence_tree
        t.delete(*t.get_children())
        for e in self.project.get("evidence", []):
            t.insert("", "end", values=(
                e.get("evidence_id"), e.get("description"), e.get("type"),
                e.get("seized_by"), e.get("datetime"), e.get("status")))
        self._refresh_stats()

    def _refresh_exhibits(self):
        t = self._exhibit_tree
        t.delete(*t.get_children())
        for x in self.project.get("exhibits", []):
            t.insert("", "end", values=(
                x.get("exhibit_id"), x.get("description"), x.get("type"),
                x.get("evidence_ref"), x.get("date"), x.get("location")))
        self._refresh_stats()

    # ------------------------------------------------------------------ #
    #  Findings actions
    # ------------------------------------------------------------------ #
    def _add_finding(self):
        rec = dict(MINIMAL_FINDING)
        rec["finding_id"] = self._next_id("F")
        dlg = FindingDialog(self, "Add Finding", rec)
        if dlg.result:
            self.project.setdefault("findings", []).append(dlg.result)
            self._refresh_findings()

    def _edit_finding(self):
        sel = self._findings_tree.selection()
        if not sel:
            self._no_selection("finding")
            return
        idx = int(sel[0])
        findings = self.project.setdefault("findings", [])
        dlg = FindingDialog(self, "Edit Finding", findings[idx])
        if dlg.result:
            findings[idx] = dlg.result
            self._refresh_findings()

    def _delete_finding(self):
        sel = self._findings_tree.selection()
        if not sel:
            self._no_selection("finding")
            return
        if messagebox.askyesno("Delete Finding",
                               "Delete the selected finding(s)?"):
            for iid in reversed(sel):
                del self.project["findings"][int(iid)]
            self._refresh_findings()

    # ------------------------------------------------------------------ #
    #  Evidence actions
    # ------------------------------------------------------------------ #
    def _add_evidence(self):
        used = [e.get("evidence_id") for e in self.project.get("evidence", [])]
        rec = dict(MINIMAL_EVIDENCE)
        rec["evidence_id"] = self._next_id("EV")
        rec["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        dlg = EvidenceDialog(self, rec, used_ids=used)
        if dlg.result:
            self.project.setdefault("evidence", []).append(dlg.result)
            self._refresh_evidence()

    def _edit_evidence(self):
        sel = self._evidence_tree.selection()
        if not sel:
            self._no_selection("evidence item")
            return
        idx = int(sel[0])
        evidence = self.project.setdefault("evidence", [])
        used = [e.get("evidence_id") for i, e in enumerate(evidence) if i != idx]
        dlg = EvidenceDialog(self, evidence[idx], used_ids=used)
        if dlg.result:
            evidence[idx] = dlg.result
            self._refresh_evidence()

    def _delete_evidence(self):
        sel = self._evidence_tree.selection()
        if not sel:
            self._no_selection("evidence item")
            return
        if messagebox.askyesno("Delete Evidence",
                               "Delete the selected evidence item(s)?"):
            refs = [self.project["evidence"][int(i)].get("evidence_id")
                    for i in sel]
            self.project["exhibits"] = [
                x for x in self.project.get("exhibits", [])
                if x.get("evidence_ref") not in refs]
            self.project["findings"] = [
                f for f in self.project.get("findings", [])
                if f.get("location") not in refs]
            for iid in reversed(sel):
                del self.project["evidence"][int(iid)]
            self._refresh_evidence()
            self._refresh_exhibits()

    # ------------------------------------------------------------------ #
    #  Exhibit actions
    # ------------------------------------------------------------------ #
    def _add_exhibit(self):
        rec = dict(MINIMAL_EXHIBIT)
        rec["exhibit_id"] = self._next_id("EX")
        dlg = ExhibitDialog(self, "Add Exhibit", rec)
        if dlg.result:
            self.project.setdefault("exhibits", []).append(dlg.result)
            self._refresh_exhibits()

    def _edit_exhibit(self):
        sel = self._exhibit_tree.selection()
        if not sel:
            self._no_selection("exhibit")
            return
        idx = int(sel[0])
        exhibits = self.project.setdefault("exhibits", [])
        dlg = ExhibitDialog(self, "Edit Exhibit", exhibits[idx])
        if dlg.result:
            exhibits[idx] = dlg.result
            self._refresh_exhibits()

    def _delete_exhibit(self):
        sel = self._exhibit_tree.selection()
        if not sel:
            self._no_selection("exhibit")
            return
        if messagebox.askyesno("Delete Exhibit",
                               "Delete the selected exhibit(s)?"):
            for iid in reversed(sel):
                del self.project["exhibits"][int(iid)]
            self._refresh_exhibits()

    def _no_selection(self, noun):
        messagebox.showinfo("No selection",
                            f"Select a {noun} from the table first.")

    # ------------------------------------------------------------------ #
    #  Project management
    # ------------------------------------------------------------------ #
    def _new_project(self):
        self.project = new_project()
        self._counters = {"F": 0, "EV": 0, "EX": 0}
        self.refresh_all()

    def _ask_path(self, save=True):
        if save:
            return filedialog.asksaveasfilename(
                title="Save Forensic Report Project",
                defaultextension=".frc",
                filetypes=[("Forensic Report Case", "*.frc"),
                           ("JSON document", "*.json")],
                initialfile="forensic_case.frc")
        return filedialog.askopenfilename(
            title="Open Forensic Report Project",
            filetypes=[("Forensic Report Case", "*.frc"),
                       ("JSON document", "*.json"),
                       ("All files", "*.*")])

    def _save_project_as(self):
        path = self._ask_path(save=True)
        if not path:
            return
        self._sync_project_meta()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.project, fh, indent=2, ensure_ascii=False)
        self.stat_label.configure(text=f"Saved: {os.path.basename(path)}")

    def _open_project(self):
        path = self._ask_path(save=False)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.project = self._coerce_project(data)
            self._sync_counters()
            self.refresh_all()
            self.stat_label.configure(text=f"Opened: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Open Project",
                                 f"Could not open project:\n{exc}")

    @staticmethod
    def _coerce_project(data):
        if not isinstance(data, dict):
            raise ValueError("Not a valid project file.")
        p = new_project()
        p["meta"] = data.get("meta", p["meta"])
        p["case"] = {**MINIMAL_CASE, **data.get("case", {})}
        clean_list(p["findings"], data, "findings", MINIMAL_FINDING)
        clean_list(p["evidence"], data, "evidence", MINIMAL_EVIDENCE)
        clean_list(p["exhibits"], data, "exhibits", MINIMAL_EXHIBIT)
        return p

    def _on_close(self):
        self._sync_project_meta()
        self._autosave()
        self.destroy()

    def _about(self):
        messagebox.showinfo(
            APP_NAME,
            f"{APP_NAME}  v{APP_VERSION}\n\n"
            "A desktop tool for building professional forensic investigation "
            "reports.\n\n"
            "Sections: Case Information · Findings · Evidence Log "
            "(with chain of custody) · Exhibit Index.\n"
            "Reports are exported as print-ready HTML.\n\n"
            "Projects are autosaved to your user profile. Use File ▶ Open "
            "to load a saved case.")

    # ------------------------------------------------------------------ #
    #  Report generation
    # ------------------------------------------------------------------ #
    def _collect_report_data(self):
        self._apply_case()
        case = self.project["case"]
        data = {
            "case": case,
            "findings": self.project["findings"],
            "evidence": self.project["evidence"],
            "exhibits": self.project["exhibits"],
            "created": datetime.now().strftime("%A, %d %B %Y at %H:%M"),
        }
        for key, ctrl in self.rep_fields.items():
            data[key] = ctrl.value
        return data

    def build_report(self, preview=True):
        data = self._collect_report_data()
        html = generate_html_report(data, self.include_vars)
        if preview:
            path = os.path.join(self._appdata_dir(), "preview_report.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            webbrowser.open("file:///" + path.replace("\\", "/"))
            return
        path = filedialog.asksaveasfilename(
            title="Download Forensic Report (HTML)",
            defaultextension=".html",
            filetypes=[("HTML document", "*.html"), ("All files", "*.*")],
            initialfile="forensic_report.html")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        self.stat_label.configure(text=f"Report saved: {os.path.basename(path)}")
        if messagebox.askyesno("Report Saved",
                               "Report saved successfully.\n\nOpen it now in "
                               "your browser?"):
            webbrowser.open("file:///" + path.replace("\\", "/"))


# =========================================================================== #
#  HTML report builder
# =========================================================================== #

def esc(value):
    return (value or "").replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


def forn(value, empty="-"):
    v = (value or "").strip()
    return esc(v) if v else empty


def clean_list(target, source, key, template):
    for raw in source.get(key, []) or []:
        if isinstance(raw, dict):
            target.append({**template, **{
                k: (raw.get(k) or template.get(k)) for k in template}})


def generate_html_report(data, include_vars):
    """Build a professional, print-ready HTML forensic report."""
    case = data["case"]
    findings = data.get("findings", [])
    evidence = data.get("evidence", [])
    exhibits = data.get("exhibits", [])

    now = datetime.now()
    use = {k: (not include_vars or bool(v.get())) for k, v in
           (include_vars or {}).items()}

    heading = [f"<span>Case {esc(case.get('case_number'))}</span>"
               if case.get("case_number") else ""]
    title = esc(data.get("rep_title") or "Forensic Examination Report")

    # ---------------- Case info table ---------------- #
    info_rows = [
        ("Case Number", case.get("case_number")),
        ("Case Title", case.get("case_title")),
        ("Agency / Organization", case.get("agency")),
        ("Case Type", case.get("case_type")),
        ("Primary Investigator", case.get("investigator")),
        ("Assisting Examiners", case.get("assistants")),
        ("Date Opened", case.get("date_opened")),
        ("Date Closed", case.get("date_closed")),
        ("Jurisdiction / Court", case.get("jurisdiction")),
        ("Classification", case.get("classification")),
        ("Status", case.get("status")),
    ]
    info_sec = ("<h2>1. Case Information</h2>"
                "<table class=\"kv\">" +
                "".join(f"<tr><th>{esc(k)}</th><td>{forn(v)}</td></tr>"
                        for k, v in info_rows if (v or "").strip()) +
                "</table>" +
                summary_block(case))

    # ---------------- Findings ---------------- #
    if findings:
        body_rows = "".join("""
        <tr><td>{id}</td><td class="sev sev-{cls}">{sev}</td><td>{title}</td>
        <td>{cat}</td><td>{dt}</td><td>{st}</td></tr>""".format(
            id=forn(f.get("finding_id")),
            cls=sev_class(f.get("severity")),
            sev=forn(f.get("severity")),
            title=forn(f.get("title")),
            cat=forn(f.get("category")),
            dt=forn(f.get("date")),
            st=forn(f.get("status"))).strip() for f in findings)
        findings_sec = (f"<h2>3. Findings</h2>"
                        f"<p class=\"count\">{len(findings)} finding(s) recorded.</p>"
                        "<table class=\"data\"><thead><tr>"
                        "<th>ID</th><th>Severity</th><th>Title</th>"
                        "<th>Category</th><th>Date</th><th>Status</th>"
                        "</tr></thead><tbody>" + body_rows + "</tbody></table>")
        details = []
        for i, f in enumerate(findings, 1):
            det = f"<h3>{i}. {forn(f.get('finding_id'))} — {forn(f.get('title'))}</h3>"
            if f.get("severity"):
                det += (f"<p class=\"tag\"><span class=\"sev sev-{sev_class(f.get('severity'))}\">"
                        f"{esc(f.get('severity'))}</span>"
                        f" · {esc(f.get('status'))}{' · ' + esc(f.get('date')) if f.get('date') else ''} "
                        f"· {esc(f.get('category')) if f.get('category') else 'General'}</p>")
            if f.get("description"):
                det += f"<p><b>Description:</b> {paragraph(f.get('description'))}</p>"
            if f.get("location"):
                det += f"<p><b>Relevant evidence / location:</b> {esc(f.get('location'))}</p>"
            if f.get("recommendation"):
                det += f"<p><b>Recommendation:</b> {paragraph(f.get('recommendation'))}</p>"
            details.append(det)
        findings_sec += f"<h3 style=\"margin-top:1.2em\">Finding Details</h3>\n" + "\n".join(details)
    else:
        findings_sec = ("<h2>3. Findings</h2>"
                        "<p><em>No findings recorded for this case.</em></p>")

    # ---------------- Evidence log ---------------- #
    if evidence:
        ev_rows = "".join("""
        <tr><td>{id}</td><td>{desc}</td><td>{typ}</td><td>{by}</td>
        <td>{dt}</td><td>{st}</td></tr>""".format(
            id=forn(e.get("evidence_id")),
            desc=forn(e.get("description")),
            typ=forn(e.get("type")),
            by=forn(e.get("seized_by")),
            dt=forn(e.get("datetime")),
            st=forn(e.get("status"))).strip() for e in evidence)
        evidence_sec = (f"<h2>4. Evidence Log</h2>"
                        f"<p class=\"count\">{len(evidence)} item(s) logged.</p>"
                        "<table class=\"data\"><thead><tr>"
                        "<th>Evidence ID</th><th>Item / Description</th><th>Type</th>"
                        "<th>Seized By</th><th>Date/Time</th><th>Status</th>"
                        "</tr></thead><tbody>" + ev_rows + "</tbody></table>")
        ev_details = []
        for e in evidence:
            det = f"<h3>Evidence {forn(e.get('evidence_id'))} — {forn(e.get('description'))}</h3>"
            det += ("<table class=\"kv nocol\">"
                    f"<tr><th>Type</th><td>{forn(e.get('type'))}</td></tr>"
                    f"<tr><th>Source / Seized location</th><td>{forn(e.get('source_location'))}</td></tr>"
                    f"<tr><th>Seized / collected by</th><td>{forn(e.get('seized_by'))}</td></tr>"
                    f"<tr><th>Date / time</th><td>{forn(e.get('datetime'))}</td></tr>"
                    f"<tr><th>Status</th><td>{forn(e.get('status'))}</td></tr>"
                    f"<tr><th>Hash value</th><td class=\"mono\">{forn(e.get('hash'))}</td></tr>"
                    f"<tr><th>Notes</th><td>{paragraph(e.get('notes'))}</td></tr>"
                    "</table>")
            coc = e.get("custody") or []
            if coc:
                coc_rows = "".join("""
                <tr><td>{d}</td><td>{f}</td><td>{t}</td><td>{r}</td></tr>""".format(
                    d=forn(c.get("date")), f=forn(c.get("from")),
                    t=forn(c.get("to")), r=forn(c.get("reason"))).strip() for c in coc)
                det += ("<p><b>Chain of Custody:</b></p>"
                        "<table class=\"data coc\"><thead><tr>"
                        "<th>Date / Time</th><th>Released By</th><th>Received By</th>"
                        "<th>Purpose / Reason</th></tr></thead><tbody>"
                        + coc_rows + "</tbody></table>")
            ev_details.append(det)
        evidence_sec += "\n".join(ev_details)
    else:
        evidence_sec = ("<h2>4. Evidence Log</h2>"
                        "<p><em>No evidence items logged.</em></p>")

    # ---------------- Exhibit index ---------------- #
    if exhibits:
        ex_rows = "".join("""
        <tr><td>{id}</td><td>{desc}</td><td>{typ}</td><td>{ref}</td>
        <td>{dt}</td><td>{loc}</td></tr>""".format(
            id=forn(x.get("exhibit_id")),
            desc=forn(x.get("description")),
            typ=forn(x.get("type")),
            ref=forn(x.get("evidence_ref")),
            dt=forn(x.get("date")),
            loc=forn(x.get("location"))).strip() for x in exhibits)
        exhibit_sec = (f"<h2>5. Exhibit Index</h2>"
                       f"<p class=\"count\">{len(exhibits)} exhibit(s) indexed.</p>"
                       "<table class=\"data\"><thead><tr>"
                       "<th>Exhibit No.</th><th>Description</th><th>Type</th>"
                       "<th>Evidence Ref.</th><th>Date</th><th>Location</th>"
                       "</tr></thead><tbody>" + ex_rows + "</tbody></table>")
    else:
        exhibit_sec = ("<h2>5. Exhibit Index</h2>"
                       "<p><em>No exhibits indexed.</em></p>")

    # ---------------- Signature / certification ---------------- #
    author = (data.get("rep_author") or case.get("investigator") or
              "______________________")
    sign_sec = f"""
    <div class="sign">
      <h2>Certification</h2>
      <p>I, the undersigned, declare that, to the best of my knowledge, the
      information and exhibits recorded in this report accurately reflect the
      examination and analysis performed, and that all findings, evidence
      handling and custody transfers were documented in accordance with
      established forensic procedures.</p>
      <table style="width:100%; border:none; margin-top:2.4em;">
        <tr>
          <td style="border:none; width:50%; padding-right:1em;">
            <p style="border-top:1px solid #555; padding-top:4px; margin:0;">
            <b>{esc(author)}</b><br>
            <span style="color:#666; font-size:.85em">Lead Examiner / Investigator</span></p>
          </td>
          <td style="border:none; width:50%; padding-left:1em;">
            <p style="border-top:1px solid #555; padding-top:4px; margin:0;">
            Date: ______________________</p>
          </td>
        </tr>
      </table>
      <p style="margin-top:2.4em; font-size:.85em; color:#666;">Certified on
      {esc(now.strftime("%d %B %Y"))}.</p>
    </div>
    """

    # ---------------- Assemble ---------------- #
    body = ""
    if use.get("case", True):
        body += info_sec
    if use.get("findings", True):
        body += findings_sec
    if use.get("evidence", True):
        body += evidence_sec
    if use.get("exhibits", True):
        body += exhibit_sec
    if use.get("sign", True):
        body += sign_sec

    header_line = data.get("rep_header_text") or ""
    agency_line = data.get("rep_agency_title") or case.get("agency") or ""
    prepared_for = data.get("rep_prepared_for") or case.get("jurisdiction") or ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<style>
  @page {{ size: A4 landscape; margin: 18mm 14mm 16mm 14mm; }}
  html {{ background: #EFEAE0; }}
  body {{
    font-family: 'Segoe UI', 'Calibri', 'Helvetica Neue', Arial, sans-serif;
    color: #2F2A22; background: #FDFBF6; max-width: 1200px; margin: 0 auto;
    padding: 28px 40px 40px; line-height: 1.45; font-size: 12px;
  }}
  header {{ border-bottom: 3px solid #5F7169; padding-bottom: 10px; margin-bottom: 18px; }}
  header .agency {{ color: #5F7169; font-size: 15px; font-weight: 700; letter-spacing: .02em; }}
  header h1 {{ margin: 6px 0 2px; font-size: 26px; color: #333; }}
  header .meta {{ color: #6E6658; font-size: 11px; }}
  h2 {{ color: #4A5B54; font-size: 17px; border-bottom: 1px solid #C9BFAA;
       padding-bottom: 4px; margin: 26px 0 10px; }}
  h3 {{ color: #333; font-size: 13.5px; margin: 18px 0 6px; }}
  p {{ margin: 6px 0; }}
  p.count {{ color: #6E6658; font-style: italic; margin-bottom: 8px; }}
  table.kv {{ border-collapse: collapse; width: 100%; margin: 4px 0 10px; background:#FAF6EC; }}
  table.kv th, table.kv td {{ border: 1px solid #C9BFAA; padding: 5px 9px; vertical-align: top; text-align: left; }}
  table.kv th {{ background: #E5DECC; color: #2F2A22; width: 240px; font-weight: 600; }}
  table.data {{ border-collapse: collapse; width: 100%; margin: 6px 0 12px; background: #FAF6EC; }}
  table.data th, table.data td {{ border: 1px solid #B8AE97; padding: 6px 9px; text-align: left; }}
  table.data thead th {{ background: #D8D0BD; color: #2F2A22; font-weight: 700; }}
  table.data tbody tr:nth-child(even) {{ background: #F1EBDE; }}
  table.data tbody tr:hover {{ background: #E7E0CD; }}
  table.coc {{ margin-top: 4px; }}
  .mono {{ font-family: Consolas, Menlo, monospace; font-size: 11px; }}
  .tag {{ margin-bottom: 6px; }}
  .sev {{ display: inline-block; padding: 1px 8px; border-radius: 3px; font-weight: 700; color: #fff; font-size: 10.5px; }}
  .sev-critical {{ background:#9B2D20; }} .sev-high {{ background:#B04A2F; }}
  .sev-medium {{ background:#9A7B22; }} .sev-low {{ background:#4F7A4A; }}
  .sev-information {{ background:#33608A; }}
  td.sev {{ padding: 4px 6px; }}
  div.sign {{ margin-top: 26px; border-top: 2px solid #5F7169; padding-top: 14px; }}
  footer {{ margin-top: 30px; padding-top: 8px; border-top: 1px solid #C9BFAA;
           font-size: 10px; color: #8A8272; text-align: center; }}
  .watermark {{ position: relative; }}
  @media print {{
    html {{ background: #ffffff; }}
    body {{ max-width: none; padding: 0; }}
    .page-break {{ page-break-before: always; }}
  }}
</style>
</head>
<body>
<header>
  <div class="agency">{esc(agency_line)}</div>
  <h1>{esc(title)}</h1>
  <div class="meta">
    Case: <b>{forn(case.get('case_number'))}</b> · {esc(case.get('case_title')) if case.get('case_title') else ''}
    &nbsp;&nbsp;|&nbsp;&nbsp;Generated {esc(data.get('created'))}
    &nbsp;&nbsp;|&nbsp;&nbsp;Classification: {forn(case.get('classification'))}
  </div>
  {('<div class="meta">' + esc(header_line) + '</div>') if header_line else ''}
  {('<div class="meta">Prepared for: ' + esc(prepared_for) + '</div>') if prepared_for else ''}
</header>

{body}

<footer>
  This document was generated by {esc(APP_NAME)} v{esc(data.get('version', APP_VERSION))}.
  It is a working exhibit and is subject to verification. Confidential —
  for authorized use only. Page footer continues.
</footer>
</body>
</html>
"""
    return html


def sev_class(sev):
    sev = (sev or "").lower()
    for name, key in [("critical", "critical"), ("high", "high"),
                      ("medium", "medium"), ("low", "low"),
                      ("info", "information")]:
        if name in sev:
            return key
    return "information"


def paragraph(value):
    value = (value or "").strip()
    if not value:
        return "<span class=\"mono\">-</span>"
    return "<br>".join(esc(line) for line in value.splitlines())


def summary_block(case):
    """Render executive summary + case description as paragraphs."""
    blocks = []
    if (case.get("summary") or "").strip():
        blocks.append("<p><b>Executive Summary:</b><br>" +
                      paragraph(case.get("summary")) + "</p>")
    if (case.get("description") or "").strip():
        blocks.append("<p><b>Case Description:</b><br>" +
                      paragraph(case.get("description")) + "</p>")
    return "\n".join(blocks)


# =========================================================================== #
#  Entry point
# =========================================================================== #

def main():
    try:
        app = ForensicApp()
        app.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()