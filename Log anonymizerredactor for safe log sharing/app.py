"""Log Anonymizer & Redactor - Desktop GUI.

A beautiful, tab-driven desktop application for desensitizing logs before
sharing them. Built with customtkinter for a modern look, ships with a
self-contained HTML report exporter.

Run:            python app.py
Bundle to exe:  python build_exe.py
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core import Redactor

try:
    from core.html_report import save_html_report
except Exception:  # pragma: no cover
    save_html_report = None  # type: ignore[assignment]

APP_NAME = "Log Anonymizer & Redactor"
APP_TAG = "Desensitize logs before sharing"
VERSION = "1.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "app.ico")

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
ACCENT = "#2fbf8f"
ACCENT_HOVER = "#279e77"
DANGER = "#ef4444"

STRATEGIES = [
    (Redactor.STRATEGY_MASK, "Partial Mask  (jo***)",
     "Show first characters, hide the rest. Best readability."),
    (Redactor.STRATEGY_FULL, "Full Redact  [REDACTED]",
     "Replace every match with a generic [REDACTED] tag."),
    (Redactor.STRATEGY_HASH, "SHA-256 Hash  (ab12cd34ef)",
     "Deterministic fingerprint - same input, same token."),
    (Redactor.STRATEGY_TOKEN, "Pseudo Tokens  (EM0001)",
     "Sequential anonymous IDs for analysis workflows."),
]


def resource_path(rel: str) -> str:
    """Return a path that works both frozen (exe) and in source."""
    base = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base, rel)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class LogRedactorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.enabled: dict[str, bool] = {k: True for k in Redactor.MODES}
        self.strategy = Redactor.DEFAULT_STRATEGY
        self.last_result: object | None = None
        self.last_original: str = ""
        self._busy = False
        self._result_queue: queue.Queue = queue.Queue()

        # ---------- window ----------
        self.title(f"{APP_NAME}  v{VERSION}")
        w, h = 1180, 760
        self.geometry(f"{w}x{h}")
        self.minsize(980, 640)

        try:
            icon = ctk.CTkImage(light_image=None, dark_image=None, size=(24, 24))
        except Exception:
            icon = None
        _ = icon

        self._configure_theme()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        self.after(80, self._safe_load_icon)
        self.after(100, self._poll_results)

    # ------------------------------------------------------------------ #
    def _configure_theme(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def _safe_load_icon(self) -> None:
        path = resource_path(os.path.join("assets", "app.ico"))
        if os.path.exists(path):
            try:
                self.iconbitmap(path)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Header
    # ------------------------------------------------------------------ #
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(18, 8))

        ctk.CTkLabel(
            header, text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text=APP_TAG,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("#5b6470", "#a3adbd"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        theme_btn = ctk.CTkButton(
            header, text="\u263d  Light", width=96, height=32,
            font=ctk.CTkFont(size=13), corner_radius=16,
            fg_color=("#e2e8f0", "#334155"), text_color=("#0f172a", "#e2e8f0"),
            hover_color=("#cbd5e1", "#475569"), command=self._toggle_theme,
        )
        theme_btn.grid(row=0, column=1, rowspan=2, sticky="ne")
        self._theme_btn = theme_btn

    # ------------------------------------------------------------------ #
    #  Tabs
    # ------------------------------------------------------------------ #
    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self, corner_radius=14,
            fg_color=("white", "#0b1220"),
            segmented_button_fg_color=("#e2e8f0", "#1e293b"),
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_hover_color=("#d3d9e3", "#2b3a52"),
            text_color="#e2e8f0",
        )
        self.tabs.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=24, pady=(12, 8))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.t_redact = self.tabs.add("  Redact  ")
        self.t_options = self.tabs.add("  Options  ")
        self.t_report = self.tabs.add("  Report  ")
        self.t_about = self.tabs.add("  About  ")

        self.tabs.tab("  Redact  ").grid_columnconfigure(0, weight=3)
        self.tabs.tab("  Redact  ").grid_columnconfigure(1, weight=4)
        self.tabs.tab("  Options  ").grid_columnconfigure(0, weight=1)
        self.tabs.tab("  Report  ").grid_columnconfigure(0, weight=1)

        self._build_redact_tab()
        self._build_options_tab()
        self._build_report_tab()
        self._build_about_tab()

    # -- Redact tab ---------------------------------------------------- #
    def _build_redact_tab(self) -> None:
        panel = self.t_redact

        # left: input
        in_frame = ctk.CTkFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"))
        in_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 0))
        in_frame.grid_rowconfigure(1, weight=1)
        in_frame.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(in_frame, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        ctk.CTkLabel(top, text="Source Log",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)
        ctk.CTkButton(top, text="Open File", width=84, height=28,
                      font=ctk.CTkFont(size=12), corner_radius=12,
                      command=self._load_file).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Paste", width=64, height=28,
                      font=ctk.CTkFont(size=12), corner_radius=12,
                      command=self._paste_clipboard).pack(side="right", padx=4)

        self.input_box = ctk.CTkTextbox(
            in_frame, wrap="word", corner_radius=10,
            fg_color=("#f1f5f9", "#0d1626"), border_width=1,
            border_color=("#cbd5e1", "#1e293b"),
            font=ctk.CTkFont(family="Cascadia Code, Consolas", size=13),
        )
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # right: output
        out_frame = ctk.CTkFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"))
        out_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        out_frame.grid_rowconfigure(1, weight=1)
        out_frame.grid_columnconfigure(0, weight=1)

        top2 = ctk.CTkFrame(out_frame, fg_color="transparent")
        top2.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        ctk.CTkLabel(top2, text="Sanitized Output",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)

        self.run_btn = ctk.CTkButton(
            top2, text="\u2694  Anonymize", width=118, height=32,
            font=ctk.CTkFont(size=13, weight="bold"), corner_radius=14,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._start_redact,
        )
        self.run_btn.pack(side="right", padx=4)

        ctk.CTkButton(top2, text="Copy", width=68, height=28,
                      font=ctk.CTkFont(size=12), corner_radius=12,
                      command=self._copy_output).pack(side="right", padx=4)

        self.output_box = ctk.CTkTextbox(
            out_frame, wrap="word", corner_radius=10,
            fg_color=("#f1f5f9", "#0d1626"), border_width=1,
            border_color=("#14b8a6", "#134e4a"),
            font=ctk.CTkFont(family="Cascadia Code, Consolas", size=13),
            text_color=("#14532d", "#5eead4"),
        )
        self.output_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # stats bar under output
        stats = ctk.CTkFrame(out_frame, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.stats_label = ctk.CTkLabel(stats, text="Ready.",
                                        font=ctk.CTkFont(size=12), text_color=("#64748b", "#94a3b8"))
        self.stats_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(stats, width=140, height=8, corner_radius=4,
                                           progress_color=ACCENT, fg_color=("#e2e8f0", "#1e293b"))
        self.progress.pack(side="left")
        self.progress.set(0)

    # -- Options tab ---------------------------------------------------- #
    def _build_options_tab(self) -> None:
        panel = self.t_options

        left = ctk.CTkScrollableFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"),
                                      label_text="    Detection Modules    ")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 0))
        left.grid_rowconfigure(99, weight=1)

        right = ctk.CTkFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.mode_switches: dict[str, ctk.CTkSwitch] = {}
        for i, (key, mode) in enumerate(Redactor.MODES.items()):
            sw = ctk.CTkSwitch(
                left, text=f"{mode.label}",
                onvalue=True, offvalue=False,
                progress_color=mode.color,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self._toggle_mode(k),
            )
            sw.select()
            sw.grid(row=i, column=0, sticky="w", padx=16, pady=7)
            self.mode_switches[key] = sw

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(right, text="Redaction Strategy",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 2))

        var = ctk.StringVar(value=self.strategy)
        self._strategy_var = var
        for i, (key, label, desc) in enumerate(STRATEGIES):
            ctk.CTkRadioButton(
                right, text=label, variable=var, value=key,
                command=self._set_strategy,
                font=ctk.CTkFont(size=13), fg_color=ACCENT, hover_color=ACCENT_HOVER,
            ).grid(row=1 + i, column=0, sticky="w", padx=18, pady=5)

        hint = ctk.CTkLabel(right, text="\u2022 Pick a mask style for detected values.",
                            font=ctk.CTkFont(size=12), text_color=("#64748b", "#94a3b8"))
        hint.grid(row=5, column=0, sticky="w", padx=18, pady=(4, 0))

        d1 = ctk.CTkFrame(right, corner_radius=12, fg_color=("#f8fafc", "#0d1626"), border_width=1,
                          border_color=("#e2e8f0", "#1e293b"))
        d1.grid(row=7, column=0, sticky="ew", padx=18, pady=(16, 0))
        ctk.CTkLabel(d1, text="Privacy Guarantees",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color="#2fbf8f").pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(d1, text="\u2714  All processing is 100% local\n"
                              "\u2714  No network calls, no telemetry\n"
                              "\u2714  Original values never written to disk\n"
                              "\u2714  XOR/audit trail optional per run",
                     font=ctk.CTkFont(size=12), text_color=("#334155", "#a3adbd"),
                     justify="left").pack(anchor="w", padx=14, pady=(2, 12))

        d2 = ctk.CTkFrame(right, corner_radius=12, fg_color=("#f8fafc", "#0d1626"), border_width=1,
                          border_color=("#e2e8f0", "#1e293b"))
        d2.grid(row=8, column=0, sticky="ew", padx=18, pady=(10, 0))
        ctk.CTkLabel(d2, text="Tips",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(d2, text="\u2022 Load large logs via \u201cOpen File\u201d\n"
                              "\u2022 Use \u201cPseudo Tokens\u201d for downstream analysis\n"
                              "\u2022 Export the HTML report for an audit trail",
                     font=ctk.CTkFont(size=12), text_color=("#334155", "#a3adbd"),
                     justify="left").pack(anchor="w", padx=14, pady=(2, 12))

    # -- Report tab ----------------------------------------------------- #
    def _build_report_tab(self) -> None:
        panel = self.t_report
        panel.grid_rowconfigure(0, weight=1)

        wrap = ctk.CTkScrollableFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"),
                                      label_text="    Run Reports   ")
        wrap.grid(row=0, column=0, sticky="nsew")

        self.report_card = ctk.CTkFrame(wrap, corner_radius=12, fg_color=("#f8fafc", "#0d1626"),
                                        border_width=1, border_color=("#e2e8f0", "#1e293b"))
        self.report_card.pack(fill="x", padx=6, pady=6)
        self._empty_report_card(wrap)

    def _empty_report_card(self, parent=None) -> None:
        for c in self.report_card.winfo_children():
            c.destroy()
        ctk.CTkLabel(self.report_card, text="No report yet.",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(24, 2))
        ctk.CTkLabel(self.report_card, text="Run the Redact tab first, then \u201cdownload\u201d the HTML report from here.",
                     font=ctk.CTkFont(size=12), text_color=("#64748b", "#94a3b8")).pack(padx=20, pady=(2, 20))

    def _populate_report_card(self) -> None:
        for c in self.report_card.winfo_children():
            c.destroy()
        r = self.last_result
        if r is None:
            self._empty_report_card()
            return

        ctk.CTkLabel(self.report_card, text="Last Run Summary",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(self.report_card, text=f"{r.total_redactions} items redacted in {r.elapsed_ms:.0f} ms",
                     font=ctk.CTkFont(size=12), text_color=("#64748b", "#94a3b8")).pack(anchor="w", padx=18)

        grid = ctk.CTkFrame(self.report_card, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=10)
        for i, (key, cnt) in enumerate(sorted(r.counts.items(), key=lambda kv: -kv[1])):
            mode = Redactor.MODES.get(key)
            col = (mode.color if mode else "#cbd5e1", mode.color if mode else "#64748b")
            ctk.CTkLabel(grid, text=f"{cnt}", font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=col).grid(row=i % 6, column=(i // 6) * 2, sticky="w", padx=(0, 16), pady=2)
            ctk.CTkLabel(grid, text=mode.label if mode else str(cnt),
                         font=ctk.CTkFont(size=12)).grid(row=i % 6, column=(i // 6) * 2 + 1, sticky="w", padx=(0, 22), pady=2)

        btns = ctk.CTkFrame(self.report_card, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(2, 14))
        ctk.CTkButton(btns, text="\u2b07  Download HTML Report", width=200, height=34,
                      font=ctk.CTkFont(size=13, weight="bold"), corner_radius=14,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._download_report).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Open in Browser", width=150, height=34,
                      font=ctk.CTkFont(size=13), corner_radius=14,
                      fg_color=("#e2e8f0", "#334155"), text_color=("#0f172a", "#e2e8f0"),
                      hover_color=("#cbd5e1", "#475569"),
                      command=self._open_in_browser).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Save Sanitized Log (.txt)", width=180, height=34,
                      font=ctk.CTkFont(size=13), corner_radius=14,
                      fg_color=("#e2e8f0", "#334155"), text_color=("#0f172a", "#e2e8f0"),
                      hover_color=("#cbd5e1", "#475569"),
                      command=self._save_txt).pack(side="left", padx=6)

    # -- About tab ------------------------------------------------------ #
    def _build_about_tab(self) -> None:
        panel = self.t_about
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(panel, corner_radius=12, fg_color=("white", "#111a2e"))
        wrap.grid(row=0, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(wrap, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#2fbf8f").grid(row=0, column=0, pady=(28, 2))
        ctk.CTkLabel(wrap, text=APP_TAG, font=ctk.CTkFont(size=13),
                     text_color=("#64748b", "#94a3b8")).grid(row=1, column=0)
        ctk.CTkLabel(wrap, text=f"Version {VERSION}", font=ctk.CTkFont(size=12),
                     text_color=("#94a3b8", "#64748b")).grid(row=2, column=0, pady=(6, 14))

        info = (
            "Detects and replaces sensitive data inside application logs so they\n"
            "can be shared with support, vendors, or AI assistants \u2014 safely.\n\n"
            "Supported patterns:\n"
            "  IPv4 / IPv6, e-mail, phone numbers, credit-card PANs, SSNs,\n"
            "  UUIDs, JWTs, API keys & secrets, URL credentials,\n"
            "  password literals, MAC addresses, geo coordinates,\n"
            "  usernames / user-ids and AWS ARNs.\n\n"
            "Everything runs locally. Nothing leaves your machine.\n"
        )
        ctk.CTkLabel(wrap, text=info, font=ctk.CTkFont(size=13),
                     text_color=("#334155", "#a3adbd"), justify="left").grid(row=3, column=0, padx=48)

        stack = ctk.CTkFrame(wrap, corner_radius=12, fg_color=("#f8fafc", "#0d1626"),
                             border_width=1, border_color=("#e2e8f0", "#1e293b"))
        stack.grid(row=4, column=0, padx=48, pady=(18, 4), sticky="ew")
        ctk.CTkLabel(stack, text="Built with",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(stack, text="Python 3  \u00b7  customtkinter  \u00b7  PyInstaller",
                     font=ctk.CTkFont(size=12), text_color=("#334155", "#a3adbd")).pack(anchor="w", padx=14, pady=(2, 12))

        ctk.CTkLabel(wrap, text="\u00a9 2026  \u2014  For safe log sharing.",
                     font=ctk.CTkFont(size=11), text_color=("#94a3b8", "#64748b")).grid(row=9, column=0, pady=(8, 16))

    # ------------------------------------------------------------------ #
    #  Status bar + helpers
    # ------------------------------------------------------------------ #
    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, corner_radius=10, fg_color=("white", "#111a2e"))
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(4, 12))
        self.status_label = ctk.CTkLabel(
            bar, text="Welcome \u2728  Paste a log, then press Anonymize.",
            font=ctk.CTkFont(size=12), text_color=("#475569", "#cbd5e1"),
        )
        self.status_label.pack(side="left", padx=14, pady=6)

    def _set_status(self, msg: str, level: str = "info") -> None:
        colors = {"info": ("#475569", "#cbd5e1"), "ok": ("#059669", "#34d399"),
                  "err": ("#dc2626", "#f87171")}
        self.status_label.configure(text=msg, text_color=colors.get(level, colors["info"]))

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #
    def _toggle_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        new = "light" if mode == "Dark" else "dark"
        ctk.set_appearance_mode(new)
        self._theme_btn.configure(text="\u2600  Dark" if new == "light" else "\u263d  Light")

    def _toggle_mode(self, key: str) -> None:
        self.enabled[key] = bool(self.mode_switches[key].get())

    def _set_strategy(self) -> None:
        v = self._strategy_var.get()
        self.strategy = v if v in (Redactor.STRATEGY_MASK, Redactor.STRATEGY_FULL,
                                   Redactor.STRATEGY_HASH, Redactor.STRATEGY_TOKEN) else Redactor.DEFAULT_STRATEGY

    def _load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open log file",
            filetypes=[("Log / text files", "*.log *.txt *.out *.err"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            return
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", data)
        self._set_status(f"Loaded {os.path.basename(path)} - {len(data):,} chars.", "ok")

    def _paste_clipboard(self) -> None:
        try:
            data = self.clipboard_get()
        except Exception:
            messagebox.showinfo("Clipboard", "Clipboard is empty or not readable.")
            return
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", data)
        self._set_status("Pasted clipboard content.")

    def _start_redact(self) -> None:
        if self._busy:
            return
        text = self.input_box.get("1.0", "end").rstrip("\n")
        if not text.strip():
            messagebox.showinfo("Nothing to do", "Paste or load a log first.")
            return
        self._busy = True
        self.run_btn.configure(state="disabled", text="Working \u2026")
        self.progress.set(0.15)
        threading.Thread(target=self._do_redact, args=(text,), daemon=True).start()

    def _do_redact(self, text: str) -> None:
        try:
            r = Redactor(strategy=self.strategy)
            result = r.redact(text, enabled=dict(self.enabled))
        except Exception as e:
            log("redact error: " + traceback.format_exc())
            self._result_queue.put(("error", text, str(e)))
            return
        self._result_queue.put(("done", text, result))

    def _poll_results(self) -> None:
        """Main-thread drain of worker results (Tk must only be touched here)."""
        drained = False
        while True:
            try:
                kind, original, payload = self._result_queue.get_nowait()
            except queue.Empty:
                break
            drained = True
            if kind == "done":
                self._redact_done(original, payload, None)
            else:
                self._redact_done(original, None, payload)
        if not drained:
            self.after(100, self._poll_results)
        else:
            self.after(50, self._poll_results)

    def _redact_done(self, original: str, result, error: str | None) -> None:
        self._busy = False
        self.run_btn.configure(state="normal", text="\u2694  Anonymize")
        if error:
            self.progress.set(0)
            self._set_status(f"Error: {error}", "err")
            messagebox.showerror("Redaction failed", error)
            return
        self.last_result = result
        self.last_original = original
        self.progress.set(1)
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", result.text)
        top = ", ".join(
            f"{Redactor.MODES[k].label}({v})" for k, v in
            sorted(result.counts.items(), key=lambda kv: -kv[1])[:3]
        ) if result.counts else "nothing"
        self._set_status(f"Redacted {result.total_redactions} items in {result.elapsed_ms:.0f} ms - {top}.", "ok")
        self.stats_label.configure(text=f"{result.total_redactions} items \u00b7 {result.elapsed_ms:.0f} ms")
        if save_html_report:
            self._populate_report_card()

    def _copy_output(self) -> None:
        data = self.output_box.get("1.0", "end").rstrip("\n")
        if not data:
            messagebox.showinfo("Nothing to copy", "Run an anonymization first.")
            return
        self.clipboard_clear()
        self.clipboard_append(data)
        self._set_status("Output copied to clipboard." if data else "Empty output.", "ok")

    # ------------------------------------------------------------------ #
    #  Report downloads
    # ------------------------------------------------------------------ #
    def _report_config(self) -> dict:
        return {"strategy": self.strategy, "enabled": dict(self.enabled)}

    def _download_report(self) -> None:
        if self.last_result is None:
            messagebox.showinfo("No report", "Run an anonymization first.")
            return
        if save_html_report is None:
            messagebox.showerror("Missing module", "core/html_report.py could not be loaded.")
            return
        default = os.path.join(os.path.expanduser("~"), "Desktop",
                               f"anonymization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        path = filedialog.asksaveasfilename(
            title="Save HTML report", defaultextension=".html",
            initialfile=os.path.basename(default),
            filetypes=[("HTML report", "*.html")],
        )
        if not path:
            return
        try:
            save_html_report(self.last_result, self._report_config(), self.last_original, path)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            self._set_status(f"Could not save report: {e}", "err")
            return
        self._set_status(f"Report saved: {path}", "ok")
        if messagebox.askyesno("Report saved", "HTML report saved.\n\nOpen it in your browser now?"):
            try:
                webbrowser.open("file://" + os.path.abspath(path).replace("\\", "/"))
            except Exception:
                pass

    def _open_in_browser(self) -> None:
        if self.last_result is None:
            messagebox.showinfo("No report", "Run an anonymization first.")
            return
        if save_html_report is None:
            messagebox.showerror("Missing module", "core/html_report.py could not be loaded.")
            return
        tmp = os.path.join(os.environ.get("TEMP", "."), "laarp_preview.html")
        try:
            save_html_report(self.last_result, self._report_config(), self.last_original, tmp)
            webbrowser.open("file://" + tmp.replace("\\", "/"))
        except Exception as e:
            messagebox.showerror("Preview failed", str(e))

    def _save_txt(self) -> None:
        data = self.output_box.get("1.0", "end").rstrip("\n")
        if not data:
            messagebox.showinfo("Nothing to save", "Run an anonymization first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save sanitized log",
            defaultextension=".txt",
            initialfile=f"sanitized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            filetypes=[("Log file", "*.log"), ("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self._set_status(f"Saved {os.path.basename(path)}.", "ok")


def main() -> None:
    log(f"{APP_NAME} v{VERSION} starting...")
    app = LogRedactorApp()
    app.mainloop()


if __name__ == "__main__":
    main()