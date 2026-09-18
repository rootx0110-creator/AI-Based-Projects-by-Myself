"""Wizard, Reports, Settings, and Training Log views for SeaSim."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, ttk
from typing import List, Optional

from seasim import constants as C
from seasim.engine import models as M
from seasim.reports import (
    build_html_report, build_text_report, campaign_stats, dept_csv,
    department_breakdown, events_csv, program_totals,
)
from seasim.safety import validate_recipients
from seasim.templates import builtin_templates
from seasim.ui import theme as T
from seasim.ui.dialogs import (
    confirm, error, info, prompt_string, show_text, warn,
)
from seasim.ui.views import ViewBase, ViewContext


# ---------------------------------------------------------------------------
# New Campaign wizard (7 steps, consent-gated finish)
# ---------------------------------------------------------------------------

class WizardView(ViewBase):
    STEPS = ["Name", "Template", "Recipients", "Mode", "Schedule",
             "Review", "Finish"]

    def build(self) -> None:
        self.wiz_frame: Optional[tk.Frame] = None
        self.step = 0
        self.name = tk.StringVar(
            value=f"Awareness run {datetime.now():%Y-%m-%d}")
        self.tpl_id: Optional[str] = None
        self.sel_pids: List[str] = []
        self.mode = tk.StringVar(value=M.MODE_INTERNAL)
        self.rate = tk.IntVar(value=min(self.ctx.store.settings.default_rate,
                                        C.RATE_PER_MINUTE))
        self.sched_mode = tk.StringVar(value="immediate")
        self.sched_date = tk.StringVar(value="")
        self.ack = tk.StringVar(value="")
        self.final = tk.BooleanVar(value=False)  # kept for compatibility

        self.header = tk.Frame(self, bg=T.BG)
        self.header.pack(fill="x", padx=28, pady=(24, 0))
        self.body = tk.Frame(self, bg=T.BG)
        self.body.pack(fill="both", expand=True, padx=28, pady=8)
        self.footer = tk.Frame(self, bg=T.BG)
        self.footer.pack(fill="x", padx=28, pady=(0, 18))
        self._show_step()

    # -- scaffolding ------------------------------------------------------

    def _steps_bar(self) -> None:
        for w in self.header.winfo_children():
            w.destroy()
        tk.Label(self.header, text="New Campaign",
                 bg=T.BG, fg=T.INK, font=(T.FONT, 20, "bold")).pack(
            anchor="w")
        bar = tk.Frame(self.header, bg=T.BG)
        bar.pack(anchor="w", pady=(6, 0))
        for i, label in enumerate(self.STEPS):
            active = i == self.step
            done = i < self.step
            chip = tk.Label(
                bar, text=f" {i + 1} {label} ",
                fg="white" if active else (T.SAFE_FG if done else T.MUTED),
                bg=T.ACCENT if active else (T.SAFE_BG if done else "#e2e8f0"),
                font=(T.FONT, 9, "bold"))
            chip.pack(side="left", padx=(0, 6), pady=2)

    def _clear_body(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()
        self.footer.destroy()
        self.footer = tk.Frame(self, bg=T.BG)
        self.footer.pack(fill="x", padx=28, pady=(0, 18))

    def _nav_buttons(self, on_back: bool, next_label: str = "Next >",
                     next_cmd=None) -> None:
        if on_back:
            ttk.Button(self.footer, text="< Back",
                       command=self._back).pack(side="left")
        ttk.Button(self.footer, text=next_label, style="Accent.TButton",
                   command=next_cmd or self._next).pack(side="right")

    def _show_step(self) -> None:
        self._steps_bar()
        self._clear_body()
        getattr(self, f"_step{self.step}")()

    def _next(self) -> None:
        validator = getattr(self, f"_validate{self.step}", None)
        if validator is not None and not validator():
            return
        if self.step < len(self.STEPS) - 1:
            self.step += 1
            self._show_step()

    def _back(self) -> None:
        if self.step > 0:
            self.step -= 1
            self._show_step()

    # -- step 0: name -------------------------------------------------------

    def _step0(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Campaign name", bg=T.CARD,
                 fg=T.INK, font=(T.FONT, 12, "bold")).pack(anchor="w",
                                                           padx=18,
                                                           pady=(16, 4))
        tk.Label(card, text="Use a neutral, non-alarming name - e.g. "
                            "'Q3 awareness wave'.", bg=T.CARD, fg=T.MUTED,
                 font=(T.FONT, 9)).pack(anchor="w", padx=18)
        tk.Entry(card, textvariable=self.name, font=(T.FONT, 12),
                 bg="white").pack(fill="x", padx=18, pady=12)
        self._nav_buttons(False, "Next >")

    def _validate0(self) -> bool:
        if not self.name.get().strip():
            warn(self, "SeaSim", "Give the campaign a name.")
            return False
        return True

    # -- step 1: template -------------------------------------------------

    def _step1(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Choose the awareness template",
                 bg=T.CARD, fg=T.INK, font=(T.FONT, 12, "bold")).pack(
            anchor="w", padx=18, pady=(16, 8))
        self.tpl_list = sorted(self.ctx.store.templates.values(),
                               key=lambda t: (t.category, t.name.lower()))
        self.tpl_box = tk.Listbox(card, font=(T.FONT, 10), bg="white",
                                  activestyle="dotbox", height=12)
        for t in self.tpl_list:
            self.tpl_box.insert("end",
                                f"{t.name}   [{t.category}, "
                                f"difficulty {t.difficulty}]")
        self.tpl_box.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        if self.tpl_id:
            for i, t in enumerate(self.tpl_list):
                if t.id == self.tpl_id:
                    self.tpl_box.selection_set(i)
        hint = tk.Label(card, text="AI-themed templates require an extra "
                                   "consent checkbox at authorization.",
                        bg=T.CARD, fg=T.MUTED, font=(T.FONT, 9))
        hint.pack(anchor="w", padx=18, pady=(0, 12))
        self._nav_buttons(True)

    def _validate1(self) -> bool:
        sel = self.tpl_box.curselection()
        if not sel:
            warn(self, "SeaSim", "Select a template.")
            return False
        self.tpl_id = self.tpl_list[sel[0]].id
        return True

    # -- step 2: recipients -------------------------------------------------

    def _step2(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        head = tk.Frame(card, bg=T.CARD)
        head.pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(head, text="Select recipients (internal staff only)",
                 bg=T.CARD, fg=T.INK,
                 font=(T.FONT, 12, "bold")).pack(side="left")
        self.count_lbl = tk.Label(head, text="", bg=T.CARD, fg=T.MUTED,
                                  font=(T.FONT, 10, "bold"))
        self.count_lbl.pack(side="right")

        pane = tk.Frame(card, bg=T.CARD)
        pane.pack(fill="both", expand=True, padx=18, pady=8)
        self.p_tree = ttk.Treeview(pane, columns=("name", "dept", "email"),
                                   show="headings", selectmode="extended")
        for cid, txt, w in (("name", "Name", 160), ("dept", "Dept", 110),
                            ("email", "Email", 220)):
            self.p_tree.heading(cid, text=txt)
            self.p_tree.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(pane, orient="vertical", command=self.p_tree.yview)
        self.p_tree.configure(yscrollcommand=sb.set)
        self.p_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        active = [p for p in self.ctx.store.participants_sorted() if p.active]
        for p in active:
            self.p_tree.insert("", "end", iid=p.id,
                               values=(p.name, p.department, p.email))
        for pid in self.sel_pids:
            if pid in self.ctx.store.participants:
                try:
                    self.p_tree.selection_add(pid)
                except tk.TclError:
                    pass
        self.p_tree.bind("<<TreeviewSelect>>", lambda e: self._upd_count())
        self._upd_count()

        quick = tk.Frame(card, bg=T.CARD)
        quick.pack(fill="x", padx=18, pady=(0, 12))
        ttk.Button(quick, text="Select all",
                   command=lambda: [self.p_tree.selection_add(i) for i in
                                    self.p_tree.get_children()]
                   ).pack(side="left", padx=2)
        ttk.Button(quick, text="Clear",
                   command=lambda: self.p_tree.selection_set([])).pack(
            side="left", padx=2)
        self._nav_buttons(True)

    def _upd_count(self) -> None:
        n = len(self.p_tree.selection())
        cap = f" / {C.MAX_RECIPIENTS} cap"
        warn_n = f"  (>{C.WARN_RECIPIENTS} requires extra confirmation)" \
            if n > C.WARN_RECIPIENTS else ""
        self.count_lbl.config(text=f"{n} selected{cap}{warn_n}")

    def _validate2(self) -> bool:
        self.sel_pids = list(self.p_tree.selection())
        if not self.sel_pids:
            warn(self, "SeaSim", "Select at least one recipient.")
            return False
        ok, why = validate_recipients(self.sel_pids, self.ctx.store)
        if not ok:
            error(self, "Recipients rejected", why)
            return False
        if len(self.sel_pids) > C.WARN_RECIPIENTS:
            if not confirm(self, "Large launch",
                           f"{len(self.sel_pids)} recipients exceeds "
                           f"{C.WARN_RECIPIENTS}. Continue?"):
                return False
        return True

    # -- step 3: mode --------------------------------------------------------

    def _step3(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Delivery mode", bg=T.CARD,
                 fg=T.INK, font=(T.FONT, 12, "bold")).pack(anchor="w",
                                                           padx=18,
                                                           pady=(16, 4))
        for val, desc in (
            (M.MODE_INTERNAL, "Email links to the built-in simulation page. "
                              "Simplest and fully contained in-app."),
            (M.MODE_TRACKED_LINK, "Tracked link - records the click event on "
                                  "a local landing stub. Nothing external."),
        ):
            rb = ttk.Radiobutton(card, text=val, value=val,
                                 variable=self.mode)
            rb.pack(anchor="w", padx=18, pady=(8, 0))
            tk.Label(card, text="   " + desc, bg=T.CARD, fg=T.MUTED,
                     font=(T.FONT, 9), wraplength=600,
                     justify="left").pack(anchor="w")

        tk.Label(card, text="Send rate (per minute, capped at "
                            f"{C.RATE_PER_MINUTE})", bg=T.CARD, fg=T.INK,
                 font=(T.FONT, 10, "bold")).pack(anchor="w", padx=18,
                                                 pady=(18, 2))
        tk.Spinbox(card, from_=1, to=C.RATE_PER_MINUTE,
                   textvariable=self.rate, width=8,
                   font=(T.FONT, 11)).pack(anchor="w", padx=18)
        self._nav_buttons(True)

    def _validate3(self) -> bool:
        try:
            r = int(self.rate.get())
        except Exception:
            r = C.RATE_PER_MINUTE
        if r < 1 or r > C.RATE_PER_MINUTE:
            warn(self, "SeaSim", f"Rate must be 1-{C.RATE_PER_MINUTE}.")
            return False
        self.rate.set(r)
        return True

    # -- step 4: schedule ------------------------------------------------------

    def _step4(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Schedule", bg=T.CARD,
                 fg=T.INK, font=(T.FONT, 12, "bold")).pack(anchor="w",
                                                           padx=18,
                                                           pady=(16, 4))
        ttk.Radiobutton(card, text="Launch immediately after authorization",
                        value="immediate", variable=self.sched_mode).pack(
            anchor="w", padx=18, pady=(8, 0))
        rb2 = ttk.Radiobutton(card, text="Schedule for a later date",
                              value="later", variable=self.sched_mode)
        rb2.pack(anchor="w", padx=18, pady=(6, 0))
        row = tk.Frame(card, bg=T.CARD)
        row.pack(anchor="w", padx=18, pady=6)
        tk.Label(row, text="Date (YYYY-MM-DD HH:MM)", bg=T.CARD, fg=T.MUTED,
                 font=(T.FONT, 9)).pack(side="left")
        default = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        self.sched_entry = tk.Entry(row, font=(T.FONT, 10), width=20,
                                    bg="white")
        self.sched_entry.insert(0, self.sched_date.get() or default)
        self.sched_entry.pack(side="left", padx=8)
        tk.Label(card, text="Scheduled drafts surface on the dashboard when "
                            "due - they still require authorization before "
                            "anything is sent.", bg=T.CARD, fg=T.MUTED,
                 font=(T.FONT, 9), wraplength=600,
                 justify="left").pack(anchor="w", padx=18, pady=(10, 12))
        self._nav_buttons(True)

    def _validate4(self) -> bool:
        if self.sched_mode.get() == "immediate":
            self.sched_date.set("")
            return True
        raw = self.sched_entry.get().strip()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                self.sched_date.set(dt.isoformat(timespec="minutes"))
                return True
            except ValueError:
                continue
        warn(self, "SeaSim", "Enter the date as YYYY-MM-DD HH:MM.")
        return False

    # -- step 5: review ---------------------------------------------------------

    def _step5(self) -> None:
        tpl = self.ctx.store.templates.get(self.tpl_id or "")
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Review before authorization",
                 bg=T.CARD, fg=T.INK, font=(T.FONT, 12, "bold")).pack(
            anchor="w", padx=18, pady=(16, 8))
        rows = [
            ("Name", self.name.get().strip()),
            ("Template", tpl.name if tpl else "(none)"),
            ("Category / difficulty",
             f"{tpl.category} / {tpl.difficulty}" if tpl else "-"),
            ("Recipients", f"{len(self.sel_pids)} internal participants"),
            ("Mode", self.mode.get()),
            ("Rate", f"{self.rate.get()} per minute (cap {C.RATE_PER_MINUTE})"),
            ("Schedule", self.sched_date.get() or "Immediate"),
        ]
        for k, v in rows:
            r = tk.Frame(card, bg=T.CARD)
            r.pack(anchor="w", padx=18, pady=2)
            tk.Label(r, text=f"{k:<24}", bg=T.CARD, fg=T.MUTED,
                     font=(T.FONT, 10, "bold")).pack(side="left")
            tk.Label(r, text=v, bg=T.CARD, fg=T.INK,
                     font=(T.FONT, 10)).pack(side="left")
        ok, why = validate_recipients(self.sel_pids, self.ctx.store)
        if not ok:
            tk.Label(card, text=f"WARNING: {why}", bg=T.CARD, fg=T.BAD,
                     font=(T.FONT, 10, "bold")).pack(anchor="w", padx=18,
                                                     pady=(10, 0))
        self._nav_buttons(True, "Continue to authorization >")

    # -- step 6: finish -> single authorization dialog ---------------------

    def _step6(self) -> None:
        card = T.card(self.body)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Ready to authorize", bg=T.CARD,
                 fg=T.INK, font=(T.FONT, 12, "bold")).pack(anchor="w",
                                                           padx=18,
                                                           pady=(16, 4))
        tk.Label(card,
                 text="Press the button below to create this campaign as a "
                      "Draft and open the 3-step authorization workflow "
                      "immediately:\n\n"
                      "      1.  Scope confirmation (recipients + content)\n"
                      "      2.  Authorized-use policy - read it, then type "
                      "the acknowledgement phrase\n"
                      "      3.  Operator sign-off (your name and role)\n\n"
                      "Delivery stays blocked until all three steps are "
                      "completed. You can also authorize later from the "
                      "Campaigns list via the 'Authorize & launch' button.",
                 bg=T.CARD, fg=T.INK, font=(T.FONT, 10), wraplength=620,
                 justify="left").pack(anchor="w", padx=18, pady=(4, 12))
        self._nav_buttons(True, "Create & authorize...", self._authorize)

    def _validate6(self) -> None:
        pass

    def _authorize(self) -> None:
        if self.tpl_id is None:
            warn(self, "SeaSim", "Pick a template (step 2).")
            return
        if not self.sel_pids:
            warn(self, "SeaSim", "Select recipients (step 3).")
            return

        camp = self.ctx.engine.create_campaign(
            self.name.get().strip(), self.tpl_id, self.sel_pids,
            self.mode.get(), self.sched_date.get(), int(self.rate.get()))
        self.app.launch_with_consent(camp.id, after=lambda launched: (
            self.app.navigate("campaigns") if launched else None))


# ---------------------------------------------------------------------------
# Reports view
# ---------------------------------------------------------------------------

class ReportsView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Reports", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 20, "bold")).pack(side="left")
        ttk.Button(bar, text="Export program JSON...",
                   command=self._export_json).pack(side="right", padx=6)

        pick = tk.Frame(self, bg=T.BG)
        pick.pack(fill="x", padx=28, pady=(4, 8))
        tk.Label(pick, text="Campaign:", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 10, "bold")).pack(side="left")
        self.cb = ttk.Combobox(pick, state="readonly", width=52,
                               font=(T.FONT, 10))
        self.cb.pack(side="left", padx=8)
        camps = self.ctx.store.campaigns_sorted()
        self.camps = camps
        self.cb["values"] = [f"{c.name}  ({c.status})" for c in camps]
        if camps:
            self.cb.current(0)
            self.cb.bind("<<ComboboxSelected>>", lambda e: self._load())

        btns = tk.Frame(self, bg=T.BG)
        btns.pack(fill="x", padx=28)
        ttk.Button(btns, text="HTML report...", style="Accent.TButton",
                   command=self._html).pack(side="left", padx=2)
        ttk.Button(btns, text="Show text report",
                   command=self._text_report).pack(side="left", padx=2)
        ttk.Button(btns, text="Events CSV...",
                   command=self._csv_events).pack(side="left", padx=2)
        ttk.Button(btns, text="Department CSV...",
                   command=self._csv_dept).pack(side="left", padx=2)

        self.out = tk.Text(self, font=(T.MONO, 10), bg=T.CARD, fg=T.INK,
                           relief="flat", padx=16, pady=12)
        self.out.pack(fill="both", expand=True, padx=28, pady=12)
        self.out.insert("1.0", "Select a campaign and choose a report.")
        self.out.configure(state="disabled")
        self._load()

    def _cid(self) -> Optional[str]:
        i = self.cb.current()
        return self.camps[i].id if i >= 0 and self.camps else None

    def _load(self) -> None:
        cid = self._cid()
        if not cid:
            return
        st = campaign_stats(self.ctx.engine, cid)
        text = build_text_report(self.ctx.engine, cid)
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.configure(state="disabled")

    def _text_report(self) -> None:
        cid = self._cid()
        if cid:
            show_text(self, "Campaign report",
                      build_text_report(self.ctx.engine, cid), mono=True)

    def _html(self) -> None:
        cid = self._cid()
        if not cid:
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".html",
            initialfile="seasim_report.html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build_html_report(self.ctx.engine, cid))
        info(self, "Exported", f"HTML report saved to\n{path}")

    def _csv_events(self) -> None:
        cid = self._cid()
        if not cid:
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv",
            initialfile="seasim_events.csv",
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(events_csv(self.ctx.engine, cid))
        info(self, "Exported", f"Saved {path}")

    def _csv_dept(self) -> None:
        cid = self._cid()
        if not cid:
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv",
            initialfile="seasim_departments.csv",
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(dept_csv(self.ctx.engine, cid))
        info(self, "Exported", f"Saved {path}")

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json",
            initialfile="seasim_program_export.json",
            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.ctx.store.export_json())
        info(self, "Exported", f"Full program state saved to {path}")


# ---------------------------------------------------------------------------
# Settings view
# ---------------------------------------------------------------------------

class SettingsView(ViewBase):
    def build(self) -> None:
        s = self.ctx.store.settings
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Settings", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 20, "bold")).pack(side="left")

        card = T.card(self.body) if hasattr(self, "body") else T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)
        form = tk.Frame(card, bg=T.CARD)
        form.pack(fill="both", expand=True, padx=18, pady=14)

        def row(r: int, label: str) -> tk.Widget:
            tk.Label(form, text=label, bg=T.CARD, fg=T.INK,
                     font=(T.FONT, 10, "bold")).grid(row=r, column=0,
                                                     sticky="nw", pady=6)
            return form

        row(0, "Organization name")
        self.e_org = tk.Entry(form, font=(T.FONT, 11), bg="white", width=34)
        self.e_org.insert(0, s.org_name)
        self.e_org.grid(row=0, column=1, sticky="w", padx=10, pady=6)

        row(1, "Default operator name")
        self.e_op = tk.Entry(form, font=(T.FONT, 11), bg="white", width=34)
        self.e_op.insert(0, s.operator_name)
        self.e_op.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        row(2, "Reminder threshold (days)")
        self.e_rem = tk.Spinbox(form, from_=1, to=90, width=6,
                                font=(T.FONT, 11))
        self.e_rem.delete(0, "end")
        self.e_rem.insert(0, str(s.reminder_days))
        self.e_rem.grid(row=2, column=1, sticky="w", padx=10, pady=6)

        self.v_jit = tk.BooleanVar(value=s.jit_training)
        ttk.Checkbutton(form, text="Show just-in-time training moments on "
                                   "interaction (recommended)",
                        variable=self.v_jit).grid(row=3, column=0,
                                                  columnspan=2, sticky="w",
                                                  pady=8)
        self.v_track = tk.BooleanVar(value=s.landing_page_track)
        ttk.Checkbutton(form, text="Record click events on tracked links",
                        variable=self.v_track).grid(row=4, column=0,
                                                    columnspan=2, sticky="w",
                                                    pady=4)

        # Safe mode display (cannot be turned off)
        safe = tk.Frame(form, bg=T.SAFE_BG, padx=10, pady=8)
        safe.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        tk.Label(safe, text="SAFE MODE: LOCKED ON", bg=T.SAFE_BG,
                 fg=T.SAFE_FG, font=(T.FONT, 10, "bold")).pack(anchor="w")
        tk.Label(safe,
                 text="SeaSim is ethical-by-design: localhost-only delivery, "
                      "recipient cap, rate cap, no credential capture, and a "
                      "mandatory authorization workflow. These cannot be "
                      "disabled.",
                 bg=T.SAFE_BG, fg=T.SAFE_FG, font=(T.FONT, 9),
                 wraplength=560, justify="left").pack(anchor="w")

        btns = tk.Frame(form, bg=T.CARD)
        btns.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(btns, text="Save settings", style="Accent.TButton",
                   command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="View authorization log",
                   command=self._consent_log).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Import program JSON...",
                   command=self._import).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Reset all data...", style="Danger.TButton",
                   command=self._reset).pack(side="left")

    def _save(self) -> None:
        s = self.ctx.store.settings
        s.org_name = self.e_org.get().strip() or C.ORG_DEFAULT
        s.operator_name = self.e_op.get().strip()
        try:
            s.reminder_days = max(1, min(90, int(self.e_rem.get())))
        except ValueError:
            s.reminder_days = 14
        s.jit_training = self.v_jit.get()
        s.landing_page_track = self.v_track.get()
        self.ctx.store.save(force=True)
        info(self, "SeaSim", "Settings saved.")

    def _consent_log(self) -> None:
        lines = []
        for entry in self.ctx.store.settings.consent_log:
            lines.append(f"{entry.get('at', '')}  {entry.get('action', '')}"
                         f"  by {entry.get('by', '')}"
                         f"  -  {entry.get('note', '')}")
        text = "\n".join(lines) or "No authorizations recorded yet."
        show_text(self, "Authorization log", text, mono=True)

    def _import(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="Import SeaSim JSON",
            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        if not confirm(self, "Import program JSON",
                       "This REPLACES all current data. Continue?"):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                n = self.ctx.store.import_json(fh.read())
        except Exception as exc:
            error(self, "Import failed", str(exc))
            return
        self.app.rebuild_views()
        info(self, "Imported", f"Loaded {n} records.")

    def _reset(self) -> None:
        if not confirm(self, "Reset all data",
                       "Delete ALL participants, campaigns, events and "
                       "settings? This cannot be undone."):
            return
        self.ctx.store.reset_all()
        for t in builtin_templates():
            self.ctx.store.templates[t.id] = t
        self.ctx.store.save(force=True)
        self.app.rebuild_views()
        info(self, "SeaSim", "All data cleared; built-in templates restored.")


# ---------------------------------------------------------------------------
# Training log
# ---------------------------------------------------------------------------

class TrainingView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Training Log", bg=T.BG,
                 fg=T.INK, font=(T.FONT, 20, "bold")).pack(side="left")

        tk.Label(self, text="Every delivered training moment, newest first. "
                            "Used to verify participants received education "
                            "after interacting - never for discipline.",
                 bg=T.BG, fg=T.MUTED, font=(T.FONT, 9)).pack(anchor="w",
                                                             padx=28)

        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)
        cols = ("when", "who", "camp", "tpl", "status", "tip")
        tree = ttk.Treeview(card, columns=cols, show="headings")
        for cid, txt, w in (("when", "Trained at", 150), ("who", "Participant",
                                                          150),
                            ("camp", "Campaign", 150), ("tpl", "Template",
                                                        170),
                            ("status", "Interaction", 90), ("tip", "Coaching "
                                                            "tip", 240)):
            tree.heading(cid, text=txt)
            tree.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        sb.pack(side="right", fill="y", pady=2)

        rows = []
        for e in self.ctx.store.events.values():
            if not e.trained_at:
                continue
            camp = self.ctx.store.campaigns.get(e.campaign_id)
            tpl = (self.ctx.store.templates.get(camp.template_id)
                   if camp else None)
            p = self.ctx.store.participants.get(e.participant_id)
            rows.append((
                e.trained_at, p.name if p else "?",
                camp.name if camp else "?",
                tpl.name if tpl else "?", e.status,
                tpl.difficulty + " difficulty" if tpl else "-",
            ))
        rows.sort(reverse=True)
        for r in rows:
            tree.insert("", "end", values=r)
        if not rows:
            tk.Label(card, text="No training moments delivered yet. Launch a "
                                "campaign and simulate a click in the Inbox "
                                "view.", bg=T.CARD, fg=T.MUTED,
                     font=(T.FONT, 10)).pack(pady=18)
