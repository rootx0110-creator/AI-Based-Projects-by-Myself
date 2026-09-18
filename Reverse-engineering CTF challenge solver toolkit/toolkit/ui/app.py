"""Main window: sidebar navigation + page switching + HTML report export."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core import encodings, entropy, fileinfo, frequency, hexdump, strings
from ..report.htmlreport import build_file_report, build_solver_report
from .pages import (CaesarPage, EncodePage, EntropyPage, FileInfoPage,
                    FrequencyPage, HexPage, HomePage, StringsPage,
                    VigenerePage, XorPage)
from .widgets import MONO, ResultBox, Toolbar, Worker, ghost_button, primary_button

NAV = [
    ("Home", "\u2302"),
    ("File", "\U0001F4C4"),
    ("Strings", "\u220F"),
    ("Hex", "#"),
    ("Entropy", "\u2211"),
    ("Frequency", "\U0001F4CA"),
    ("Encodings", "\u21C4"),
    ("XOR", "\u2295"),
    ("Caesar", "\u21BB"),
    ("Vigenere", "\U0001F511"),
    ("Report", "\U0001F4E4"),
]


class SolverApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("RE CTF Challenge Solver Toolkit")
        self.geometry("1180x760")
        self.minsize(960, 620)

        self.current_path: str | None = None
        self.current_bytes: bytes | None = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = self._build_sidebar()
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        self.topbar = self._build_topbar()
        self.topbar.grid(row=0, column=0, sticky="ew")

        self.stack = ctk.CTkFrame(self.content, fg_color="transparent")
        self.stack.grid(row=1, column=0, sticky="nsew")
        self.stack.grid_columnconfigure(0, weight=1)
        self.stack.grid_rowconfigure(0, weight=1)

        self.pages: dict[str, ctk.CTkFrame] = {}
        self._build_pages()
        self.nav["Home"].invoke()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- UI build

    def _build_sidebar(self) -> ctk.CTkFrame:
        sb = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color="#0d1017")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkLabel(sb, text="\U0001F50E  RE-Toolkit", font=ctk.CTkFont(size=17, weight="bold"),
                            text_color="#2dd4bf", anchor="w")
        logo.grid(row=0, column=0, padx=16, pady=(18, 4), sticky="ew")
        sub = ctk.CTkLabel(sb, text="CTF solver toolkit", font=ctk.CTkFont(size=11),
                           text_color="#5d6678", anchor="w")
        sub.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")

        self.nav: dict[str, ctk.CTkButton] = {}
        row = 2
        for name, icon in NAV:
            b = ctk.CTkButton(
                sb, text=f"  {icon}  {name}", anchor="w",
                height=34, corner_radius=8,
                fg_color="transparent", hover_color="#161c2b",
                text_color="#a7b6d0", font=ctk.CTkFont(size=13),
                command=lambda n=name: self.goto(n),
            )
            b.grid(row=row, column=0, padx=10, pady=2, sticky="ew")
            self.nav[name] = b
            row += 1

        open_btn = primary_button(sb, "Open File", self.open_file)
        open_btn.grid(row=row, column=0, padx=14, pady=(18, 4), sticky="ew")
        hint = ctk.CTkLabel(sb, text="Load a binary/challenge file to\ntriage and solve.",
                            font=ctk.CTkFont(size=10), text_color="#5d6678", justify="left")
        hint.grid(row=row + 1, column=0, padx=16, pady=(0, 0), sticky="w")

        self.status = ctk.CTkLabel(sb, text="No file loaded",
                                   font=ctk.CTkFont(size=11), text_color="#facc15", wraplength=180,
                                   justify="left", anchor="w")
        self.status.grid(row=row + 3, column=0, padx=16, pady=(14, 14), sticky="ew")
        return sb

    def _build_topbar(self) -> ctk.CTkFrame:
        tb = ctk.CTkFrame(self.content, height=56, corner_radius=0, fg_color="#0d1017")
        tb.grid_propagate(False)
        tb.grid_columnconfigure(0, weight=1)
        self.file_lbl = ctk.CTkLabel(tb, text="No file loaded", font=ctk.CTkFont(size=13),
                                     text_color="#8b93a5", anchor="w")
        self.file_lbl.grid(row=0, column=0, padx=18, sticky="w")
        self.report_btn = ghost_button(tb, "Download HTML Report", self.goto_report)
        self.report_btn.grid(row=0, column=1, padx=14)
        return tb

    def _build_pages(self) -> None:
        makers = [
            ("Home", HomePage),
            ("File", FileInfoPage),
            ("Strings", StringsPage),
            ("Hex", HexPage),
            ("Entropy", EntropyPage),
            ("Frequency", FrequencyPage),
            ("Encodings", EncodePage),
            ("XOR", XorPage),
            ("Caesar", CaesarPage),
            ("Vigenere", VigenerePage),
        ]
        for name, cls in makers:
            page = cls(self.stack, self)
            page.grid(row=0, column=0, sticky="nsew", padx=18, pady=14)
            self.pages[name] = page
        self.pages["Report"] = ReportPage(self.stack, self)
        self.pages["Report"].grid(row=0, column=0, sticky="nsew", padx=18, pady=14)

    # ------------------------------------------------------------- actions

    def goto(self, name: str) -> None:
        for key, page in self.pages.items():
            if key == name:
                page.grid()
                self.nav[key].configure(fg_color="#0f1b26", text_color="#2dd4bf")
            else:
                page.grid_remove()
                if key in self.nav:
                    self.nav[key].configure(fg_color="transparent", text_color="#a7b6d0")

    def goto_report(self, *_):
        self.goto("Report")

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open challenge file",
            filetypes=[("All files", "*.*"), ("Binaries", "*.exe *.bin *.out"), ("Images", "*.png *.jpg"),
                       ("Archives", "*.zip *.gz *.zst")],
        )
        if not path:
            return
        try:
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))
            return
        self.current_path = path
        self.current_bytes = data
        self.file_lbl.configure(text=f"{os.path.basename(path)}   \u00b7   {size:,} bytes")
        self.status.configure(text=f"Loaded: {os.path.basename(path)} ({size:,} bytes)",
                              text_color="#4ade80")
        self.goto("File")

    def _on_close(self):
        self.destroy()


class ReportPage(ctk.CTkFrame):
    """Collects current analysis results and exports an HTML report."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.tb = Toolbar(self, "HTML Report Export",
                          "Generate a self-contained analysis report and save it in HTML format")
        self.tb.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.checks: dict[str, ctk.CTkCheckBox] = {}
        for i, (key, label) in enumerate([
            ("file", "File metadata & hashes"),
            ("strings", "Strings"),
            ("entropy", "Entropy"),
            ("hex", "Hex dump"),
            ("freq", "Letter frequency"),
            ("findings", "Notable findings"),
        ]):
            cb = ctk.CTkCheckBox(opts, text=label, onvalue=1, offvalue=0)
            cb.select()
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=4)
            self.checks[key] = cb

        self.box = ResultBox(self, height=10)
        self.box.grid(row=3, column=0, sticky="nsew", pady=(6, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        primary_button(btns, "Generate & Download HTML", self.generate).pack(side="left")
        ghost_button(btns, "Open report after save", self._toggle_default).pack(side="left", padx=8)
        self.open_after = tk.BooleanVar(value=True)

    def _toggle_default(self, *_):
        self.open_after.set(not self.open_after.get())

    def _selected(self, key: str) -> bool:
        return bool(self.checks.get(key).get()) if key in self.checks else True

    def generate(self, *_):
        if not self.app.current_bytes:
            messagebox.showinfo("No data", "Load a challenge file first.")
            return
        self.box.clear()
        self.box.write("Building report...", "info")
        Worker(self, self._build, self._finished)

    def _build(self):
        data = self.app.current_bytes
        info = fileinfo.FileInfo(self.app.current_path)
        info_d = info.info()
        info_d["extra"] = fileinfo.deep_header_info(data)

        strings_d = strings.extract(data, min_len=5, include_unicode=True) if self._selected("strings") else None
        entropy_d = entropy.file_entropy(data) if self._selected("entropy") else None
        hex_d = hexdump.generate(data, 16)[:220] if self._selected("hex") else None
        freq_d = frequency.letter_histogram(data) if self._selected("freq") else None

        findings = []
        if strings_d:
            flags = [s["value"] for s in strings_d if "flag{" in s["value"].lower() or "ctf{" in s["value"].lower()]
            if flags:
                findings.append(f"{len(flags)} flag-like string(s) found: {', '.join(flags[:4])}")
            httpl = [s for s in strings_d if "http://" in s["value"] or "https://" in s["value"]]
            if httpl:
                findings.append(f"{len(httpl)} URL(s) embedded.")
        if entropy_d and entropy_d["overall"] > 6.5:
            findings.append("Overall entropy is very high - payload is likely packed or encrypted.")
        if info_d.get("extra", {}).get("pe_type"):
            findings.append("Windows PE binary detected - consider disassembly in a debugger/IDA/Ghidra.")
        if info_d.get("extra", {}).get("elf_label"):
            findings.append(f"ELF binary detected ({info_d['extra']['elf_label']}).")

        html = build_file_report(info_d, strings_d, entropy_d, hex_d, freq_d,
                                 findings if self._selected("findings") else [])
        return info_d, html

    def _finished(self, result, err):
        if err is not None:
            self.box.clear()
            self.box.write(f"Build failed: {err}", "bad")
            return
        info_d, html = result
        default = f"{os.path.splitext(os.path.basename(self.app.current_path))[0]}_report.html"
        path = filedialog.asksaveasfilename(
            title="Download HTML report",
            defaultextension=".html",
            initialfile=default,
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")],
        )
        if not path:
            self.box.write("Export cancelled.", "dim")
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
        except OSError as exc:
            self.box.write(f"Save failed: {exc}", "bad")
            return
        self.box.clear()
        self.box.write(f"Report saved: {path}", "ok")
        if self.open_after.get():
            try:
                os.startfile(path)  # type: ignore[attr-defined]
                self.box.write("Opened in your browser.", "text")
            except OSError:
                pass