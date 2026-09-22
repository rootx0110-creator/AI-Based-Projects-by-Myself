# -*- coding: utf-8 -*-
"""app.py - MSF Lab Module Studio (GUI).

A polished desktop toolkit to build, test and report on a custom Metasploit
module that targets a LAB-ONLY vulnerable service.

Run:          python app.py
Build exe:    powershell -ExecutionPolicy Bypass -File build_exe.ps1
"""
from __future__ import annotations

import os
import platform
import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from module_builder import (
    APP_NAME,
    APP_VERSION,
    BANNER_MARKER,
    COMMON_PORTS,
    DEFAULT_PORT,
    DEFAULT_TARGET,
    DEFAULT_URI,
    MODULE_CATEGORIES,
    PAYLOAD_CHOICES,
    VULN_TEMPLATES,
    VULN_TEMPLATES_BY_ID,
    LabHtmlReport,
    LabServiceProbe,
    MetasploitModuleGenerator,
    default_config,
    scan_tcp_ports,
)

# --------------------------------------------------------------------------
# Palette - soft aqua / teal (deliberately NOT black, NOT white)
# --------------------------------------------------------------------------
BG        = "#E7F5F3"   # app background, soft mint
BG_SIDE   = "#CBE9E8"   # sidebar
ACCENT    = "#0E8C99"   # primary teal
ACCENT_D  = "#085F73"   # deep teal (text)
ACCENT_L  = "#B8E6E8"   # light teal
CARD      = "#FDFFFF"   # card surface
MINT      = "#EFFAF8"   # tinted field bg
INK       = "#164A56"   # main ink
MUTED     = "#5B7F88"
WARN      = "#E8734A"
GOOD      = "#1A8A4F"
GRAD_TOP  = "#16C9A0"
GRAD_MID  = "#0E8C99"
GRAD_BOT  = "#085F73"
CODE_BG   = "#0D2730"   # dark-teal code area (editor-style, not app background)
CODE_FG   = "#B7E6E3"
CODE_ACC  = "#6FE3C9"

FONT_UI   = "Segoe UI"
FONT_SZ   = 10
FONT_CODE = "Consolas"

SECTION_ICONS = {
    "setup":  "1  Setup",
    "builder":"2  Builder",
    "test":   "3  Live Test",
    "report": "4  Report",
}


def hex2rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def mix(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex2rgb(c1)
    r2, g2, b2 = hex2rgb(c2)
    return "#%02x%02x%02x" % (lerp(r1, r2, t), lerp(g1, g2, t), lerp(b1, b2, t))


# --------------------------------------------------------------------------
# Error logging (always available, essential for a --windowed exe)
# --------------------------------------------------------------------------
def _error_log_path() -> str:
    return os.path.join(tempfile.gettempdir(), "msf_lab_studio_error.log")


def _write_error(kind: str, exc_info) -> None:
    try:
        with open(_error_log_path(), "a", encoding="utf-8") as fh:
            fh.write("%s [%s]\n%s\n%s\n" % (
                time.strftime("%Y-%m-%d %H:%M:%S"), kind,
                "-" * 50, "".join(traceback.format_exception(*exc_info))))
    except Exception:
        pass


# --------------------------------------------------------------------------
# Widget helpers
# --------------------------------------------------------------------------
def label(parent, text, **kw):
    kw.setdefault("bg", parent.cget("bg"))
    kw.setdefault("fg", INK)
    kw.setdefault("font", (FONT_UI, FONT_SZ))
    return tk.Label(parent, text=text, **kw)


def entry(parent, width=28, **kw):
    e = tk.Entry(
        parent,
        width=width,
        relief="flat",
        bg=MINT,
        fg=INK,
        insertbackground=ACCENT_D,
        highlightthickness=1,
        highlightbackground=ACCENT_L,
        highlightcolor=ACCENT,
        font=(FONT_UI, FONT_SZ),
        **kw,
    )
    return e


def combo(parent, values, width=30, **kw):
    c = ttk.Combobox(
        parent,
        values=values,
        width=width,
        state="readonly",
        font=(FONT_UI, FONT_SZ),
        **kw,
    )
    style = ttk.Style(parent)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Accent.TCombobox",
        fieldbackground=MINT,
        background=MINT,
        foreground=INK,
        arrowcolor=ACCENT,
        bordercolor=ACCENT_L,
        lightcolor=ACCENT_L,
        darkcolor=ACCENT_L,
    )
    c.configure(style="Accent.TCombobox")
    return c


def action_button(parent, text, command, kind="primary", **kw):
    """Flat paint-style button with rounded-ish look & hover state."""
    colors = {
        "primary":  (ACCENT, "#ffffff", ACCENT_D),
        "gold":     (GOOD,    "#ffffff", "#136b3d"),
        "warn":     (WARN,    "#ffffff", "#b9532c"),
        "ghost":    (ACCENT_L, ACCENT_D, "#9fd6d8"),
    }
    bg, fg, hover = colors.get(kind, colors["primary"])
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground="#ffffff",
        bd=0,
        relief="flat",
        padx=16,
        pady=8,
        cursor="hand2",
        font=(FONT_UI, FONT_SZ, "bold"),
        takefocus=0,
        **kw,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def card(parent, title):
    """Returns a card frame with a title bar, packed into `parent`.

    Cards are packed top-to-bottom with equal vertical share inside the
    section page.
    """
    frame = tk.Frame(parent, bg=CARD, highlightbackground=ACCENT,
                     highlightthickness=1)
    tk.Frame(frame, bg=ACCENT, height=3).pack(fill="x")
    head = tk.Frame(frame, bg=CARD)
    head.pack(fill="x", padx=14, pady=(10, 2))
    tk.Label(head, text=title, bg=CARD, fg=ACCENT_D,
             font=(FONT_UI, 11, "bold")).pack(side="left")
    frame.pack(fill="both", expand=True, pady=(0, 14))
    frame._cards_default_bg = CARD
    return frame


def card_body(parent):
    body = tk.Frame(parent, bg=CARD)
    body.pack(fill="both", expand=True, padx=14, pady=(2, 14))
    return body


# --------------------------------------------------------------------------
# Gradient header
# --------------------------------------------------------------------------
class GradientHeader(tk.Canvas):
    def __init__(self, master, height=110):
        super().__init__(master, height=height, bd=0, highlightthickness=0)
        self._h = height
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        w = self.winfo_width()
        h = self._h
        if w <= 2:
            return
        self.delete("all")
        for y in range(h):
            t = y / max(1, h - 1)
            color = mix(GRAD_TOP, GRAD_MID, t)
            if t > 0.5:
                color = mix(GRAD_MID, GRAD_BOT, (t - 0.5) * 2)
            self.create_line(0, y, w, y, fill=color)
        self.create_text(
            26, 34, anchor="w", text=APP_NAME,
            fill="#ffffff", font=(FONT_UI, 23, "bold"))
        self.create_text(
            26, 64, anchor="w",
            text="Custom Metasploit module studio - build, verify, report (LAB ONLY)",
            fill="#dffff6", font=(FONT_UI, 11))
        self.create_text(
            w - 24, 34, anchor="e",
            text="v%s  |  lab-safe" % APP_VERSION,
            fill="#b8f0e4", font=(FONT_UI, 9))


# --------------------------------------------------------------------------
# Main application
# --------------------------------------------------------------------------
class LabModuleStudio:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("%s - Lab Module Studio" % APP_NAME)
        root.geometry("1180x760")
        root.minsize(1000, 640)
        root.configure(bg=BG)

        self.config = default_config()
        self.check_result = None
        self.probe = LabServiceProbe()
        self._gen = MetasploitModuleGenerator()
        self.history = []
        self.last_scan = []

        # profile persistence (%LOCALAPPDATA%\MSFLabStudio\profile.json)
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "MSFLabStudio")
        self.profile_path = os.path.join(self.profile_dir, "profile.json")
        self.remember = tk.BooleanVar(value=True)

        # thread-safe channel: worker threads only ever PUT results here;
        # a main-thread poller (idle loop) drains it. Calling self.root.*
        # from worker threads is NOT safe and crashes tkinter.
        self._work_queue = queue.Queue()
        self._poll_job = None

        self._build_layout()
        self._build_sidebar()
        self._build_setup()
        self._build_builder()
        self._build_test()
        self._build_report()
        self._build_statusbar()
        self.switch("setup")
        self.root.update_idletasks()
        self._load_profile()
        self._refresh_advisor()
        self._status("Ready. Point the lab at 127.0.0.1:%d and start exploring." % self.config["target_port"])
        self._poll()

        # keyboard navigation: Alt+1 .. Alt+4
        for i, key in enumerate(SECTION_ICONS, 1):
            root.bind("<Alt-KeyPress-%d>" % i, lambda e, k=key: self.switch(k))
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ layout
    def _build_layout(self):
        self.header = GradientHeader(self.root)
        self.header.pack(fill="x", side="top")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=BG_SIDE, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True, padx=22, pady=18)

        self.sections = {}

    def _nav_button(self, key):
        btn = tk.Button(
            self.sidebar, text=SECTION_ICONS[key], anchor="w",
            font=(FONT_UI, 11, "bold"), bd=0, relief="flat",
            padx=16, pady=12, cursor="hand2", takefocus=0,
            command=lambda: self.switch(key))
        return btn

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="WORKFLOW", bg=BG_SIDE, fg=ACCENT_D,
                 font=(FONT_UI, 9, "bold")).pack(anchor="w", padx=16, pady=(18, 6))
        self.nav = {}
        for key in SECTION_ICONS:
            btn = self._nav_button(key)
            btn.pack(fill="x", padx=10, pady=3)
            self.nav[key] = btn
        tk.Label(self.sidebar, text="SAFETY", bg=BG_SIDE, fg=ACCENT_D,
                 font=(FONT_UI, 9, "bold")).pack(anchor="w", padx=16, pady=(22, 6))
        note = tk.Label(
            self.sidebar, bg=BG_SIDE, fg=ACCENT_D, justify="left",
            font=(FONT_UI, 9), wraplength=195,
            text="Authorized lab / CTF use only. This studio builds test "
                 "tooling for a deliberately vulnerable service - never "
                 "deploy against a real environment.")
        note.pack(anchor="w", padx=16, pady=4)

    # ------------------------------------------------------------------ setup
    def _build_setup(self):
        page = tk.Frame(self.content, bg=BG)
        self.sections["setup"] = page

        c = card(page, "Target & module identity")
        body = card_body(c)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Lab vulnerability template").pack(side="left")
        self.template_combo = combo(row, [t.label for t in VULN_TEMPLATES], width=52)
        self.template_combo.set(VULN_TEMPLATES_BY_ID[self._gen.template_id].label)
        self.template_combo.pack(side="left", padx=12)
        self.template_combo.bind("<<ComboboxSelected>>", self._on_template_pick)
        tk.Label(row, text="switches module class + endpoint automatically",
                 bg=CARD, fg=MUTED, font=(FONT_UI, 9)).pack(side="left", padx=6)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4+2)
        label(row, "RHOSTS / target host").pack(side="left")
        self.tgt_host = entry(row, width=26)
        self.tgt_host.insert(0, self.config["target_host"])
        self.tgt_host.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "RPORT / port").pack(side="left")
        self.tgt_port = entry(row, width=10)
        self.tgt_port.insert(0, str(self.config["target_port"]))
        self.tgt_port.pack(side="left", padx=12)
        label(row, "TARGETURI").pack(side="left", padx=(12, 0))
        self.tgt_uri = entry(row, width=16)
        self.tgt_uri.insert(0, self.config["target_uri"])
        self.tgt_uri.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Module category").pack(side="left")
        self.mod_cat = combo(row, MODULE_CATEGORIES, width=30)
        self.mod_cat.set(self.config["module_name"])
        self.mod_cat.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Friendly name").pack(side="left")
        self.cli_name = entry(row, width=34)
        self.cli_name.insert(0, self.config["cli_name"])
        self.cli_name.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Author").pack(side="left")
        self.author = entry(row, width=30)
        self.author.insert(0, self.config["author"])
        self.author.pack(side="left", padx=12)
        label(row, "Reference (CVE)").pack(side="left", padx=(12, 0))
        self.cve = entry(row, width=18)
        self.cve.insert(0, self.config["reference"])
        self.cve.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=(14, 0))
        action_button(row, "Apply configuration", self.apply_config,
                      kind="primary").pack(side="left")
        action_button(row, "Reset to defaults", self.reset_config,
                      kind="ghost").pack(side="left", padx=8)
        tk.Checkbutton(row, text="Remember settings",
                       variable=self.remember, bg=CARD, fg=INK,
                       activebackground=CARD, selectcolor=CARD,
                       font=(FONT_UI, 9), takefocus=0).pack(side="left", padx=(18, 0))

        c2 = card(page, "Lab target helper")
        body2 = card_body(c2)
        tk.Label(body2, bg=CARD, fg=MUTED, justify="left", wraplength=760,
                 font=(FONT_UI, 9),
                 text="To exercise this studio end-to-end, a LAB-ONLY vulnerable HTTP service is "
                      "included with the project (vuln_service.py). Run it on 127.0.0.1 with:\n\n"
                      "    python vuln_service.py --host 127.0.0.1 --port 8080\n\n"
                      "The lab exposes three lesson vulnerabilities that the studio detects and "
                      "builds modules for:\n"
                      "    /exec   -> OS command injection (Exploit module)\n"
                      "    /file   -> path traversal / arbitrary file read (Scanner module)\n"
                      "    /backup -> unauth config disclosure with plaintext secrets (Scanner)\n\n"
                      "Use section 3 (Live Test) to auto-detect them and port-scan the box, then "
                      "section 2 to generate the matching Metasploit module. Files architecture.md / "
                      "memory.md / state.md / todo.txt / readme.txt document the build.").pack(anchor="w", pady=4)

    # ---------------------------------------------------------------- builder
    def _build_builder(self):
        page = tk.Frame(self.content, bg=BG)
        self.sections["builder"] = page

        c = card(page, "Payload & style options")
        body = card_body(c)
        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Payload").pack(side="left")
        self.payload = combo(row, [p[0] for p in PAYLOAD_CHOICES], width=42)
        self.payload.set(PAYLOAD_CHOICES[0][0])
        self.payload.pack(side="left", padx=12, ipady=2)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        label(row, "Bad characters").pack(side="left")
        self.badchars = entry(row, width=16)
        self.badchars.insert(0, self.config["badchars"])
        self.badchars.pack(side="left", padx=12)
        label(row, "Module rank").pack(side="left", padx=(12, 0))
        self.rank = combo(row, ["ExcellentRanking", "GreatRanking", "GoodRanking", "NormalRanking"], width=18)
        self.rank.set(self.config["default_rank"])
        self.rank.pack(side="left", padx=12)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=(14, 0))
        action_button(row, "Generate Ruby module", self.generate_module,
                      kind="primary").pack(side="left")
        action_button(row, "Quick syntax check", self.quick_syntax,
                      kind="ghost").pack(side="left", padx=8)
        action_button(row, "Copy to clipboard", self.copy_module,
                      kind="gold").pack(side="left", padx=8)
        action_button(row, "Save as .rb", self.save_module_rb,
                      kind="warn").pack(side="left", padx=8)

        c2 = card(page, "Generated Metasploit module (Ruby)")
        body2 = card_body(c2)
        self.code = tk.Text(
            body2, wrap="none", bg=CODE_BG, fg=CODE_FG,
            insertbackground=CODE_ACC, relief="flat",
            font=(FONT_CODE, 10), padx=12, pady=10,
            highlightthickness=1, highlightbackground=ACCENT_L,
            state="disabled")
        self.code.pack(fill="both", expand=True)
        sby = tk.Scrollbar(body2, orient="vertical", command=self.code.yview)
        sby.pack(side="right", fill="y")
        sbx = tk.Scrollbar(body2, orient="horizontal", command=self.code.xview)
        sbx.pack(side="bottom", fill="x")
        self.code.configure(yscrollcommand=sby.set, xscrollcommand=sbx.set)

    # ------------------------------------------------------------------- test
    def _build_test(self):
        page = tk.Frame(self.content, bg=BG)
        self.sections["test"] = page

        c_adv = card(page, "Smart advisor")
        body_adv = card_body(c_adv)
        tk.Label(body_adv, bg=CARD, fg=MUTED, font=(FONT_UI, 9),
                 text="Context-aware recommendation based on your target, "
                      "detection results and latest check verdict:").pack(anchor="w")
        self.advisor = tk.Label(body_adv, text="  Ready.", anchor="w",
                                bg=CARD, fg=ACCENT_D,
                                font=(FONT_UI, 10, "bold"))
        self.advisor.pack(fill="x", pady=(4, 2))

        c = card(page, "Live lab verification")
        body = card_body(c)
        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=4)
        action_button(row, "Probe target (/health)", self.run_probe,
                      kind="primary").pack(side="left")
        action_button(row, "Simulate Metasploit `check`", self.run_check,
                      kind="gold").pack(side="left", padx=8)
        action_button(row, "Verify selected endpoint", self.verify_exec,
                      kind="ghost").pack(side="left", padx=8)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=(10, 4))
        action_button(row, "Detect all lab vulns", self.run_detect_all,
                      kind="gold").pack(side="left")
        action_button(row, "TCP port scan (common ports)", self.run_port_scan,
                      kind="ghost").pack(side="left", padx=8)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=(14, 6))
        label(row, "Result").pack(anchor="w")
        self.badge = tk.Label(body, text="Not tested yet", bg=CARD,
                              font=(FONT_UI, 11, "bold"))
        self.badge.pack(anchor="w", pady=(0, 8))

        self.probe_out = tk.Text(
            body, height=16, wrap="word", bg=MINT, fg=INK,
            relief="flat", font=(FONT_CODE, 9),
            highlightthickness=1, highlightbackground=ACCENT_L)
        self.probe_out.pack(fill="both", expand=True)
        sb = tk.Scrollbar(body, orient="vertical", command=self.probe_out.yview)
        sb.pack(side="right", fill="y")
        self.probe_out.configure(yscrollcommand=sb.set)

        self.probe_out.insert("end",
            "Expected lab service banner: %s\n\n"
            "Click 'Probe target' to fingerprint the box, 'Detect all lab vulns' "
            "to automatically check every lab vulnerability, or 'TCP port scan' "
            "for an open-port sweep.\n" % BANNER_MARKER)

        c3 = card(page, "Activity timeline")
        body3 = card_body(c3)
        self.timeline = tk.Text(body3, height=8, wrap="word", bg=MINT, fg=INK,
                                relief="flat", font=(FONT_CODE, 9),
                                highlightthickness=1, highlightbackground=ACCENT_L)
        self.timeline.pack(fill="both", expand=True)
        sb3 = tk.Scrollbar(body3, orient="vertical", command=self.timeline.yview)
        sb3.pack(side="right", fill="y")
        self.timeline.configure(yscrollcommand=sb3.set)
        self.timeline.insert("end", "(no activity recorded yet)\n")

    # ----------------------------------------------------------------- report
    def _build_report(self):
        page = tk.Frame(self.content, bg=BG)
        self.sections["report"] = page

        c = card(page, "HTML / JSON security report")
        body = card_body(c)
        tk.Label(body, bg=CARD, fg=MUTED, justify="left", wraplength=780,
                 font=(FONT_UI, 9),
                 text="Snapshots your target configuration, the generated Metasploit "
                      "module source, the latest live-check verdict, auto-detection "
                      "results and your activity timeline into a polished, "
                      "printer-friendly HTML file (or structured JSON) you can share "
                      "with your lab team or attach to a remediation ticket.").pack(anchor="w", pady=4)

        row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=(14, 0))
        action_button(row, "Generate & download report (.html)",
                      self.download_report, kind="primary").pack(side="left")
        action_button(row, "Download JSON (machine readable)",
                      self.download_json, kind="ghost").pack(side="left", padx=8)
        action_button(row, "Open in browser", self.open_report_browser,
                      kind="gold").pack(side="left", padx=8)

        c2 = card(page, "What will be inside the report")
        body2 = card_body(c2)
        for line in [
            "- Vulnerable template, module class & name, RHOSTS / RPORT / TARGETURI",
            "- Payload selection, rank, bad characters, author & CVE reference",
            "- Live check verdict (Safe / Vulnerable / Unknown) with probe evidence",
            "- Auto-detection table: which lab vulnerabilities match the target",
            "- Activity timeline (last 12 events) and open-port scan results",
            "- Full generated Ruby module source in a syntax-friendly block",
            "- Deployment cheatsheet (copy module, reload_all, run check)",
            "- Lab-safety notice and audit metadata (Report ID, timestamp, app version)",
        ]:
            tk.Label(body2, text=line, bg=CARD, fg=INK,
                     font=(FONT_UI, 9), anchor="w").pack(anchor="w", pady=1)

    # ------------------------------------------------------------- statusbar
    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=ACCENT_D)
        bar.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar()
        self.status = tk.Label(bar, textvariable=self.status_var, bg=ACCENT_D,
                               fg="#dffff6", font=(FONT_UI, 9), anchor="w")
        self.status.pack(side="left", padx=12, pady=4)
        tag = tk.Label(bar, text="python %s | platform: %s" % (
            platform.python_version(), platform.platform()),
            bg=ACCENT_D, fg="#9fe3d9", font=(FONT_UI, 8))
        tag.pack(side="right", padx=12)

    # ------------------------------------------------------------------ view
    def switch(self, key):
        for k, frame in self.sections.items():
            frame.pack_forget()
        self.sections[key].pack(fill="both", expand=True)
        for k, btn in self.nav.items():
            if k == key:
                btn.configure(bg=ACCENT, fg="#ffffff")
            else:
                btn.configure(bg=BG_SIDE, fg=ACCENT_D)
        self.header._redraw()

    def _status(self, msg):
        self.status_var.set("  %s" % msg)

    # ----------------------------------------------------------- config logic
    def _collect(self):
        tid = self.config.get("template_id") or "cmd-injection"
        try:
            tpl = VULN_TEMPLATES_BY_ID[tid]
        except KeyError:
            tpl = VULN_TEMPLATES[0]
        self.config["template_id"] = tpl.tid
        self.config["module_class"] = tpl.module_class
        self.config["module_name"] = tpl.module_name
        self.config["target_host"] = self.tgt_host.get().strip() or DEFAULT_TARGET
        try:
            self.config["target_port"] = int(self.tgt_port.get().strip())
        except ValueError:
            self.config["target_port"] = DEFAULT_PORT
        self.config["target_uri"] = self.tgt_uri.get().strip() or tpl.default_uri
        self.config["cli_name"] = self.cli_name.get().strip() or tpl.cli_name
        self.config["author"] = self.author.get().strip() or "MSF Lab Author"
        self.config["reference"] = self.cve.get().strip() or tpl.reference
        self.config["cve_id"] = tpl.cve_id
        chosen = self.payload.get()
        for name, payload, arch, _plat in PAYLOAD_CHOICES:
            if name == chosen:
                self.config["payload_name"] = payload
                self.config["payload_arch"] = arch
                break
        self.config["badchars"] = self.badchars.get().strip() or "\\x00"
        self.config["default_rank"] = self.rank.get() or "ExcellentRanking"

    def apply_config(self):
        self._collect()
        if self.remember.get():
            self._save_profile()
        self._refresh_advisor()
        self._status("Configuration applied: %s:%s%s" % (
            self.config["target_host"], self.config["target_port"],
            self.config["target_uri"]))

    def reset_config(self):
        self.config = default_config()
        self._gen = MetasploitModuleGenerator()
        self.template_combo.set(VULN_TEMPLATES_BY_ID[self.config["template_id"]].label)
        self.tgt_host.delete(0, "end"); self.tgt_host.insert(0, self.config["target_host"])
        self.tgt_port.delete(0, "end"); self.tgt_port.insert(0, str(self.config["target_port"]))
        self.tgt_uri.delete(0, "end");  self.tgt_uri.insert(0, self.config["target_uri"])
        self.mod_cat.set(self.config["module_name"])
        self.cli_name.delete(0, "end"); self.cli_name.insert(0, self.config["cli_name"])
        self.author.delete(0, "end");   self.author.insert(0, self.config["author"])
        self.cve.delete(0, "end");      self.cve.insert(0, self.config["reference"])
        self.badchars.delete(0, "end"); self.badchars.insert(0, self.config["badchars"])
        self.payload.set(PAYLOAD_CHOICES[0][0])
        self.rank.set(self.config["default_rank"])
        if self.remember.get():
            self._save_profile()
        self._refresh_advisor()
        self._status("Configuration reset to defaults.")

    # ------------------------------------------------- template picking
    def _on_template_pick(self, _event=None):
        chosen = self.template_combo.get()
        tid = next((t.tid for t in VULN_TEMPLATES if t.label == chosen), None)
        if tid is None:
            return
        self._gen.adopt_template(tid)
        self.config["template_id"] = tid
        self.config["module_name"] = self._gen.module_name
        self.config["cli_name"] = self._gen.cli_name
        self.config["description"] = self._gen.description
        self.config["reference"] = self._gen.reference
        self.config["cve_id"] = self._gen.cve_id
        self.config["target_uri"] = self._gen.target_uri
        self.config["template_label"] = VULN_TEMPLATES_BY_ID[tid].label
        self.cli_name.delete(0, "end"); self.cli_name.insert(0, self._gen.cli_name)
        self.cve.delete(0, "end");      self.cve.insert(0, self._gen.reference)
        self.tgt_uri.delete(0, "end");  self.tgt_uri.insert(0, self._gen.target_uri)
        self.mod_cat.set(self._gen.module_name)
        self._status("Template '%s' adopted - build the matching module or run "
                     "'Detect all lab vulns'." % self.config["template_label"])
        self._refresh_advisor()

    # ------------------------------------------------- history + profile + advice
    def _log_event(self, kind, detail, verdict=""):
        self.history.append({
            "ts": time.strftime("%H:%M:%S"),
            "kind": kind,
            "detail": str(detail)[:240],
            "verdict": str(verdict),
        })
        if len(self.history) > 60:
            del self.history[:-60]

    def _recent_detect(self):
        first = next((h for h in reversed(self.history)
                      if h["kind"] == "detect"), None)
        return first

    def _advice(self):
        cfg = self.config
        tid = cfg.get("template_id", "cmd-injection")
        host = "%s:%s" % (cfg.get("target_host"), cfg.get("target_port"))
        if self.check_result and self.check_result.get("state") == "Vulnerable":
            return (GOOD, "Lab verified at %s - deploy the generated module and run "
                          "`check` in msfconsole to confirm the verdict." % host)
        if self.check_result and not (self.check_result.get("probe") or {}).get("reachable"):
            return (WARN, "Target %s is offline - check the port in section 1, then start the "
                          "lab with `python vuln_service.py --host %s --port %s`."
                          % (host, cfg.get("target_host"), cfg.get("target_port")))
        d = cfg.get("last_detect")
        if isinstance(d, dict) and d.get("open_vulns"):
            open_list = ", ".join(d["open_vulns"])
            if tid in d["open_vulns"]:
                return (GOOD, "Auto-detection matches the '%s' template - exploit it "
                              "via %s now (payload: %s)." % (
                                  tid, cfg.get("target_uri"), cfg.get("payload_name")))
            return (ACCENT, "Auto-detection found open vulnerabilities (%s) but the "
                            "selected template is '%s'. Switch templates or rebuild "
                            "in section 2." % (open_list, tid))
        if tid == "cmd-injection":
            return (ACCENT, "Tip for '%s': point TARGETURI at /exec and keep LHOST "
                            "routable from the lab box. Then generate + save the .rb."
                            % tid)
        return (MUTED, "No live activity yet. Run 'Detect all lab vulns' in section 3 "
                       "for a smart recommendation.")

    def _refresh_advisor(self):
        color, text = self._advice()
        self.advisor.configure(text="  " + text, fg=color)

    def _save_profile(self):
        try:
            os.makedirs(self.profile_dir, exist_ok=True)
            import json
            data = {
                "remember": bool(self.remember.get()),
                "template_id": self.config.get("template_id", "cmd-injection"),
                "target_host": self.config.get("target_host"),
                "target_port": self.config.get("target_port"),
                "target_uri": self.config.get("target_uri"),
                "cli_name": self.config.get("cli_name"),
                "author": self.config.get("author"),
                "reference": self.config.get("reference"),
                "payload_name": self.config.get("payload_name"),
                "badchars": self.config.get("badchars"),
                "default_rank": self.config.get("default_rank"),
            }
            with open(self.profile_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception:
            _write_error("profile-save", sys.exc_info())

    def _load_profile(self):
        if not os.path.isfile(self.profile_path):
            return
        try:
            import json
            with open(self.profile_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            _write_error("profile-load", sys.exc_info())
            return
        if not data.get("remember", True):
            return
        tid = data.get("template_id", "cmd-injection")
        if tid in VULN_TEMPLATES_BY_ID:
            self._gen.adopt_template(tid)
            self.config["template_id"] = tid
            self.config["template_label"] = VULN_TEMPLATES_BY_ID[tid].label
            self.template_combo.set(VULN_TEMPLATES_BY_ID[tid].label)
        for key in ("target_host", "target_port", "target_uri", "cli_name", "author",
                    "reference"):
            if key in data and data[key] is not None:
                self.config[key] = data[key]
        for widget, key in ((self.tgt_host, "target_host"), (self.tgt_port, "target_port"),
                            (self.tgt_uri, "target_uri"), (self.cli_name, "cli_name"),
                            (self.author, "author"), (self.cve, "reference")):
            widget.delete(0, "end")
            widget.insert(0, str(self.config.get(key, "")))
        try:
            self.badchars.delete(0, "end")
            self.badchars.insert(0, self.config.get("badchars", "\\x00"))
        except tk.TclError:
            pass
        chosen_payload = next((n for n, p, a, _plat in PAYLOAD_CHOICES
                               if p == data.get("payload_name")), PAYLOAD_CHOICES[0][0])
        self.payload.set(chosen_payload)
        rank = data.get("default_rank")
        if rank in ("ExcellentRanking", "GreatRanking", "GoodRanking", "NormalRanking"):
            self.rank.set(rank)
        self.mod_cat.set(self.config.get("module_name", ""))

    def _on_close(self):
        if self.remember.get():
            self._save_profile()
        self.root.destroy()

    # ------------------------------------------------------------- builder logic
    def generate_module(self):
        self.apply_config()
        tg = self.config.get("template_id") or "cmd-injection"
        gen = MetasploitModuleGenerator()
        gen.adopt_template(tg)
        for k in ("module_name", "cli_name", "author", "reference", "payload_name",
                  "payload_arch", "badchars", "default_rank", "disclosure_date"):
            setattr(gen, k, self.config.get(k))
        gen.target_host = self.config["target_host"]
        gen.target_port = self.config["target_port"]
        gen.target_uri = self.config["target_uri"]
        source = gen.generate()
        self.config["module_source"] = source
        self.config["gen"] = gen
        self.code.configure(state="normal")
        self.code.delete("1.0", "end")
        self.code.insert("1.0", source)
        self.code.configure(state="disabled")
        gen_name = self.config["module_name"].rsplit("/", 1)[-1]
        self._log_event("build", "generated %s (%d lines)" % (
            self.config["module_name"], source.count("\n") + 1), "built")
        self._status("Module generated (%d lines). Copy or save as %s.rb" % (
            source.count("\n") + 1, gen_name))

    def copy_module(self):
        if not self.config.get("module_source", "").strip():
            self.generate_module()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.config["module_source"])
        self._status("Module source copied to clipboard.")

    def save_module_rb(self):
        self.generate_module()
        fname = filedialog.asksaveasfilename(
            title="Save Metasploit module",
            defaultextension=".rb",
            initialfile="vulnlab_exec.rb",
            filetypes=[("Ruby module", "*.rb"), ("All files", "*.*")])
        if not fname:
            return
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(self.config["module_source"])
        self._status("Module saved to %s" % fname)

    def quick_syntax(self):
        source = self.config.get("module_source", "")
        if not source.strip():
            source = str(getattr(self.config.get("gen"), "generate", lambda: "")())
        if not source.strip():
            self.generate_module()
            source = self.config["module_source"]
        opens = source.count("do") + source.count("if ") + source.count("def ") + source.count("while ") + 1  # class
        closes = source.count("end")
        balanced = abs(opens - closes) <= 1
        msg = ("Syntax scan: %d block-open keywords vs %d `end` keywords AND "
               "unbalanced=%s." % (opens, closes, not balanced))
        if balanced:
            self._status("Quick syntax scan looks OK. %s" % msg)
            messagebox.showinfo("Quick syntax check", msg + "\n\nSignature: " +
                                self.config["module_name"])
        else:
            messagebox.showwarning("Quick syntax check", msg + "\n\nReview the "
                                   "generated code before loading it into Metasploit.")

    # ----------------------------------------------------------------- test logic
    def _poll(self):
        """Main-thread idle loop. Drains background results safely."""
        try:
            while True:
                done, result = self._work_queue.get_nowait()
                if isinstance(result, BaseException):
                    _write_error("worker", (type(result), result, result.__traceback__))
                    self._status("Background task failed - error logged to %s" % _error_log_path())
                    continue
                try:
                    done(result)
                except Exception:
                    _write_error("callback", sys.exc_info())
                    self._status("UI callback failed - error logged to %s" % _error_log_path())
        except queue.Empty:
            pass
        try:
            self._poll_job = self.root.after(80, self._poll)
        except (tk.TclError, RuntimeError):
            pass  # window is being destroyed

    def _run_in_thread(self, fn, done):
        def worker():
            try:
                result = fn()
            except BaseException as exc:  # never touch Tk from threads
                result = exc
            self._work_queue.put((done, result))
        threading.Thread(target=worker, daemon=True).start()

    def _probe_safe(self):
        self.probe.host = self.config["target_host"]
        self.probe.port = self.config["target_port"]
        return self.probe.probe()

    def _set_badge(self, text, color):
        self.badge.configure(text=text, fg=color)

    def _refresh_timeline(self):
        self.timeline.configure(state="normal")
        self.timeline.delete("1.0", "end")
        if not self.history:
            self.timeline.insert("end", "(no activity recorded yet)\n")
        for h in self.history[-40:]:
            verdict = (" [%s]" % h["verdict"]) if h["verdict"] else ""
            self.timeline.insert("end", "%s  %-8s  %s%s\n" % (
                h["ts"], h["kind"], h["detail"], verdict))
        self.timeline.configure(state="disabled")

    def run_probe(self):
        self.apply_config()
        self._set_badge("Probing ...", ACCENT)
        self._status("Probing %s:%s ..." % (self.config["target_host"], self.config["target_port"]))
        self._run_in_thread(self._probe_safe, self._on_probe_done)

    def _on_probe_done(self, probe):
        self.check_result = {"probe": probe, "state": "Safe", "detail": ""}
        self._log_probe(probe)
        if not probe["reachable"]:
            self._set_badge("OFFLINE - %s" % (probe.get("warning") or "no route"), WARN)
            self._status("Target offline. Is vuln_service.py running?")
            self._log_event("probe", "%s:%s unreachable" % (probe["host"], probe["port"]), "offline")
        elif probe["vulnlab"]:
            self._set_badge("ONLINE - VulnLab lab service detected", GOOD)
            self._status("VulnLab banner found. You can now run `check` or auto-detect.")
            self._log_event("probe", "VulnLab banner found at %s:%s" % (probe["host"], probe["port"]), "online")
        else:
            self._set_badge("REACHED - no lab banner found", WARN)
            self._status("Service answered but no VulnLab banner. Check host/port/URI.")
            self._log_event("probe", "service answered, banner missing", "unknown")
        self._refresh_timeline()
        self._refresh_advisor()

    def _log_probe(self, probe):
        self.probe_out.delete("1.0", "end")
        lines = [
            "[probe] %s" % probe["probe_ts"],
            "[host ] %s [port] %s" % (probe["host"], probe["port"]),
            "[tcp  ] %s" % ("reachable" if probe["reachable"] else "not reachable"),
            "[http ] status=%s" % (probe.get("health_code") or "n/a"),
            "[login] %s" % probe.get("banner"),
            "[lab  ] VulnLab marker: %s" % ("present" if probe.get("vulnlab") else "absent"),
        ]
        if probe.get("warning"):
            lines.append("[warn ] %s" % probe["warning"])
        self.probe_out.insert("end", "\n".join(lines) + "\n")

    def run_check(self):
        self.apply_config()
        self._set_badge("Running simulated `check` ...", ACCENT)

        def fn():
            return self.probe.run_check(self.config["target_host"], self.config["target_port"],
                                        self.config.get("target_uri", DEFAULT_URI))

        def done(check):
            self.check_result = check
            probe = check["probe"]
            self._log_probe(probe)
            self.probe_out.insert("end", "\n[check] %s\n[state] %s\n[detail] %s\n" % (
                check["check_ts"], check["state"], check["detail"]))
            if check["state"] == "Vulnerable":
                self._set_badge("VERDICT: VULNERABLE - proceed inside the lab", GOOD)
            elif check["state"] == "Safe":
                self._set_badge("VERDICT: SAFE - banner not present", MUTED)
            else:
                self._set_badge("VERDICT: UNKNOWN - target unreachable", WARN)
            self._log_event("check", "state=%s banner=%s" % (check["state"], probe.get("banner")),
                            check["state"])
            self._status("check() finished: %s" % check["state"])
            self._refresh_timeline()
            self._refresh_advisor()
        self._run_in_thread(fn, done)

    def verify_exec(self):
        """Template-aware endpoint verification (uses the live detector)."""
        self.apply_config()
        tid = self.config.get("template_id") or "cmd-injection"
        probe = self.probe.probe(self.config["target_host"], self.config["target_port"])
        if not probe["reachable"]:
            self._set_badge("ENDPOINT NOT REACHED", WARN)
            self._log_probe(probe)
            self._log_event("verify", "target unreachable", "fail")
            self._refresh_timeline()
            self._status("Target offline - endpoint verification aborted.")
            return
        checks = {
            "cmd-injection": self.probe.check_cmd_injection,
            "path-traversal": self.probe.check_path_traversal,
            "config-leak": self.probe.check_config_leak,
        }
        self._set_badge("Verifying %r endpoint ..." % tid, ACCENT)

        def fn():
            return checks.get(tid, self.probe.check_cmd_injection)(
                self.config["target_host"], self.config["target_port"])

        def done(r):
            self.probe_out.delete("1.0", "end")
            self.probe_out.insert("end", "[verify] %s (%s)\n[detail ] %s\n[evidence]\n%s\n" % (
                r["ts"], r["template"], r["detail"], r.get("evidence") or "n/a"))
            if r.get("detected"):
                self._set_badge("ENDPOINT IS EXPLOITABLE (lab) - template matches", GOOD)
                self._status("Selected endpoint verified live. Generate the module in section 2.")
                self._log_event("verify", "%s confirmed live" % r["template"], "vulnerable")
            else:
                self._set_badge("ENDPOINT NOT MATCHING TEMPLATE", WARN)
                self._log_event("verify", "%s not confirmed" % r["template"], "fail")
            self._refresh_timeline()
            self._refresh_advisor()
        self._run_in_thread(fn, done)

    def run_detect_all(self):
        self.apply_config()
        self._set_badge("Running auto-detection ...", ACCENT)

        def fn():
            return self.probe.detect_all(self.config["target_host"], self.config["target_port"])

        def done(det):
            self.config["last_detect"] = det
            self.probe_out.delete("1.0", "end")
            base = det["base"]
            self.probe_out.insert("end", "[detect] %s\n[summary] %s\n[target] %s:%s\n\n" % (
                base["probe_ts"], det["summary"], base["host"], base["port"]))
            for tid, r in det["checks"].items():
                mark = "VULNERABLE" if r["detected"] else "safe"
                color = GOOD if r["detected"] else MUTED
                self.probe_out.insert("end", "- %s: %s\n  %s\n  evidence: %s\n" % (
                    tid, mark, r["detail"], (r.get("evidence") or "n/a")[:120]))
            if det["open_vulns"]:
                self._set_badge("DETECTED: %s" % ", ".join(det["open_vulns"]), GOOD)
                self._log_event("detect", "open vulns: %s" % ", ".join(det["open_vulns"]),
                                "vulnerable")
            elif det["summary"] == "Target unreachable":
                self._set_badge("TARGET UNREACHABLE", WARN)
                self._log_event("detect", "target unreachable", "offline")
            else:
                self._set_badge("NO LAB VULNERABILITY MATCHED", MUTED)
                self._log_event("detect", "no vuln matched (%s)" % det["summary"], "safe")
            self._status("Auto-detection finished: %s" % det["summary"])
            self._refresh_timeline()
            self._refresh_advisor()
        self._run_in_thread(fn, done)

    def run_port_scan(self):
        self.apply_config()
        self._set_badge("Scanning common TCP ports ...", ACCENT)

        def fn():
            return scan_tcp_ports(self.config["target_host"], COMMON_PORTS)

        def done(ports):
            self.last_scan = ports
            self.probe_out.delete("1.0", "end")
            if ports:
                self.probe_out.insert("end", "[scan] open ports on %s: %s\n" % (
                    self.config["target_host"], ", ".join(str(p) for p in ports)))
                self._set_badge("OPEN PORTS: %d" % len(ports), GOOD)
            else:
                self.probe_out.insert("end", "[scan] no open ports on %s (of %s)\n" % (
                    self.config["target_host"], ", ".join(str(p) for p in COMMON_PORTS)))
                self._set_badge("NO OPEN PORTS - is the lab running?", WARN)
            self._log_event("scan", "open ports: %s" % (ports or "none"),
                            "open=%d" % len(ports))
            self._status("Port scan finished - %d open port(s)." % len(ports))
            self._refresh_timeline()
            self._refresh_advisor()
        self._run_in_thread(fn, done)

    # ---------------------------------------------------------------- report logic
    def _ensure_report_data(self):
        self.apply_config()
        if "module_source" not in self.config or not self.config.get("module_source", "").strip():
            self.generate_module()

    def build_report(self) -> LabHtmlReport:
        self._ensure_report_data()
        return LabHtmlReport(self.config, self.check_result, self.history, self.last_scan)

    @staticmethod
    def _save_dialog(title, initialfile, defaultext, patterns):
        return filedialog.asksaveasfilename(
            title=title, defaultextension=defaultext,
            initialfile=initialfile, filetypes=patterns)

    def download_report(self):
        report = self.build_report()
        html_doc = report.to_html()
        fname = self._save_dialog(
            "Download report", "msf-lab-report_%s.html" % report.report_id, ".html",
            [("HTML report", "*.html"), ("All files", "*.*")])
        if not fname:
            return
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(html_doc)
        self._status("Report downloaded: %s" % os.path.basename(fname))
        self._log_event("report", "HTML written: %s" % os.path.basename(fname), "ok")
        self._refresh_timeline()
        open_result = messagebox.askyesno(
            "Report downloaded",
            "Saved:\n%s\n\nOpen it in your browser now?" % fname)
        if open_result:
            self._open_path(fname)

    def download_json(self):
        report = self.build_report()
        fname = self._save_dialog(
            "Download JSON", "msf-lab-report_%s.json" % report.report_id, ".json",
            [("JSON report", "*.json"), ("All files", "*.*")])
        if not fname:
            return
        with open(fname, "wb") as fh:
            fh.write(report.to_json().encode("utf-8"))
        self._status("JSON report downloaded: %s" % os.path.basename(fname))
        self._log_event("report", "JSON written: %s" % os.path.basename(fname), "ok")
        self._refresh_timeline()

    def open_report_browser(self):
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".html", prefix="msf-lab-report_")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(self.build_report().to_html())
        self._open_path(tmp)
        self._status("Opened in browser (temporary copy in system temp).")

    @staticmethod
    def _open_path(path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                os.system('open "%s"' % path)
            else:
                os.system('xdg-open "%s"' % path)
        except OSError:
            pass


def _run_selftest(ui) -> str:
    """Headless self-test executed INSIDE the frozen app.

    Gated by MSF_STUDIO_SELFTEST=1. Exercises section switching, config,
    module generation, HTML report rendering + writing, and an offline
    probe. Writes results to %TEMP%\\msf_studio_selftest.out
    """
    import traceback as _tb

    results: list = []
    out_path = os.path.join(tempfile.gettempdir(), "msf_studio_selftest.out")

    def ok(name, passed, note=""):
        results.append(("PASS - " if passed else "FAIL - ") + name + (" | " + note if note else ""))

    try:
        ui.switch("builder")
        root_update = ui.root.update_idletasks
        root_update()
        ui.apply_config()
        ui.generate_module()
        src = ui.config.get("module_source", "")
        ok("switch sections + apply config", ui.sections["builder"].winfo_ismapped())
        ok("module generation", "class MetasploitModule" in src,
           "lines=%d" % (src.count("\n") + 1))
        html = ui.build_report().to_html()
        ok("html report render", len(html) > 3000, "bytes=%d" % len(html))
        report_file = os.path.join(tempfile.gettempdir(), "msf_studio_selftest_report.html")
        with open(report_file, "w", encoding="utf-8") as fh:
            fh.write(html)
        ok("report file write", os.path.getsize(report_file) > 3000)
        # template switching -> scanner-style module
        ui.template_combo.set(VULN_TEMPLATES_BY_ID["path-traversal"].label)
        ui._on_template_pick()
        ui.generate_module()
        trav_src = ui.config.get("module_source", "")
        ok("template switch to scanner", "run_host" in trav_src and "report_web_vuln" in trav_src,
           "lines=%d" % (trav_src.count("\n") + 1))
        # JSON report twin
        ui.template_combo.set(VULN_TEMPLATES_BY_ID["cmd-injection"].label)
        ui._on_template_pick()
        ui.generate_module()
        rep = ui.build_report()
        json_file = os.path.join(tempfile.gettempdir(), "msf_studio_selftest_report.json")
        with open(json_file, "wb") as fh:
            fh.write(rep.to_json().encode("utf-8"))
        import json as _json
        with open(json_file, "r", encoding="utf-8") as fh:
            _json.load(fh)
        ok("json report write + parse", os.path.getsize(json_file) > 500,
           "bytes=%d" % os.path.getsize(json_file))
        # offline detect_all must not raise
        ui.probe.host = "127.0.0.1"
        ui.probe.port = 1  # connection refused -> fast offline verdict
        probe = ui.probe.probe()
        ok("probe offline handling", probe["reachable"] is False,
           "warning=%s" % (probe.get("warning") or "none"))
        det = ui.probe.detect_all()
        ok("detect_all offline safe", det["summary"] == "Target unreachable",
           "summary=%s" % det["summary"])
        ok("port scan offline empty", scan_tcp_ports("127.0.0.1", [1]) == [],
           "ports=%r" % scan_tcp_ports("127.0.0.1", [1]))
        # LIVE probe/detect mode: run against a real lab on 127.0.0.1:8080.
        if os.environ.get("MSF_STUDIO_SELFTEST_LIVE") == "1":
            live = LabServiceProbe("127.0.0.1", 8080).probe()
            ok("frozen LIVE probe 127.0.0.1:8080", live["reachable"] is True,
               "reachable=%r banner=%r warning=%r" % (
                   live["reachable"], live.get("banner"), live.get("warning")))
            if live["reachable"]:
                live_det = LabServiceProbe("127.0.0.1", 8080).detect_all()
                ok("frozen LIVE detect_all", len(live_det["open_vulns"]) == 3,
                   "summary=%r open=%r" % (live_det["summary"], live_det["open_vulns"]))
                ok("frozen LIVE port scan", 8080 in scan_tcp_ports("127.0.0.1", [8080]),
                   "open8080=%r" % (8080 in scan_tcp_ports("127.0.0.1", [8080])))
        ui.run_probe()  # threaded path: must not raise
        for _ in range(20):
            try:
                ui.root.update()
            except (tk.TclError, RuntimeError):
                break
            time.sleep(0.05)
        ok("threaded probe path", True)
    except BaseException as exc:  # noqa: BLE001
        results.append("EXCEPTION: %r\n%s" % (exc, _tb.format_exc()))

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("MSF Lab Module Studio selftest\n" + "=" * 40 + "\n")
        fh.write("\n".join(results) + "\n")
    return out_path


def main() -> int:
    sys.excepthook = lambda typ, val, tb: _write_error("global", (typ, val, tb))

    root = tk.Tk()
    root.report_callback_exception = lambda typ, val, tb: _write_error("tk", (typ, val, tb))
    ui = LabModuleStudio(root)

    if os.environ.get("MSF_STUDIO_SELFTEST") == "1":
        out = _run_selftest(ui)
        try:
            root.destroy()
        except tk.TclError:
            pass
        # short marker file so automation can detect completion
        with open(os.path.join(tempfile.gettempdir(), "msf_studio_selftest.done"), "w",
                  encoding="utf-8") as fh:
            fh.write(out)
        return 0

    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())