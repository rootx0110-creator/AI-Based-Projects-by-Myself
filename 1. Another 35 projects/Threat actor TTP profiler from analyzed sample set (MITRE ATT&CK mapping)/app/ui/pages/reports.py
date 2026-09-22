"""Reports page: generate, preview and download the HTML report."""

from __future__ import annotations

import datetime
import os
import tempfile
import webbrowser

import customtkinter as ctk
from tkinter import filedialog, messagebox

from .. import theme
from .. import widgets as w
from ...reports import html_report


class ReportsPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.last_html = None
        

    def _build(self) -> None:
        outer = ctk.CTkScrollableFrame(self.frame, fg_color=theme.BG)
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        outer.grid_columnconfigure(0, weight=1)

        w.header(outer, "Report Generation",
                 "Export a self-contained analytical report (HTML / JSON)").grid(
            row=0, column=0, sticky="ew", pady=(0, 10))

        meta = w.card(outer, "Report Metadata", row=1, column=0, pady=(0, 10))
        meta.grid_columnconfigure(1, weight=1)
        fields = [("analyst", "Analyst"), ("org", "Organization"), ("case_id", "Case / Engagement ID")]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(meta.body, text=label, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                         text_color=theme.TEXT).grid(row=i, column=0, sticky="w", padx=(6, 10), pady=5)
            e = ctk.CTkEntry(meta.body, height=32, corner_radius=6, fg_color=theme.BG_2,
                             border_color=theme.BORDER, text_color=theme.TEXT,
                             placeholder_text=None if label == "Case / Engagement ID" else "—")
            e.grid(row=i, column=1, sticky="ew", padx=6, pady=4)
            self.entries[key] = e

        ctk.CTkLabel(meta.body, text="Report timestamp: %s" % datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"), font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
            text_color=theme.TEXT_MUTED).grid(row=len(fields) + 1, column=0, columnspan=2,
                                              sticky="w", padx=6, pady=(8, 0))

        actions = w.card(outer, "Generate & Export", row=2, column=0, pady=(0, 10))
        for i, (label, descr, cmd, primary) in enumerate([
            ("Generate & Preview in Browser", "Build the HTML report and open it for review",
             self.preview_report, True),
            ("Download HTML Report…", "Save the report as a standalone .html file",
             self.save_report, False),
            ("Export JSON Report…", "Serialize the full analysis for re-import / sharing",
             self.export_json, False),
        ]):
            row = ctk.CTkFrame(actions.body, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=descr, anchor="w", font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                         text_color=theme.TEXT_MUTED).grid(row=0, column=0, sticky="w")
            btn = ctk.CTkButton(row, text=label, width=250, height=36, corner_radius=8,
                                fg_color=theme.ACCENT if primary else "transparent",
                                hover_color=theme.ACCENT_HOVER if primary else theme.FRAME_2,
                                text_color="#ffffff" if primary else theme.TEXT,
                                font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"), command=cmd)
            btn.grid(row=0, column=1, sticky="e")

        status = w.card(outer, "Last Output", row=3, column=0)
        self.status_label = ctk.CTkLabel(status.body, text="No report generated yet.", justify="left",
                                         anchor="w", wraplength=900, font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                                         text_color=theme.TEXT_MUTED)
        self.status_label.grid(row=0, column=0, padx=6, pady=6, sticky="w")

        info = ctk.CTkLabel(outer, justify="left", wraplength=900, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                            text_color=theme.TEXT_MUTED,
                            text="The HTML report is fully self-contained (inline CSS/JS, no external "
                                 "CDN dependencies) and prints cleanly via the browser's Print → Save as "
                                 "PDF. The JSON export preserves the same schema the tool accepts for "
                                 "re-import as an analyzed sample.")
        info.grid(row=4, column=0, padx=6, pady=(12, 0), sticky="w")

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        pass

    def refresh(self) -> None:
        pass

    # ------------------------------------------------------------------
    def _extra(self) -> dict:
        extra = {
            "analyst": self.entries["analyst"].get(),
            "org": self.entries["org"].get(),
            "case_id": self.entries["case_id"].get(),
        }
        if self.app.workbench.yara.error and not self.app.workbench.yara.is_native:
            extra["yara_note"] = "pseudo-yara"
        return extra

    def _build_html(self) -> str:
        return html_report.build_report(self.app.workbench._analysis, self._extra())

    def preview_report(self) -> None:
        if not self.app.workbench.samples:
            messagebox.showinfo("No data", "Load samples before generating a report.")
            return
        html = self._build_html()
        path = os.path.join(tempfile.gettempdir(),
                            "ttp_profiler_preview_%s.html" % datetime.datetime.now().strftime("%H%M%S"))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        self.last_html = (path, html)
        webbrowser.open("file://" + path.replace("\\", "/"))
        self.status_label.configure(text="Report built and opened in browser: %s (%d bytes)" % (
            path, len(html)))
        self.app.set_status("Preview opened.")

    def save_report(self) -> None:
        if not self.app.workbench.samples:
            messagebox.showinfo("No data", "Load samples before generating a report.")
            return
        default_name = "ttp_profile_%s.html" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Save HTML report",
            defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")],
        )
        if not path:
            return
        html = self._build_html()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        self.last_html = (path, html)
        self.status_label.configure(text="Report saved: %s (%d bytes)" % (path, len(html)))
        self.app.set_status("HTML report downloaded.")
        messagebox.showinfo("Report saved", "HTML report written to:\n%s" % path)

    def export_json(self) -> None:
        if not self.app.workbench.samples:
            messagebox.showinfo("No data", "Load samples before exporting.")
            return
        default_name = "ttp_analysis_%s.json" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Export analysis JSON",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        res = self.app.workbench.to_report(path)
        self.status_label.configure(text="JSON analysis exported: %s" % res)
        self.app.set_status("JSON report exported.")