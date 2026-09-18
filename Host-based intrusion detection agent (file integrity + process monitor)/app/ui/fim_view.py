import threading

import customtkinter as ctk
from tkinter import filedialog

from .theme import ACCENT, BG, CARD, CRIT, MUTED, OK, PANEL, TEXT, WARN, FONT_FAMILY
from .widgets import build_btn, build_label, card, clear_tree, make_scrollbar, make_tree


class FIMView(ctk.CTkFrame):
    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self.last_results = {}
        self._busy = False
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        build_label(header, "File Integrity Monitor", size=22, weight="bold").pack(side="left")
        build_label(header, "detect added, modified and removed files", size=12,
                    color=MUTED).pack(side="left", padx=12, pady=8)

        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # left: watched dirs
        left = card(body, title="Watched Directories", accent=ACCENT)
        left.grid(row=0, column=0, sticky="nsew", padx=6)
        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=8)
        build_btn(bar, "+ Add Directory", self._add_dir, primary=True).pack(side="left")
        build_btn(bar, "Remove", self._remove_dir).pack(side="left", padx=6)
        self._job_info = build_label(bar, "", size=11, color=MUTED)
        self._job_info.pack(side="right")

        self.dir_tree = make_tree(left, ["path", "files", "status"],
                                  [420, 90, 130], height=12)
        make_scrollbar(left, self.dir_tree)
        self.dir_tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 10))
        self.scan_btn = build_btn(actions, "Scan Selected Now", self._scan_selected)
        self.scan_btn.pack(side="left")
        self.baseline_btn = build_btn(actions, "Build Baseline", self._build_baseline_selected)
        self.baseline_btn.pack(side="left", padx=6)

        # right: results
        right = card(body, title="Last Scan Results")
        right.grid(row=0, column=1, sticky="nsew", padx=6)
        self.res_bar = ctk.CTkProgressBar(right, height=8, progress_color=OK,
                                          fg_color="#141a24", corner_radius=4)
        self.res_bar.pack(fill="x", padx=14, pady=(8, 2))
        self.res_state = build_label(right, "Select a directory and run a scan.", size=12,
                                     color=MUTED)
        self.res_state.pack(anchor="w", padx=14, pady=(0, 4))

        tabs = ctk.CTkTabview(right, fg_color=CARD, segmented_button_fg_color=PANEL,
                              text_color=MUTED,
                              segmented_button_selected_color=ACCENT,
                              segmented_button_unselected_hover_color=PANEL)
        tabs.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        results = {}
        for key, label in [("added", f"Added"), ("modified", "Modified"), ("removed", "Removed")]:
            t = tabs.add(label)
            tree = make_tree(t, ["file"], [520], height=10)
            make_scrollbar(t, tree)
            tree.pack(fill="both", expand=True, padx=6, pady=6)
            results[key] = tree
        self.result_trees = results
        self.result_tabview = tabs

    # ---------- dir management ----------
    def _add_dir(self):
        path = filedialog.askdirectory(title="Select directory to protect")
        if not path:
            return
        try:
            added = self.agent.add_watch_dir(path)
        except ValueError as exc:
            self._job_info.configure(text=str(exc), text_color=CRIT)
            return
        if added:
            self._job_info.configure(text="Added - baseline will be built on next cycle",
                                     text_color=OK)
        else:
            self._job_info.configure(text="Already watched", text_color=WARN)
        self.refresh()

    def _remove_dir(self):
        sel = self.dir_tree.selection()
        if not sel:
            return
        path = self.dir_tree.item(sel[0], "values")[0]
        self.agent.remove_watch_dir(path)
        self.refresh()

    def _selected_dirs(self):
        sel = self.dir_tree.selection()
        if sel:
            return [self.dir_tree.item(i, "values")[0] for i in sel]
        return self.agent.watch_dirs()

    def _scan_selected(self):
        self._run_jobs("scan", self._selected_dirs())

    def _build_baseline_selected(self):
        self._run_jobs("baseline", self._selected_dirs())

    # ---------- background job (sequential over multiple dirs) ----------
    def _run_jobs(self, kind, dirs):
        dirs = [d for d in dirs if d]
        if not dirs or self._busy:
            return
        self._busy = True
        self.scan_btn.configure(state="disabled")
        self.baseline_btn.configure(state="disabled")
        total = len(dirs)

        def cb(processed, total_files, curr):
            self.after(0, lambda: self._update_progress(kind, processed, total_files, curr))
            return False

        def work():
            for idx, d in enumerate(dirs, 1):
                self.after(0, lambda i=idx: self._job_info.configure(
                    text=f"{kind} {i}/{total}: {os.path.basename(d)}", text_color=MUTED))
                try:
                    if kind == "baseline":
                        res = self.agent.fim.build_baseline(d, progress_cb=cb)
                        self.after(0, lambda r=res, p=d: self._finish_job_baseline(p, r))
                    else:
                        ch = self.agent.fim.scan(d, progress_cb=cb)
                        self.after(0, lambda c=ch, p=d: self._finish_job_scan(p, c))
                except Exception as exc:
                    self.after(0, lambda e=str(exc), p=d: self._job_failed(p, e))
            self.after(0, lambda: (self._unbusy(),
                                   self._job_info.configure(
                                       text=f"{kind} complete for {total} director{'y' if total == 1 else 'ies'}",
                                       text_color=OK)))

        threading.Thread(target=work, daemon=True).start()

    def _update_progress(self, kind, processed, total_files, curr):
        self.res_bar.set(processed / max(total_files, 1))
        label = (f"Building baseline: {processed}/{total_files}"
                 if kind == "baseline" else f"Scanning: {processed}/{total_files}")
        if curr:
            label += f"  {curr}"
        self.res_state.configure(text=label, text_color=TEXT)

    def _finish_job_baseline(self, d, res):
        self.res_bar.set(1.0)
        self.res_state.configure(
            text=f"Baseline created for {d}: {res.total} files ({res.skipped} skipped)",
            text_color=OK)

    def _finish_job_scan(self, d, ch):
        label = (f"{d} - clean ({ch.unchanged} unchanged)"
                 if ch.changed == 0 else
                 f"{d} - {len(ch.added)} added, {len(ch.modified)} modified, {len(ch.removed)} removed")
        self.res_state.configure(
            text=label,
            text_color=OK if ch.changed == 0 else WARN)
        self._populate_results(ch)

    def _job_failed(self, d, err):
        self.res_bar.set(0)
        self.res_state.configure(text=f"Job failed for {d}: {err}", text_color=CRIT)

    def _unbusy(self):
        self._busy = False
        self.scan_btn.configure(state="normal")
        self.baseline_btn.configure(state="normal")

    def _populate_results(self, ch):
        data = {"added": ch.added, "modified": ch.modified, "removed": ch.removed}
        for key, tree in self.result_trees.items():
            clear_tree(tree)
            for rel in data[key]:
                tag = {"added": "sev_2", "modified": "sev_2", "removed": "sev_3"}[key]
                tree.insert("", "end", values=(rel,), tags=(tag,))

    # ---------- periodic refresh ----------
    def refresh(self):
        rows = []
        for d in self.agent.watch_dirs():
            try:
                n = self.agent.storage.baseline_file_count(d)
            except Exception:
                n = 0
            status = "Baseline" if n else "Pending baseline"
            rows.append((d, n, status))
        clear_tree(self.dir_tree)
        for d, n, s in rows:
            self.dir_tree.insert("", "end",
                                 values=(d, n, s),
                                 tags=("ok" if n else "hl",))