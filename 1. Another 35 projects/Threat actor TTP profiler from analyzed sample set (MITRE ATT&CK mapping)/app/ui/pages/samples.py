"""Sample Analysis page: add, inspect and analyze samples."""

from __future__ import annotations

import os

import customtkinter as ctk
from tkinter import filedialog, messagebox

from .. import theme
from .. import widgets as w


class SamplesPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.rows = {}
        self.selected = None
        

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.content = ctk.CTkFrame(self.frame, fg_color=theme.BG)
        self.content.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        self.content.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        # Header stacked above the action buttons: placing them side by side
        # pushed the title past the right edge of the window.
        w.header(top, "Sample Analysis", "Add analyzed samples and inspect static evidence").grid(
            row=0, column=0, sticky="w")

        def btn(parent, text, cmd, variant="ghost"):
            return ctk.CTkButton(
                parent, text=text, height=34, corner_radius=8,
                font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                fg_color=("transparent" if variant == "ghost" else theme.ACCENT),
                text_color=theme.TEXT if variant == "ghost" else "#ffffff",
                hover_color=theme.FRAME_2 if variant == "ghost" else theme.ACCENT_HOVER,
                command=cmd,
            )

        controls = ctk.CTkFrame(top, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="w", pady=(2, 0))
        btn(controls, "Add Files…", self.add_files_dialog, "primary").grid(row=0, column=0, padx=(0, 6))
        btn(controls, "Add Folder…", self.add_folder_dialog).grid(row=0, column=1, padx=6)
        btn(controls, "Add JSON Report…", self.add_report_dialog).grid(row=0, column=2, padx=6)
        btn(controls, "Remove Selected", self.remove_selected).grid(row=0, column=3, padx=6)
        btn(controls, "Clear All", self.clear_all).grid(row=0, column=4, padx=6)

        analyze_row = ctk.CTkFrame(self.content, fg_color="transparent")
        analyze_row.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        analyze_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(analyze_row, text="Batch count: %d" % 0, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                     text_color=theme.TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.count_label = analyze_row.winfo_children()[0]
        self.analyze_btn = btn(analyze_row, "Run Full Analysis", self.app.run_analysis, "primary")
        self.analyze_btn.grid(row=0, column=2, sticky="e", padx=(0, 0))

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)
        self.content.grid_rowconfigure(2, weight=1)

        list_card = w.card(body, "Loaded Samples", row=0, column=0)
        self.scroll = ctk.CTkScrollableFrame(list_card.body, fg_color="transparent", label_text="")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        list_card.grid_rowconfigure(0, weight=1)

        detail = w.card(body, "Sample Details", row=0, column=1)
        detail.grid_columnconfigure(0, weight=1)
        detail.grid_rowconfigure(1, weight=1)
        self.detail_empty = w.empty_state(detail, "Select a sample to inspect its static indicators.")
        self.detail_empty.grid(row=1, column=0, padx=10, pady=10)
        self.detail_tabs = ctk.CTkFrame(detail, fg_color="transparent")
        self.detail_tabs.grid(row=1, column=0, sticky="nsew")
        self.detail_tabs.grid_remove()
        self.detail_tabs.grid_rowconfigure(0, weight=1)
        self.detail_tabs.grid_columnconfigure(0, weight=1)
        self.detail_tabs_displayed = False

        btn_bar = ctk.CTkFrame(detail, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._rebuild_list()
        self.count_label.configure(text="Batch count: %d" % len(self.app.workbench.samples))
        if self.selected is not None:
            self._render_detail(self.selected)

    # ------------------------------------------------------------------
    def _rebuild_list(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self.rows = {}
        for idx, s in enumerate(self.app.workbench.samples):
            self._add_row(idx, s)

    def _add_row(self, idx, s) -> None:
        state = "error: %s" % s.error if s.error else ""
        row = ctk.CTkFrame(self.scroll, fg_color=theme.FRAME_2, corner_radius=8)
        row.grid(row=len(self.rows), column=0, sticky="ew", padx=2, pady=4)
        row.grid_columnconfigure(1, weight=1)
        badge = "ERR" if s.error else (s.packer or s.file_type.upper())
        chip = ctk.CTkLabel(row, text=badge, width=92, fg_color=(theme.BAD if s.error else theme.FRAME),
                            corner_radius=5, font=ctk.CTkFont(theme.FONT, theme.FS_TINY, "bold"),
                            text_color=(theme.TEXT if not s.error else "#ffffff"))
        chip.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=8, sticky="n")
        name = ctk.CTkLabel(row, text=s.filename, anchor="w", font=ctk.CTkFont(theme.FONT, theme.FS_BODY, "bold"),
                            text_color=theme.TEXT)
        name.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(7, 0))
        meta = "%s · %s · %s" % (s.archive if hasattr(s, "archive") else (s.machine or s.file_type),
                                  s.sha256[:12], state or "analyzed")
        meta_lbl = ctk.CTkLabel(row, text=meta, anchor="w", font=ctk.CTkFont(theme.FONT_MONO, theme.FS_TINY),
                                text_color=theme.TEXT_MUTED)
        meta_lbl.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(0, 7))

        def select(_e=None, ridx=idx):
            self.selected = ridx
            self._render_detail(ridx)
            self.app.set_status("Inspecting %s" % self.app.workbench.samples[ridx].filename)

        row.bind("<Button-1>", select)
        for ch in (chip, name, meta_lbl):
            ch.bind("<Button-1>", select)
        self.rows[idx] = row

    # ------------------------------------------------------------------
    def _render_detail(self, idx: int) -> None:
        if not (0 <= idx < len(self.app.workbench.samples)):
            return
        s = self.app.workbench.samples[idx]
        if not self.detail_tabs_displayed:
            self.detail_empty.grid_remove()
            self.detail_tabs.grid()
            self.detail_tabs_displayed = True

        for child in self.detail_tabs.winfo_children():
            child.destroy()

        summary = ctk.CTkFrame(self.detail_tabs, fg_color="transparent")
        summary.pack(fill="both", expand=False, pady=(0, 8))

        rows = [
            ("File", s.filename),
            ("Path", s.filepath),
            ("Type / Arch", "%s / %s" % (s.file_type or "?", s.architecture or "?")),
            ("Size", "%s bytes" % s.size_bytes),
            ("MD5", s.md5 or "—"),
            ("SHA-1", s.sha1 or "—"),
            ("SHA-256", s.sha256 or "—"),
            ("Compile time", s.compile_time or "—"),
            ("Entropy (max section)", "%.4f" % s.entropy if s.entropy else "—"),
            ("Packer signature", s.packer or "none detected"),
        ]
        for i, (k, v) in enumerate(rows):
            ctk.CTkLabel(summary, text=k + ":", width=170, anchor="w",
                         font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"),
                         text_color=theme.TEXT).grid(row=i, column=0, sticky="w", padx=(2, 10), pady=2)
            ctk.CTkLabel(summary, text=v, anchor="w", font=ctk.CTkFont(theme.FONT_MONO, theme.FS_MONO_SM),
                         text_color=theme.TEXT, wraplength=560, justify="left").grid(
                row=i, column=1, sticky="w", pady=2)

        self._detail_text = ctk.CTkTextbox(self.detail_tabs, fg_color=theme.BG_2,
                                           text_color=theme.TEXT, corner_radius=8,
                                           font=ctk.CTkFont(theme.FONT_MONO, theme.FS_MONO), height=260)
        self._detail_text.pack(fill="both", expand=True)
        content = self._compose_detail(s)
        self._detail_text.insert("1.0", content)
        self._detail_text.configure(state="disabled")

        self.app.set_status("Inspecting %s" % s.filename)

    @staticmethod
    def _compose_detail(s) -> str:
        lines = []
        lines.append("— Sections —")
        if s.sections:
            for sec in s.sections:
                lines.append("  %-10s vsize=0x%x raw=0x%x entropy=%.3f %s%s" % (
                    sec.get("name", ""), sec.get("vsize", 0), sec.get("rawsize", 0),
                    sec.get("entropy", 0), "X" if sec.get("exec") else ".",
                    "W" if sec.get("write") else "."))
        else:
            lines.append("  (none)")

        lines.append("\n— Imports (%d) —" % len(s.imports))
        lines.extend("  " + i for i in s.imports[:120])

        lines.append("\n— Strings (%d shown of %d) —" % (min(len(s.strings), 160), len(s.strings)))
        lines.extend("  " + st for st in s.strings[:160])

        if s.yara_hits:
            lines.append("\n— YARA hits —")
            lines.extend("  " + r for r in s.yara_hits)
        if s.iocs:
            lines.append("\n— IOCs —")
            seen = set()
            for ioc in s.iocs:
                key = (ioc["type"], ioc["name"])
                if key in seen:
                    continue
                seen.add(key)
                lines.append("  [%s] %s" % (ioc["type"], ioc["name"]))
        if s.notes:
            lines.append("\n— Notes —")
            lines.extend("  " + n for n in s.notes)
        if s.error:
            lines.append("\n— ERROR — %s" % s.error)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def add_files_dialog(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select analyzed samples",
            filetypes=[("Analysis targets", "*.*"), ("PE executables", "*.exe *.dll *.scr *.cpl"),
                       ("Scripts", "*.ps1 *.vbs *.js *.bat *.cmd *.py"), ("Archives", "*.zip *.rar *.7z")])
        if not paths:
            return
        self.app.set_status("Analyzing %d file(s)…" % len(paths))

        def task():
            added = [self.app.workbench.add_file(p) for p in paths]
            return added

        def done(result):
            n_ok = sum(1 for s in result if not s.error)
            self.app.set_status("Added %d/%d files." % (n_ok, len(result)))
            self.app.run_analysis()

        self.app.runner.submit(task, on_done=done,
                               on_error=lambda e: messagebox.showerror("Analysis error", str(e)))

    def add_folder_dialog(self) -> None:
        folder = filedialog.askdirectory(title="Select a folder of samples")
        if not folder:
            return
        paths = []
        for root, _dirs, files in os.walk(folder):
            for fn in files:
                paths.append(os.path.join(root, fn))

        self.app.set_status("Analyzing %d file(s)…" % len(paths))

        def task():
            return [self.app.workbench.add_file(p) for p in paths]

        def done(result):
            n_ok = sum(1 for s in result if not s.error)
            self.app.set_status("Added %d/%d files from folder." % (n_ok, len(result)))
            self.app.run_analysis()

        self.app.runner.submit(task, on_done=done,
                               on_error=lambda e: messagebox.showerror("Analysis error", str(e)))

    def add_report_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Import a JSON analysis report",
            filetypes=[("JSON reports", "*.json"), ("All files", "*.*")])
        if not path:
            return

        def task():
            return self.app.workbench.load_report(path)

        def done(sample):
            self.app.set_status("Imported report: %s" % sample.filename)
            self.app.run_analysis()

        self.app.runner.submit(task, on_done=done,
                               on_error=lambda e: messagebox.showerror(
                                   "Import error", "Could not parse report:\n%s" % e))

    def remove_selected(self) -> None:
        if self.selected is None or not self.app.workbench.samples:
            return
        self.app.workbench.remove_at(self.selected)
        self.selected = None
        self.app.run_analysis()

    def clear_all(self) -> None:
        if self.app.workbench.samples and not messagebox.askyesno(
                "Clear all samples", "Remove all loaded samples?"):
            return
        self.app.workbench.reset()
        self.selected = None
        self.app.refresh_all()