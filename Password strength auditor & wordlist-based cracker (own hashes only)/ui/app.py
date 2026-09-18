"""VaultGuard — Password Strength Auditor & Wordlist-based Hash Cracker."""
from __future__ import annotations

import os
import queue
import sys
import threading
import time
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core import cracker, hashing, report, strength
from core.default_wordlist import ensure_default_wordlist
from core.hashing import ALGORITHMS
from ui.widgets import (
    C,
    CheckRow,
    Header,
    SectionTitle,
    StatCard,
    StatusDot,
    StrengthGauge,
    gradient_color,
)

APP_TITLE = "VaultGuard"
VERSION = "1.0.0"


def resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AuditorPage(ctk.CTkFrame):
    def __init__(self, master, on_report, **kw):
        super().__init__(master, fg_color=C["bg"], **kw)
        self.on_report = on_report
        self.last_audit: dict | None = None
        self._debounce = None

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        SectionTitle(self, "Password Strength Auditor", accent=False).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 10))

        # ---- input card --------------------------------------------------
        input_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                  border_width=1, border_color=C["border"])
        input_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        input_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(input_card, text="Enter a password to analyse — results update live",
                     font=("Segoe UI", 12), text_color=C["muted"]).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 4))

        self.password_var = ctk.StringVar()
        self.password_entry = ctk.CTkEntry(
            input_card, textvariable=self.password_var, show="•",
            font=("Consolas", 15), fg_color="#0f1320", text_color="#ffffff",
            border_color="#2a3242", border_width=1, corner_radius=10,
        )
        self.password_entry.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=(0, 12))
        self.password_var.trace_add("write", lambda *_: self._schedule_audit())

        self.show_var = ctk.BooleanVar(value=False)
        show_cb = ctk.CTkCheckBox(input_card, text="Show", variable=self.show_var,
                                  command=self._toggle_show, font=("Segoe UI", 12),
                                  fg_color=C["accent"], hover_color="#6a4dff",
                                  text_color=C["muted"], checkbox_width=18, checkbox_height=18)
        show_cb.grid(row=1, column=1, padx=4, pady=(0, 12))

        ctk.CTkButton(input_card, text="Clear", width=80, fg_color="#1d2434",
                      hover_color="#26304a", text_color=C["text"],
                      font=("Segoe UI", 12, "bold"), command=self._clear).grid(
            row=1, column=2, padx=(4, 14), pady=(0, 12))

        # ---- gauge + stats ------------------------------------------------
        gauge_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                  border_width=1, border_color=C["border"])
        gauge_card.grid(row=2, column=0, sticky="nsew", padx=(16, 6), pady=(0, 10))
        self.gauge = StrengthGauge(gauge_card, size=228)
        self.gauge.pack(pady=16)

        stats_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                  border_width=1, border_color=C["border"])
        stats_card.grid(row=2, column=1, sticky="nsew", padx=(6, 16), pady=(0, 10))
        stats_card.columnconfigure(0, weight=1)
        stats_card.columnconfigure(1, weight=1)

        ctk.CTkLabel(stats_card, text="Key metrics", font=("Segoe UI", 13, "bold"),
                     text_color=C["text"]).grid(row=0, column=0, columnspan=2,
                                                sticky="w", padx=14, pady=(12, 8))

        self.card_length = StatCard(stats_card, "Length")
        self.card_entropy = StatCard(stats_card, "Entropy")
        self.card_bruteforce = StatCard(stats_card, "Crack time · brute force", accent=C["bad"])
        self.card_dictionary = StatCard(stats_card, "Crack time · dictionary", accent=C["warn"])

        self.card_length.grid(row=1, column=0, sticky="ew", padx=(14, 7), pady=4)
        self.card_entropy.grid(row=1, column=1, sticky="ew", padx=(7, 14), pady=4)
        self.card_bruteforce.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 0))
        self.card_dictionary.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 14))

        # ---- checks + suggestions ----------------------------------------
        checks_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                   border_width=1, border_color=C["border"])
        checks_card.grid(row=3, column=0, sticky="nsew", padx=(16, 6), pady=(0, 10))
        self.check_rows: list[CheckRow] = []

        sug_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                border_width=1, border_color=C["border"])
        sug_card.grid(row=3, column=1, sticky="nsew", padx=(6, 16), pady=(0, 10))
        SectionTitle(sug_card, "Recommendations", accent=True).pack(anchor="w", padx=14, pady=10)
        self.suggestions_text = ctk.CTkTextbox(
            sug_card, height=170, fg_color=C["card2"], border_width=1,
            border_color=C["border"], text_color="#c9d1e2", font=("Segoe UI", 12),
            wrap="word",
        )
        self.suggestions_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.suggestions_text.configure(state="disabled")

        SectionTitle(checks_card, "Checklist", accent=True).pack(anchor="w", padx=14, pady=10)
        self.checks_frame = ctk.CTkFrame(checks_card, fg_color="transparent")
        self.checks_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # report button footer inside page
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=1, sticky="e", padx=16, pady=(0, 8))
        ctk.CTkButton(
            footer, text="Download HTML Report", height=38, font=("Segoe UI", 13, "bold"),
            fg_color=C["accent"], hover_color="#6a4dff", command=self.on_report,
        ).pack(side="right")

        self._audit_now()

    def _toggle_show(self):
        self.password_entry.configure(show="" if self.show_var.get() else "•")

    def _clear(self):
        self.password_var.set("")
        self.password_entry.focus_set()

    def _schedule_audit(self):
        if self._debounce:
            self.after_cancel(self._debounce)
        self._debounce = self.after(220, self._audit_now)

    def _audit_now(self):
        pwd = self.password_var.get()
        result = strength.audit_password(pwd)
        self.last_audit = result
        self._render(result)

    def _render(self, a: dict):
        self.gauge.set(a["score_float"], a["rating"], a["rating_color"])
        self.card_length.value_label.configure(text=str(a["length"]))
        self.card_entropy.value_label.configure(text=f'{a["entropy"]} bits')
        self.card_bruteforce.value_label.configure(text=a["time_estimates"]["bruteforce"])
        self.card_dictionary.value_label.configure(text=a["time_estimates"]["dictionary"])

        for row in self.check_rows:
            row.destroy()
        self.check_rows.clear()
        for c in a["checks"]:
            row = CheckRow(self.checks_frame, c["status"], c["text"])
            row.pack(fill="x", pady=3)
            self.check_rows.append(row)

        self.suggestions_text.configure(state="normal")
        self.suggestions_text.delete("1.0", "end")
        for s in a["suggestions"]:
            self.suggestions_text.insert("end", "•  " + s + "\n")
        self.suggestions_text.configure(state="disabled")


class CrackerPage(ctk.CTkFrame):
    def __init__(self, master, on_report, **kw):
        super().__init__(master, fg_color=C["bg"], **kw)
        self.on_report = on_report
        self.last_result: dict | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._running = False

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        SectionTitle(self, "Wordlist-based Hash Cracker", accent=False).grid(
            row=0, column=0, sticky="w", padx=16, pady=(4, 10))

        # ---- target card ----
        target_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                   border_width=1, border_color=C["border"])
        target_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        target_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(target_card, text="Target hash (your own hash to recover the password)",
                     font=("Segoe UI", 12, "bold"), text_color=C["text"]).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(12, 6))

        self.hash_entry = ctk.CTkTextbox(
            target_card, height=52, fg_color="#0f1320", border_width=1,
            border_color="#2a3242", text_color="#9be1ff", font=("Consolas", 13),
        )
        self.hash_entry.grid(row=1, column=0, columnspan=4, sticky="ew",
                             padx=(14, 14), pady=(0, 8))
        self.hash_entry.bind("<KeyRelease>", lambda _e: self._update_detection())

        self.algo_var = ctk.StringVar(value="Auto-detect")
        algo_menu = ctk.CTkOptionMenu(
            target_card, variable=self.algo_var, values=["Auto-detect", *ALGORITHMS.keys()],
            fg_color="#1d2434", button_color="#283348", button_hover_color="#34425f",
            text_color=C["text"], font=("Segoe UI", 12), dropdown_fg_color="#1d2434",
            dropdown_hover_color="#283348", command=lambda _v: self._update_detection(),
        )
        algo_menu.grid(row=2, column=0, sticky="w", padx=(14, 6), pady=(0, 12))

        self.detect_label = ctk.CTkLabel(target_card, text="Waiting for hash…",
                                         font=("Segoe UI", 12), text_color=C["muted"])
        self.detect_label.grid(row=2, column=1, sticky="w", padx=6)
        ctk.CTkLabel(target_card, text="Generate: " + " · ".join(ALGORITHMS.keys()),
                     font=("Segoe UI", 10), text_color="#5d6678").grid(
            row=2, column=2, columnspan=2, sticky="e", padx=14)

        # ---- wordlist card ----
        wl_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                               border_width=1, border_color=C["border"])
        wl_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        wl_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(wl_card, text="Attack configuration", font=("Segoe UI", 12, "bold"),
                     text_color=C["text"]).grid(row=0, column=0, columnspan=4,
                                                sticky="w", padx=14, pady=(12, 6))

        self.wl_var = ctk.StringVar()
        wl_entry = ctk.CTkEntry(wl_card, textvariable=self.wl_var, font=("Segoe UI", 12),
                                fg_color="#0f1320", text_color="#c9d1e2",
                                border_color="#2a3242", border_width=1)
        wl_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(14, 6), pady=(0, 8))

        ctk.CTkButton(wl_card, text="Browse…", width=88, fg_color="#1d2434",
                      hover_color="#26304a", text_color=C["text"],
                      font=("Segoe UI", 12, "bold"), command=self._browse_wordlist).grid(
            row=1, column=2, padx=4, pady=(0, 8))
        ctk.CTkButton(wl_card, text="Use bundled", width=110, fg_color="#1d2434",
                      hover_color="#26304a", text_color=C["text"],
                      font=("Segoe UI", 12, "bold"), command=self._use_bundled).grid(
            row=1, column=3, padx=(4, 14), pady=(0, 8))

        self.mangle_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(wl_card, text="Mangling rules (capitals, digits, leet, suffixes…)",
                        variable=self.mangle_var, font=("Segoe UI", 12),
                        fg_color=C["accent"], hover_color="#6a4dff",
                        text_color=C["muted"]).grid(row=2, column=0, columnspan=2,
                                                    sticky="w", padx=14, pady=(0, 12))

        ctk.CTkLabel(wl_card, text="Threads", font=("Segoe UI", 12), text_color=C["muted"]).grid(
            row=2, column=2, sticky="e", padx=4, pady=(0, 12))
        self.workers_var = ctk.StringVar(value="8")
        ctk.CTkOptionMenu(
            wl_card, variable=self.workers_var, values=["1", "2", "4", "8", "16"],
            width=80, fg_color="#1d2434", button_color="#283348", button_hover_color="#34425f",
            text_color=C["text"], font=("Segoe UI", 12), dropdown_fg_color="#1d2434",
            dropdown_hover_color="#283348",
        ).grid(row=2, column=3, padx=(4, 14), pady=(0, 12))

        # ---- attack card ----
        atk_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                border_width=1, border_color=C["border"])
        atk_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        atk_card.columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(atk_card, text="▶  Start Attack", width=130, height=38,
                                       font=("Segoe UI", 13, "bold"), fg_color=C["accent"],
                                       hover_color="#6a4dff", command=self._start)
        self.start_btn.grid(row=0, column=0, padx=(14, 6), pady=12)

        self.stop_btn = ctk.CTkButton(atk_card, text="■  Stop", width=100, height=38,
                                      font=("Segoe UI", 13, "bold"), fg_color="#1d2434",
                                      hover_color="#33415c", text_color=C["text"],
                                      state="disabled", command=self._stop_attack)
        self.stop_btn.grid(row=0, column=1, sticky="w", padx=6, pady=12)

        stats_line = ctk.CTkFrame(atk_card, fg_color="transparent")
        stats_line.grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 4))
        self.prog = ctk.CTkProgressBar(stats_line, fg_color="#1d2434",
                                       progress_color=C["accent"], height=12)
        self.prog.set(0)
        self.prog.pack(fill="x", pady=4)

        self.stats_label = ctk.CTkLabel(stats_line, text="Ready.",
                                        font=("Segoe UI", 12), text_color=C["muted"], anchor="w")
        self.stats_label.pack(fill="x", pady=(2, 8))

        # ---- result card ----
        res_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                                border_width=1, border_color=C["border"])
        res_card.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 10))
        res_card.columnconfigure(0, weight=1)
        SectionTitle(res_card, "Identity recovered?", accent=True).pack(anchor="w", padx=14, pady=10)

        self.result_label = ctk.CTkLabel(
            res_card, text="Run an attack to see results here.", font=("Segoe UI", 14),
            text_color=C["muted"], anchor="w", justify="left")
        self.result_label.pack(fill="x", padx=14, pady=(0, 10))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="e", padx=16, pady=(0, 8))
        ctk.CTkButton(
            footer, text="Download HTML Report", height=38, font=("Segoe UI", 13, "bold"),
            fg_color=C["accent"], hover_color="#6a4dff", command=self.on_report,
        ).pack(side="right")

        # default bundled wordlist path
        self._bundled_paths = ensure_default_wordlist([resource_dir(),
                                                       os.path.join(os.path.expanduser("~"), ".vaultguard")])
        if self._bundled_paths and os.path.exists(self._bundled_paths[0]):
            self.wl_var.set(self._bundled_paths[0])

    # ---- helpers -------------------------------------------------------
    def _browse_wordlist(self):
        path = filedialog.askopenfilename(
            title="Select wordlist",
            filetypes=[("Text files", "*.txt"), ("Wordlist", "*.lst"), ("All files", "*.*")])
        if path:
            self.wl_var.set(path)

    def _use_bundled(self):
        if self._bundled_paths and os.path.exists(self._bundled_paths[0]):
            self.wl_var.set(self._bundled_paths[0])

    def _effective_algorithm(self) -> tuple[str, bool]:
        algo = self.algo_var.get()
        target = self.hash_entry.get("1.0", "end-1c").strip()
        if algo == "Auto-detect":
            detected = hashing.detect_algorithm(target)
            if not detected:
                return "MD5", False
            return detected, True
        if algo in ALGORITHMS:
            return algo, True
        return "MD5", False

    def _update_detection(self):
        algo, ok = self._effective_algorithm()
        target = self.hash_entry.get("1.0", "end-1c").strip()
        if not target:
            self.detect_label.configure(text="Waiting for hash…", text_color=C["muted"])
        elif ok:
            self.detect_label.configure(
                text=f"Auto-detected: {algo}  ({ALGORITHMS[algo][0]} hex chars)",
                text_color="#2ecc71")
        else:
            self.detect_label.configure(
                text="Unknown format — not a valid hex digest of the supported algorithms",
                text_color="#ff5c5c")

    def _validate(self) -> tuple[str | None, str | None]:
        target = self.hash_entry.get("1.0", "end-1c").strip()
        if not target:
            return None, "Enter a target hash to attack."
        algo, ok = self._effective_algorithm()
        if not ok or not hashing.is_valid_hash(target, None):
            return None, "The hash must be an even-length hexadecimal string."
        return target, None

    def _start(self):
        if self._running:
            return
        target, err = self._validate()
        if err:
            messagebox.showerror(APP_TITLE, err)
            return
        path = self.wl_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror(APP_TITLE,
                                 "Wordlist file not found.\nChoose a wordlist or use the bundled one.")
            return
        algo, _ = self._effective_algorithm()
        workers = max(1, min(int(self.workers_var.get()), 16))

        self._stop.clear()
        self._queue.queue.clear()
        self._running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.prog.set(0)
        self.stats_label.configure(text="Loading wordlist…", text_color=C["text"])
        self.result_label.configure(text="Attack in progress…", text_color=C["muted"])

        self.last_result = None
        mangling = self.mangle_var.get()
        self._thread = threading.Thread(
            target=self._run_attack, args=(target, algo, path, workers, mangling), daemon=True)
        self._thread.start()
        self.after(120, self._poll)

    def _stop_attack(self):
        self._stop.set()
        self.stats_label.configure(text="Stopping… will halt on next candidate…", text_color=C["warn"])

    def _run_attack(self, target: str, algo: str, path: str, workers: int, mangling: bool):
        try:
            result = cracker.crack(
                target, algo, path,
                mangling=mangling, workers=workers,
                stop_event=self._stop,
                progress_cb=lambda p: self._queue.put(("progress", p)),
            )
            self._queue.put(("done", result))
        except Exception as exc:  # pragma: no cover - defensive
            self._queue.put(("error", exc))

    def _poll(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress":
                    self._render_progress(payload)
                elif kind == "done":
                    self._render_done(payload)
                    return
                elif kind == "error":
                    self._render_error(payload)
                    return
        except queue.Empty:
            pass
        if self._running:
            self.after(120, self._poll)

    def _render_progress(self, p: cracker.CrackProgress):
        total = max(p.total_words, 1)
        self.prog.set(min(p.words_done / total, 1.0))
        self.stats_label.configure(
            text=(f"Words {p.words_done:,} / {p.total_words:,}  ·  Candidates {p.attempts:,}  ·  "
                  f"{p.cps:,.0f} guesses/s  ·  {p.elapsed:,.1f}s"),
            text_color="#c9d1e2")

    def _render_done(self, res: cracker.CrackResult):
        self._running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.last_result = res.__dict__

        if res.errors:
            self.result_label.configure(
                text="Error: " + "; ".join(res.errors), text_color="#ff5c5c")

        if res.found:
            self.result_label.configure(
                text=(f"IDENTITY RECOVERED:  “{res.password}”\n"
                      f"Algorithm {res.algorithm} · {res.attempts:,} candidates tested "
                      f"in {res.elapsed:.2f}s ({res.cps:,.0f} guesses/s)"),
                text_color="#2ecc71")
            self.prog.set(1.0)
        else:
            self.result_label.configure(
                text=(f"Not found in {res.words_done:,} words / {res.attempts:,} candidates "
                      f"({res.elapsed:.1f}s). Try a bigger wordlist or enable mangling rules."),
                text_color="#ffd93d")
        self.stats_label.configure(
            text=(f"Words {res.words_done:,}/{res.total_words:,}  ·  Candidates {res.attempts:,}  ·  "
                  f"{res.cps:,.0f} guesses/s  ·  {res.elapsed:,.1f}s"),
            text_color="#c9d1e2")

    def _render_error(self, exc: Exception):
        self._running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.result_label.configure(text=f"Attack failed: {exc}", text_color="#ff5c5c")
        self.stats_label.configure(text="Failed.", text_color="#ff5c5c")


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title(f"{APP_TITLE} — Password Strength Auditor & Wordlist-based Hash Cracker")
        self.geometry("1180x820")
        self.minsize(1040, 720)
        self.configure(fg_color=C["bg"])

        self._build_chrome()
        self._build_pages()
        self._show_page("auditor")

    def _build_chrome(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        Header(self, APP_TITLE, "Audit password strength · Recover passwords from YOUR OWN hashes",
               badge=f"v{VERSION}", height=88).grid(row=0, column=0, sticky="ew")

        # nav
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        self.nav_auditor = ctk.CTkButton(
            nav, text="🛡  Strength Auditor", width=190, height=34,
            font=("Segoe UI", 13, "bold"), command=lambda: self._show_page("auditor"))
        self.nav_auditor.pack(side="left", padx=(0, 8))
        self.nav_cracker = ctk.CTkButton(
            nav, text="⚡  Hash Cracker", width=170, height=34,
            font=("Segoe UI", 13, "bold"), command=lambda: self._show_page("cracker"))
        self.nav_cracker.pack(side="left")

        # footer status bar
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.status_dot = StatusDot(footer, color="#5d6678")
        self.status_dot.pack(side="left", padx=(2, 8), pady=6)
        self.status_label = ctk.CTkLabel(
            footer, text="Ready — imports of your OWN passwords only. Ethical use only.",
            font=("Segoe UI", 11), text_color=C["muted"], anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)

    def _build_pages(self):
        container = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        container.grid(row=2, column=0, sticky="nsew", padx=0, pady=(8, 0))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.auditor = AuditorPage(container, on_report=lambda: self._save_report())
        self.cracker = CrackerPage(container, on_report=lambda: self._save_report())
        self.auditor.grid(row=0, column=0, sticky="nsew")
        self.cracker.grid(row=0, column=0, sticky="nsew")

    def _show_page(self, which: str):
        if which == "auditor":
            self.auditor.tkraise()
            self.nav_auditor.configure(fg_color=C["accent"], hover_color="#6a4dff", text_color="#ffffff")
            self.nav_cracker.configure(fg_color="#1d2434", hover_color="#26304a", text_color=C["text"])
        else:
            self.cracker.tkraise()
            self.nav_cracker.configure(fg_color=C["accent"], hover_color="#6a4dff", text_color="#ffffff")
            self.nav_auditor.configure(fg_color="#1d2434", hover_color="#26304a", text_color=C["text"])

    def _flash(self, text: str, color: str = "#2ecc71"):
        self.status_label.configure(text=text, text_color=color)
        self.status_dot.set_color(color)

    def _save_report(self):
        audit = self.auditor.last_audit
        crack = self.cracker.last_result
        if not audit and not crack:
            messagebox.showinfo(APP_TITLE,
                                "Nothing to report yet.\nAnalyze a password or run a cracking session first.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"vaultguard_report_{stamp}.html"
        path = filedialog.asksaveasfilename(
            title="Save HTML report", defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")])
        if not path:
            return
        try:
            html_text = report.build_html_report(
                audit, crack,
                title="Password Security Lab Report",
                version=f"{APP_TITLE} v{VERSION}",
            )
            report.save_html_report(path, html_text)
            self._flash(f"Report saved → {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not save report:\n{exc}")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()