import csv
import io
import os
import threading

import customtkinter as ctk
from tkinter import filedialog

from ..reporter import build_html, build_json_str, build_txt
from .theme import ACCENT, BG, CRIT, MUTED, OK, TEXT, WARN, FONT_FAMILY
from .widgets import build_btn, build_label, card


class ReportsView(ctk.CTkFrame):
    """Generate and download security reports (HTML / JSON / TXT / CSV)."""

    def __init__(self, master, agent):
        super().__init__(master, fg_color=BG)
        self.agent = agent
        self.last_path = None
        self._busy = False
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 8))
        build_label(header, "Reports", size=22, weight="bold").pack(side="left")
        build_label(header, "download system, integrity and event reports", size=12,
                    color=MUTED).pack(side="left", padx=12, pady=8)

        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # ---- full report card ----
        full = card(body, title="Full Security Report", accent=ACCENT)
        full.pack(fill="x", pady=4)
        text = ctk.CTkFrame(full, fg_color="transparent")
        text.pack(fill="x", padx=14, pady=(6, 0))
        build_label(text, """Includes host snapshot (CPU, memory, uptime), module status,
watched directories, alert summary, recent security events and the most
active processes.""", size=11, color=MUTED).pack(anchor="w")
        row = ctk.CTkFrame(full, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(8, 12))
        build_label(row, "Format", size=12).pack(side="left")
        self.full_fmt = ctk.CTkComboBox(
            row, values=["HTML", "JSON", "TXT"], width=120, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly")
        self.full_fmt.set("HTML")
        self.full_fmt.pack(side="left", padx=10)
        build_btn(row, "Download Report", self._download_full, primary=True).pack(side="left")

        # ---- events log export card ----
        events = card(body, title="Security Events Export", accent=ACCENT)
        events.pack(fill="x", pady=(8, 4))
        text2 = ctk.CTkFrame(events, fg_color="transparent")
        text2.pack(fill="x", padx=14, pady=(6, 0))
        build_label(text2, "Export the alert log, optionally filtered by severity and source.",
                    size=11, color=MUTED).pack(anchor="w")
        row2 = ctk.CTkFrame(events, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(8, 12))
        build_label(row2, "Severity", size=12).pack(side="left")
        self.ev_sev = ctk.CTkComboBox(
            row2, values=["All", "Critical", "Warning", "Info"], width=110, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly")
        self.ev_sev.set("All")
        self.ev_sev.pack(side="left", padx=6)

        build_label(row2, "Source", size=12).pack(side="left", padx=(10, 0))
        self.ev_src = ctk.CTkComboBox(
            row2, values=["All", "fim", "process", "agent"], width=110, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly")
        self.ev_src.set("All")
        self.ev_src.pack(side="left", padx=6)

        build_label(row2, "Format", size=12).pack(side="left", padx=(10, 0))
        self.ev_fmt = ctk.CTkComboBox(
            row2, values=["CSV", "JSON", "TXT"], width=110, height=28,
            fg_color="#141a24", border_color="#2a3444", text_color=TEXT,
            dropdown_fg_color="#161b22", dropdown_text_color=TEXT,
            button_color=ACCENT, button_hover_color=ACCENT, state="readonly")
        self.ev_fmt.set("CSV")
        self.ev_fmt.pack(side="left", padx=6)
        build_btn(row2, "Download Log", self._download_events).pack(side="left", padx=8)

        # ---- save status + open ----
        savecard = card(body, title="Downloaded Files")
        savecard.pack(fill="x", pady=(8, 4))
        row3 = ctk.CTkFrame(savecard, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=10)
        self.status = build_label(savecard, "No file downloaded yet.", size=12, color=MUTED)
        self.status.pack(anchor="w", padx=14, pady=(0, 0))
        self.open_btn = build_btn(row3, "Open Last Download", self._open_last)
        self.open_btn.pack(side="left", pady=(0, 10))
        build_label(row3, "Reports are generated from live data and saved to disk.",
                    size=10, color=MUTED).pack(side="right", pady=(0, 10))

    # ---------------- actions ----------------
    def _default_name(self, prefix, ext):
        import time
        stamp = time.strftime("%Y%m%d-%H%M%S")
        return f"{prefix}-{stamp}.{ext}"

    def _save(self, path, data, enc="utf-8"):
        with open(path, "w", encoding=enc, newline="") as fh:
            fh.write(data)
        self.last_path = path
        self.status.configure(text=f"Saved -> {path}", text_color=OK)

    def _download_full(self):
        fmt = self.full_fmt.get()
        ext = fmt.lower()
        path = filedialog.asksaveasfilename(
            title="Save security report",
            defaultextension=f".{ext}",
            initialfile=self._default_name("hids-report", ext),
            filetypes=[(f"{fmt} document", f"*.{ext}")])
        if not path:
            return
        self._run(lambda: self._build_full(fmt), lambda data: self._save(path, data))

    def _build_full(self, fmt):
        if fmt == "JSON":
            return build_json_str(self.agent)
        if fmt == "TXT":
            return build_txt(self.agent)
        return build_html(self.agent)

    def _download_events(self):
        sev = self.ev_sev.get()
        src = self.ev_src.get()
        fmt = self.ev_fmt.get()
        ext = {"CSV": "csv", "JSON": "json", "TXT": "txt"}[fmt]
        path = filedialog.asksaveasfilename(
            title="Save alerts log",
            defaultextension=f".{ext}",
            initialfile=self._default_name("hids-alerts", ext),
            filetypes=[(f"{fmt} file", f"*.{ext}")])
        if not path:
            return
        self._run(lambda: self._build_events(fmt, sev, src),
                  lambda data: self._save(path, data))

    def _build_events(self, fmt, sev, src):
        min_sev = {"All": 1, "Info": 1, "Warning": 2, "Critical": 3}[sev]
        source = None if src == "All" else src
        rows = self.agent.storage.alerts(min_severity=min_sev, source=source,
                                         limit=10000)
        import time as _t
        if fmt == "CSV":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["time", "severity", "source", "status", "title", "detail"])
            for r in rows:
                w.writerow([
                    _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(r["ts"])),
                    {1: "Info", 2: "Warning", 3: "Critical"}[r["severity"]],
                    r["source"], r["status"], r["title"], r["detail"] or ""])
            return buf.getvalue()
        if fmt == "JSON":
            import json
            return json.dumps({
                "generated": _t.strftime("%Y-%m-%d %H:%M:%S"),
                "filter": {"severity": sev, "source": src},
                "count": len(rows),
                "alerts": [dict(row) for row in rows],
            }, indent=2, default=str)
        # TXT
        lines = [f"Security events  generated={_t.strftime('%Y-%m-%d %H:%M:%S')}",
                 f"filter  severity={sev}  source={src}  rows={len(rows)}",
                 "=" * 70]
        for r in rows:
            lines.append(
                f"[{_t.strftime('%Y-%m-%d %H:%M:%S', _t.localtime(r['ts']))}] "
                f"{r['severity']} {r['source']:<7} {r['status']:<5} "
                f"{r['title']} - {r['detail']}")
        return "\n".join(lines)

    def _open_last(self):
        if self.last_path and os.path.exists(self.last_path):
            try:
                os.startfile(self.last_path)  # noqa: S606  (Windows only)
            except Exception as exc:
                self.status.configure(text=f"Could not open: {exc}", text_color=CRIT)
        else:
            self.status.configure(text="Nothing to open yet.", text_color=WARN)

    def _run(self, work, done):
        if self._busy:
            return
        self._busy = True
        self.status.configure(text="Generating report...", text_color=ACCENT)

        def runner():
            try:
                data = work()
                self.after(0, lambda: self._done(done, data))
            except Exception as exc:
                self.after(0, lambda: self._fail(str(exc)))

        threading.Thread(target=runner, daemon=True).start()

    def _done(self, done, data):
        self._busy = False
        try:
            done(data)
        except Exception as exc:
            self.status.configure(text=f"Save failed: {exc}", text_color=CRIT)
        else:
            self.status.configure(text="Report ready.", text_color=OK)

    def _fail(self, err):
        self._busy = False
        self.status.configure(text=f"Generation failed: {err}", text_color=CRIT)

    def refresh(self):
        pass