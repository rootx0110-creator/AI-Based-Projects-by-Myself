"""Dashboard: quick stats and primary actions."""

from __future__ import annotations

import customtkinter as ctk

from .. import theme
from .. import widgets as w

ACTION_DEFS = [
    ("Add Sample Files…", "Load PE / script files for analysis"),
    ("Add JSON Report…", "Ingest an exported analysis report"),
    ("Run Full Analysis", "Map indicators to ATT&CK techniques"),
    ("Generate HTML Report…", "Build and download the analytical report"),
    ("Load Demo Data…", "Try the tool with a bundled demonstration sample set"),
]


class DashboardPage:
    def __init__(self, app, frame) -> None:
        self.app = app
        self.frame = frame
        self.kpis = {}
        self.tactic_box = None
        

    def _build(self) -> None:
        outer = ctk.CTkScrollableFrame(self.frame, fg_color=theme.BG)
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        outer.grid_columnconfigure(0, weight=1)

        w.header(outer, "Dashboard", "Profile a threat actor from an analyzed sample set").grid(
            row=0, column=0, sticky="ew", pady=(0, 6))

        kpi_row = ctk.CTkFrame(outer, fg_color="transparent")
        kpi_row.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        for i, (key, label) in enumerate([
            ("samples", "Samples"), ("tech", "Techniques"),
            ("actors", "Actors profiled"), ("iocs", "IOCs"),
        ]):
            kpi_row.grid_columnconfigure(i, weight=1)
            kpi = w.kpi(kpi_row, "0", label)
            kpi.grid(row=0, column=i, padx=5, sticky="ew")
            self.kpis[key] = kpi

        actions_card = w.card(outer, "Quick Actions", row=2, column=0, pady=(0, 12))
        for i, (label, descr) in enumerate(ACTION_DEFS):
            row = ctk.CTkFrame(actions_card.body, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(0, weight=1)
            d = ctk.CTkLabel(row, text=descr, font=ctk.CTkFont(theme.FONT, theme.FS_SMALL),
                             text_color=theme.TEXT_MUTED, anchor="w")
            d.grid(row=0, column=0, sticky="w")
            b = ctk.CTkButton(row, text=label, width=190, height=34, corner_radius=8,
                              fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                              font=ctk.CTkFont(theme.FONT, theme.FS_SMALL, "bold"))
            b.grid(row=0, column=1, sticky="e")
            command = None
            if i == 0:
                command = self.app.page_objects["samples"].add_files_dialog
            elif i == 1:
                command = self.app.page_objects["samples"].add_report_dialog
            elif i == 2:
                command = self.app.run_analysis
            elif i == 3:
                command = self.app.page_objects["reports"].save_report
            else:
                command = self.load_demo
            if command:
                b.configure(command=command)

        status_card = w.card(outer, "Engine Status", row=3, column=0, pady=(0, 12))
        self.status_label = ctk.CTkLabel(status_card.body, text="…", anchor="w", justify="left",
                                         wraplength=900, font=ctk.CTkFont(theme.FONT, theme.FS_BODY),
                                         text_color=theme.TEXT_MUTED)
        self.status_label.grid(row=0, column=0, padx=6, pady=4, sticky="w")

        tactic_card = w.card(outer, "Tactic Coverage", row=4, column=0)
        self.tactic_box = tactic_card.body

        about = ctk.CTkLabel(outer, justify="left", wraplength=900,
                             text_color=theme.TEXT_MUTED, font=ctk.CTkFont(theme.FONT, theme.FS_TINY),
                             text=(
            "Workflow: add analyzed samples (binaries, scripts or prior JSON reports) → "
            "run MITRE ATT&CK mapping → review technique evidence → rank matching threat actors → "
            "export a standalone HTML report.\n\n"
            "Detection sources: PE imports & DLL usage, embedded strings & IOCs, section entropy/packer "
            "traits, and optional YARA classification rules. Mapping matches MITRE ATT&CK meta-techniques; "
            "confidence reflects evidence strength and is for analyst triage only."
        ))
        about.grid(row=5, column=0, padx=6, pady=(14, 0), sticky="w")

    # ------------------------------------------------------------------
    def load_demo(self) -> None:
        self.app.set_status("Loading demonstration dataset…")

        def task():
            return self.app.workbench.load_demo()

        def done(msg: str) -> None:
            self.app.set_status(msg)
            self.app.refresh_all()
            self.app.show_page("dashboard")

        self.app.runner.submit(task, on_done=done,
                               on_error=lambda e: self.app.set_status("Demo load failed: %s" % e))

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        wb = self.app.workbench
        self.kpis["samples"].winfo_children()[0].configure(text=str(len(wb.samples)))
        self.kpis["tech"].winfo_children()[0].configure(text=str(len(wb.techniques)))
        self.kpis["actors"].winfo_children()[0].configure(text=str(len(wb.actors)))
        self.kpis["iocs"].winfo_children()[0].configure(text=str(wb._analysis.iocs_total))

        yara_state = "Native YARA" if wb.yara.is_native else "Pseudo-YARA (yara-python not installed)"
        lines = [
            "YARA engine: %s" % yara_state,
            "Samples loaded: %d   |   Detected techniques: %d   |   Tracked actors upstream: %d" % (
                len(wb.samples), len(wb.techniques), len(wb.actor_db.all_actor_ids())),
        ]
        if wb.yara.error:
            lines.append("Note: %s" % wb.yara.error)
        if wb.samples:
            lines.append("Last result generated: %s" % wb._analysis.generated_at)
        self.status_label.configure(text="\n".join(lines))

        for child in self.tactic_box.winfo_children():
            child.destroy()
        counts = {}
        for t in wb.techniques.values():
            for tac in t.tactics:
                counts[tac] = counts.get(tac, 0) + 1
        if not counts:
            lbl = w.empty_state(self.tactic_box, "No techniques detected yet. Add samples and run analysis.")
            lbl.grid(row=0, column=0, padx=10, pady=8)
            return
        for i, (tac, n) in enumerate(sorted(counts.items(),
                                            key=lambda kv: -kv[1])[:14]):
            row = ctk.CTkFrame(self.tactic_box, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=tac.replace("-", " ").title(), width=200, anchor="w",
                         font=ctk.CTkFont(theme.FONT, theme.FS_SMALL), text_color=theme.TEXT).grid(row=0, column=0)
            bar = ctk.CTkProgressBar(row, width=220, height=12, progress_color=theme.ACCENT,
                                     fg_color=theme.BG_2)
            bar.grid(row=0, column=1, sticky="w")
            mx = max(counts.values())
            bar.set(n / mx if mx else 0)
            ctk.CTkLabel(row, text=str(n), width=40, font=ctk.CTkFont(theme.FONT_MONO, theme.FS_SMALL),
                         text_color=theme.TEXT_MUTED).grid(row=0, column=2, padx=(8, 0))