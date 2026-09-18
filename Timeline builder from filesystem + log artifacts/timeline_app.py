import csv
import datetime as dt
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from timeline_core import (EVENT_TYPES, Scanner, TimelineEvent, build_stats,
                           filter_events)
from timeline_report import TYPE_LABELS, build_html_report

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_LIGHT = "#f4f5fb"
BG_DARK = "#121316"
TREE_LIGHT = {"bg": "#ffffff", "head": "#eef0f8", "fg": "#1f2430",
              "headfg": "#374151", "row": "#f5f6fe"}
TREE_DARK = {"bg": "#1c1e23", "head": "#262a33", "fg": "#e8eaf2",
             "headfg": "#cdd2e0", "row": "#34405c"}

FONT = "Segoe UI"
MONO = "Consolas"


def meter_bytes(n):
    if n is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return "{:.1f} {}".format(n, unit) if unit != "B" else "{} B".format(int(n))
        n /= 1024.0
    return "-"


def num(n):
    return format(int(n or 0), ",")


class TimelineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Builder - Filesystem & Log Artifacts")
        self.geometry("1280x820")
        self.minsize(1120, 720)

        self.all_events = []
        self.stats = None
        self.scanning = False
        self._busy = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        self._build_ui()
        self._apply_style()
        self._center()

    def _palette(self):
        if ctk.get_appearance_mode() == "Dark":
            return BG_DARK, TREE_DARK
        return BG_LIGHT, TREE_LIGHT

    def _build_ui(self):
        self.bg, self._tree_theme = self._palette()

        header = ctk.CTkFrame(self, corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Timeline Builder",
                     font=(FONT, 20, "bold")).grid(row=0, column=0,
                                                   padx=(20, 4), pady=(14, 0),
                                                   sticky="w")
        ctk.CTkLabel(header, text="reconstruct activity from files and logs",
                     font=(FONT, 12), text_color=("gray55", "gray60")).grid(
            row=0, column=0, padx=(170, 4), pady=(20, 0), sticky="w")
        self.theme_btn = ctk.CTkButton(
            header, text="Light" if ctk.get_appearance_mode() == "Dark" else "Dark",
            width=70, height=30, command=self._toggle_theme)
        self.theme_btn.grid(row=0, column=1, padx=18, pady=16)

        ctk.CTkFrame(self, height=2, corner_radius=0).grid(row=1, column=0,
                                                           sticky="ew")

        toolbar = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=20, pady=(16, 6))
        toolbar.columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            toolbar, placeholder_text="Choose a folder to analyse...",
            font=(FONT, 13), border_color=("gray70", "gray35"))
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10),
                             ipady=4)
        self.browse_btn = ctk.CTkButton(
            toolbar, text="Choose Folder", width=130, height=36,
            command=self._pick_folder)
        self.browse_btn.grid(row=0, column=1, padx=(0, 8))
        self.scan_btn = ctk.CTkButton(
            toolbar, text="Scan", width=110, height=36,
            fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"),
            font=(FONT, 13, "bold"), command=self._start_scan)
        self.scan_btn.grid(row=0, column=2)
        self.clear_btn = ctk.CTkButton(
            toolbar, text="Clear", width=80, height=36, fg_color="transparent",
            border_width=1, command=self._clear)
        self.clear_btn.grid(row=0, column=3, padx=8)

        opts = ctk.CTkFrame(self, corner_radius=12)
        opts.grid(row=3, column=0, sticky="ew", padx=20, pady=6)
        opt_wrap = ctk.CTkFrame(opts, fg_color="transparent")
        opt_wrap.grid(row=0, column=0, sticky="w", padx=14, pady=10)
        self.inc_accessed = ctk.CTkCheckBox(
            opt_wrap, text="Collect 'accessed'", font=(FONT, 12))
        self.inc_accessed.select()
        self.inc_accessed.grid(row=0, column=0, padx=(0, 14))
        self.parse_logs = ctk.CTkCheckBox(
            opt_wrap, text="Parse log files", font=(FONT, 12))
        self.parse_logs.select()
        self.parse_logs.grid(row=0, column=1, padx=(0, 14))
        ctk.CTkLabel(opt_wrap, text="Filter types:",
                     font=(FONT, 12)).grid(row=0, column=2, padx=(10, 4))
        self.type_vars = {}
        for i, t in enumerate(EVENT_TYPES):
            var = tk.BooleanVar(value=True)
            self.type_vars[t] = var
            ctk.CTkCheckBox(opt_wrap, text=TYPE_LABELS.get(t, t),
                            variable=var, font=(FONT, 12)).grid(
                row=0, column=3 + i, padx=(0, 10))
        ctk.CTkLabel(opt_wrap, text="From:", font=(FONT, 12)).grid(
            row=0, column=3 + len(EVENT_TYPES), padx=(14, 4))
        self.from_entry = ctk.CTkEntry(opt_wrap, placeholder_text="YYYY-MM-DD",
                                       width=110, font=(FONT, 12))
        self.from_entry.grid(row=0, column=4 + len(EVENT_TYPES), padx=(0, 8))
        ctk.CTkLabel(opt_wrap, text="To:", font=(FONT, 12)).grid(
            row=0, column=5 + len(EVENT_TYPES), padx=(4, 4))
        self.to_entry = ctk.CTkEntry(opt_wrap, placeholder_text="YYYY-MM-DD",
                                     width=110, font=(FONT, 12))
        self.to_entry.grid(row=0, column=6 + len(EVENT_TYPES), padx=(0, 10))
        self.apply_btn = ctk.CTkButton(
            opt_wrap, text="Apply", width=80, height=30, command=self._refresh)
        self.apply_btn.grid(row=0, column=7 + len(EVENT_TYPES))

        metrics = ctk.CTkFrame(self, corner_radius=12)
        metrics.grid(row=4, column=0, sticky="ew", padx=20, pady=6)
        for c in range(6):
            metrics.columnconfigure(c, weight=1, uniform="m")
        self.m = {k: None for k in
                  ("events", "files", "dirs", "logs", "lines", "span")}
        titles = [("events", "Events"), ("files", "Files"),
                  ("dirs", "Folders"), ("logs", "Log files"),
                  ("lines", "Log lines"), ("span", "Time span")]
        for c, (key, lbl) in enumerate(titles):
            cell = ctk.CTkFrame(metrics, corner_radius=10)
            cell.grid(row=0, column=c, sticky="ew", padx=7, pady=12)
            val = ctk.CTkLabel(cell, text="-", font=(FONT, 22, "bold"),
                               text_color=("#4f46e5", "#818cf8"))
            val.pack(pady=(12, 0))
            ctk.CTkLabel(cell, text=lbl, font=(FONT, 12),
                         text_color=("gray50", "gray55")).pack(pady=(0, 12))
            self.m[key] = val

        body = ctk.CTkFrame(self, corner_radius=12)
        body.grid(row=5, column=0, sticky="nsew", padx=20, pady=6)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            body, columns=("time", "type", "source", "path", "details", "size"),
            show="headings", selectmode="browse", style="Timeline.Treeview")
        cols = [("time", "Time", 165, "w"),
                ("type", "Type", 90, "w"),
                ("source", "Source", 140, "w"),
                ("path", "Path", 440, "w"),
                ("details", "Details", 400, "w"),
                ("size", "Size", 95, "e")]
        for cid, text, width, anchor in cols:
            self.tree.heading(cid, text="  " + text, anchor=anchor)
            self.tree.column(cid, width=width, anchor=anchor,
                             minwidth=60, stretch=(cid in ("path", "details")))
        vs = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(body, orient="horizontal",
                           command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        vs.grid(row=0, column=1, sticky="ns", pady=10)
        hs.grid(row=1, column=0, sticky="ew", padx=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        detail = ctk.CTkFrame(body, width=320, corner_radius=10)
        detail.grid(row=0, column=2, sticky="ns", padx=10, pady=10)
        detail.grid_propagate(False)
        ctk.CTkLabel(detail, text="Event details", font=(FONT, 13, "bold"),
                     text_color=("#4f46e5", "#818cf8")).pack(
            anchor="w", padx=14, pady=(12, 6))
        self.detail_box = ctk.CTkScrollableFrame(detail, width=290)
        self.detail_box.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        self._detail_rows = {}
        for key, lbl in [("time", "Time"), ("type", "Type"),
                         ("source", "Source"), ("path", "Path"),
                         ("details", "Details"), ("size", "Size")]:
            box = ctk.CTkFrame(self.detail_box, corner_radius=8)
            box.pack(fill="x", pady=3)
            ctk.CTkLabel(box, text=lbl, font=(FONT, 11, "bold"),
                         text_color=("gray55", "gray60")).pack(
                anchor="w", padx=10, pady=(6, 0))
            lab = ctk.CTkLabel(box, text="-", font=(FONT, 12), justify="left",
                               wraplength=250, anchor="w")
            lab.pack(anchor="w", padx=10, pady=(0, 7))
            self._detail_rows[key] = lab
        self._clear_detail()

        bar = ctk.CTkFrame(self, corner_radius=12)
        bar.grid(row=6, column=0, sticky="ew", padx=20, pady=(6, 16))
        bar.columnconfigure(1, weight=1)
        self.progress = ctk.CTkProgressBar(bar, width=220,
                                           mode="indeterminate")
        self.progress.grid(row=0, column=0, padx=(14, 12), pady=12)
        self.progress.set(0)
        self.status = ctk.CTkLabel(bar, text="Ready. Choose a folder and press Scan.",
                                   font=(FONT, 12), anchor="w")
        self.status.grid(row=0, column=1, sticky="w")
        self.html_btn = ctk.CTkButton(
            bar, text="Export HTML Report", width=170, height=34,
            fg_color=("#0f766e", "#14b8a6"), hover_color=("#115e59", "#0d9488"),
            font=(FONT, 13, "bold"), command=self._export_html)
        self.html_btn.grid(row=0, column=2, padx=(0, 8))
        self.csv_btn = ctk.CTkButton(
            bar, text="Export CSV", width=120, height=34, fg_color="transparent",
            border_width=1, command=self._export_csv)
        self.csv_btn.grid(row=0, column=3, padx=(0, 14))

    def _apply_style(self):
        t = self._tree_theme
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Timeline.Treeview",
                        background=t["bg"], fieldbackground=t["bg"],
                        foreground=t["fg"], rowheight=28,
                        borderwidth=0, font=(FONT, 10))
        style.configure("Timeline.Treeview.Heading",
                        background=t["head"], foreground=t["headfg"],
                        relief="flat", font=(FONT, 10, "bold"), padding=(6, 7))
        style.map("Timeline.Treeview",
                  background=[("selected", t["row"])],
                  foreground=[("selected", t["fg"])])
        style.map("Timeline.Treeview.Heading",
                  background=[("active", t["head"])])
        vs = ttk.Style(self)
        vs.theme_use("clam")
        vs.configure("Vertical.TScrollbar", background=t["head"],
                     troughcolor=self.bg, bordercolor=self.bg, arrowcolor=t["fg"])
        vs.configure("Horizontal.TScrollbar", background=t["head"],
                     troughcolor=self.bg, bordercolor=self.bg, arrowcolor=t["fg"])

    def _toggle_theme(self):
        mode = "Dark" if ctk.get_appearance_mode() == "Dark" else "Light"
        ctk.set_appearance_mode(mode)
        mode = ctk.get_appearance_mode()
        self.theme_btn.configure(
            text="Light" if mode == "Dark" else "Dark")
        self._apply_style()

    def _center(self):
        self.update_idletasks()
        self.update()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = max(40, (self.winfo_screenheight() - h) // 2)
        self.geometry("+{}+{}".format(x, y))

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Select folder to analyse")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

    def _start_scan(self):
        if self.scanning:
            return
        root = self.path_entry.get().strip()
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Timeline Builder",
                                   "Please choose a valid folder first.")
            return
        self._set_busy(True)
        self.status.configure(text="Scanning in progress...")
        self.progress.start()
        sc = Scanner(include_accessed=self.inc_accessed.get(),
                     parse_logs=self.parse_logs.get())

        def work():
            try:
                events, stats = sc.scan(root, progress=self._on_progress_thread)
                stats = build_stats(events, stats)
                self.after(0, lambda: self._scan_done(events, stats))
            except Exception as exc:
                self.after(0, lambda: self._scan_failed(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_progress_thread(self, msg):
        try:
            self.after(0, lambda: self.status.configure(text=msg))
        except Exception:
            pass

    def _scan_done(self, events, stats):
        self.progress.stop()
        self.progress.set(0)
        self._set_busy(False)
        self.all_events = events
        self.stats = stats
        self.from_entry.delete(0, "end")
        self.to_entry.delete(0, "end")
        self.m["events"].configure(text=num(len(events)))
        self.m["files"].configure(text=num(stats.get("files")))
        self.m["dirs"].configure(text=num(stats.get("dirs")))
        self.m["logs"].configure(text=num(stats.get("log_files")))
        self.m["lines"].configure(text=num(stats.get("log_lines")))
        span = stats.get("span_days", 0.0)
        if span and span < 1:
            self.m["span"].configure(text="{} hr".format(int(span * 24)))
        else:
            self.m["span"].configure(text="{} day{}".format(
                int(span), "s" if int(span) != 1 else ""))
        self._refresh()
        self.status.configure(
            text="Scan complete: {} events from {} files / {} log lines.".format(
                num(len(events)), num(stats.get("files")),
                num(stats.get("log_lines"))))
        if not events:
            messagebox.showinfo(
                "Timeline Builder",
                "The scan completed but no timeline events were found.\n"
                "Try enabling 'Collect accessed' or 'Parse log files'.")

    def _scan_failed(self, exc):
        self.progress.stop()
        self.progress.set(0)
        self._set_busy(False)
        self.status.configure(text="Scan failed.")
        messagebox.showerror("Timeline Builder",
                             "Scan failed:\n{}".format(exc))

    def _set_busy(self, busy):
        self.scanning = busy
        state = "disabled" if busy else "normal"
        for w in (self.browse_btn, self.scan_btn, self.clear_btn,
                  self.html_btn, self.csv_btn, self.apply_btn):
            w.configure(state=state)
        if busy:
            self.status.configure(text_color=("#4f46e5", "#818cf8"))

    def _selected_types(self):
        return [t for t in EVENT_TYPES if self.type_vars[t].get()]

    def _date_value(self, entry):
        s = entry.get().strip()
        if not s:
            return None
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None

    def _filtered(self):
        start = self._date_value(self.from_entry)
        end = self._date_value(self.to_entry)
        if end is not None:
            end = end + dt.timedelta(days=1)
        types = self._selected_types()
        return types, start, end

    def _refresh(self):
        types, start, end = self._filtered()
        self.tree.delete(*self.tree.get_children())
        events = filter_events(self.all_events, types=types, start=start,
                               end=end)
        if len(events) > 200000:
            events = events[:200000]
        for e in events:
            self.tree.insert("", "end", values=(
                e.ts.strftime("%Y-%m-%d %H:%M:%S"),
                TYPE_LABELS.get(e.type, e.type),
                e.source,
                e.path,
                e.details,
                meter_bytes(e.size),
            ), tags=(e.type,))
        for t in EVENT_TYPES:
            self.tree.tag_configure(t)
        self.status.configure(
            text="Showing {} of {} events.".format(num(len(events)),
                                                   num(len(self.all_events))))

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        vals = self.tree.item(iid, "values")
        if vals:
            self._show_detail(*vals)

    def _show_detail(self, time, etype, source, path, details, size):
        for key, val in (("time", time), ("type", etype), ("source", source),
                         ("path", path), ("details", details), ("size", size)):
            lab = self._detail_rows[key]
            lab.configure(text=val if val else "-")
            if not val and key == "path":
                lab.configure(text="(none)")

    def _clear_detail(self):
        for lab in self._detail_rows.values():
            lab.configure(text="-")
        ctk.CTkLabel(self.detail_box, text="Select an event row to see its "
                                           "full details here.",
                     font=(FONT, 12), text_color=("gray50", "gray55"),
                     wraplength=250, justify="left").pack(
            anchor="w", padx=6, pady=10)

    def _clear(self):
        if self.scanning:
            return
        self.tree.delete(*self.tree.get_children())
        self.all_events = []
        self.stats = None
        self.path_entry.delete(0, "end")
        self.from_entry.delete(0, "end")
        self.to_entry.delete(0, "end")
        for var in self.type_vars.values():
            var.set(True)
        for m in self.m.values():
            m.configure(text="-")
        self._clear_detail()
        self.status.configure(text="Ready. Choose a folder and press Scan.")
        self.html_btn.configure(state="normal")
        self.csv_btn.configure(state="normal")

    def _export_html(self):
        if not self.all_events:
            messagebox.showinfo("Timeline Builder",
                                "Nothing to export. Scan a folder first.")
            return
        types, start, end = self._filtered()
        events = filter_events(self.all_events, types=types, start=start, end=end)
        if not events:
            messagebox.showinfo("Timeline Builder",
                                "Current filter selects no events.")
            return
        path = filedialog.asksaveasfilename(
            title="Download HTML report",
            defaultextension=".html",
            initialfile="timeline_report.html",
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")])
        if not path:
            return
        try:
            merged = dict(self.stats)
            merged["total"] = len(events)
            merged["counts"] = build_stats(events)["counts"]
            html = build_html_report(events, merged,
                                     options={"title": "Timeline Report - "
                                                       + os.path.basename(
                                                           self.path_entry.get())})
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
        except Exception as exc:
            messagebox.showerror("Timeline Builder",
                                 "Export failed:\n{}".format(exc))
            return
        self.status.configure(text="HTML report saved: " + path)
        if messagebox.askyesno("Timeline Builder",
                               "HTML report saved.\nOpen it now?"):
            os.startfile(path)

    def _export_csv(self):
        if not self.all_events:
            messagebox.showinfo("Timeline Builder",
                                "Nothing to export. Scan a folder first.")
            return
        types, start, end = self._filtered()
        events = filter_events(self.all_events, types=types, start=start, end=end)
        if not events:
            messagebox.showinfo("Timeline Builder",
                                "Current filter selects no events.")
            return
        path = filedialog.asksaveasfilename(
            title="Export timeline as CSV", defaultextension=".csv",
            initialfile="timeline.csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(["time", "type", "source", "path", "details",
                                 "size_bytes"])
                for e in events:
                    writer.writerow([e.ts.strftime("%Y-%m-%d %H:%M:%S"),
                                     e.type, e.source, e.path, e.details,
                                     e.size if e.size is not None else ""])
        except Exception as exc:
            messagebox.showerror("Timeline Builder",
                                 "Export failed:\n{}".format(exc))
            return
        self.status.configure(text="CSV saved: " + path)
        if messagebox.askyesno("Timeline Builder",
                               "CSV saved.\nOpen it now?"):
            os.startfile(path)


def run():
    app = TimelineApp()
    app.mainloop()