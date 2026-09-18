"""Main application views for SeaSim.

Each view is a method-built tk.Frame hosted by AppShell (app.py).
Views read state through ``self.ctx.store`` / ``self.ctx.engine`` and
are rebuilt on data-change notifications.
"""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, ttk
from typing import Callable, Dict, List, Optional

from seasim import constants as C
from seasim.engine import models as M
from seasim.reports import (
    build_text_report, campaign_stats, dept_csv, department_breakdown,
    events_csv, program_totals,
)
from seasim.safety import POLICY_TEXT, validate_recipients
from seasim.templates import builtin_templates
from seasim.ui import theme as T
from seasim.ui.dialogs import (
    ParticipantDialog, TemplateEditorDialog, confirm, error, info,
    prompt_string, show_text, warn,
)


class ViewContext:
    """Bundle passed to every view."""

    def __init__(self, app) -> None:
        self.app = app
        self.store = app.store
        self.engine = app.engine


class Sidebar(tk.Frame):
    """Dark navigation rail."""

    ITEMS = [
        ("dashboard", "Dashboard"),
        ("campaigns", "Campaigns"),
        ("wizard", "New Campaign"),
        ("participants", "Participants"),
        ("templates", "Templates"),
        ("inbox", "Inbox Simulation"),
        ("training", "Training Log"),
        ("reports", "Reports"),
        ("settings", "Settings"),
    ]

    def __init__(self, master, on_nav: Callable[[str], None]) -> None:
        super().__init__(master, bg=T.INK, width=C.SIDEBAR_W)
        self.pack_propagate(False)
        self.on_nav = on_nav
        self.buttons: Dict[str, tk.Label] = {}

        tk.Frame(self, bg=T.INK, height=18).pack()
        head = tk.Frame(self, bg=T.INK)
        head.pack(fill="x", padx=16)
        tk.Label(head, text="SeaSim", fg="white", bg=T.INK,
                 font=(T.FONT, 17, "bold")).pack(anchor="w")
        tk.Label(head, text="Awareness Simulator", fg="#94a3b8", bg=T.INK,
                 font=(T.FONT, 9)).pack(anchor="w")

        self.safe_chip = tk.Label(
            self, text="  SAFE MODE  ", fg=T.SAFE_FG, bg=T.SAFE_BG,
            font=(T.FONT, 8, "bold"))
        self.safe_chip.pack(anchor="w", padx=16, pady=(10, 2))
        self.offline_chip = tk.Label(
            self, text="  LOCALHOST ONLY  ", fg="#1e3a8a", bg="#dbeafe",
            font=(T.FONT, 8, "bold"))
        self.offline_chip.pack(anchor="w", padx=16, pady=(2, 14))

        self.navframe = tk.Frame(self, bg=T.INK)
        self.navframe.pack(fill="x", padx=8)
        for key, label in self.ITEMS:
            b = tk.Label(self.navframe, text=label, fg="#cbd5e1", bg=T.INK,
                         font=(T.FONT, 11), anchor="w", padx=12, pady=8)
            b.pack(fill="x", pady=1)
            b.bind("<Button-1>", lambda e, k=key: self.on_nav(k))
            b.bind("<Enter>", lambda e, w=b: w.config(fg="white"))
            b.bind("<Leave>", lambda e, w=b: w.config(
                fg="white" if w.cget("bg") == T.ACCENT else "#cbd5e1"))
            self.buttons[key] = b

        tk.Frame(self, bg=T.INK).pack(fill="both", expand=True)
        ver = tk.Label(self, text=f"v{C.APP_VERSION} - internal use only",
                       fg="#64748b", bg=T.INK, font=(T.FONT, 8))
        ver.pack(anchor="w", padx=16, pady=10)

    def highlight(self, key: str) -> None:
        for k, b in self.buttons.items():
            if k == key:
                b.config(bg=T.ACCENT, fg="white")
            else:
                b.config(bg=T.INK, fg="#cbd5e1")


class ViewBase(tk.Frame):
    def __init__(self, ctx: ViewContext) -> None:
        super().__init__(ctx.app.content, bg=T.BG)
        self.ctx = ctx
        self.app = ctx.app


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(ViewBase):
    def build(self) -> None:
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(head, text="Program Dashboard",
                 bg=T.BG, fg=T.INK, font=(T.FONT, 20, "bold")).pack(
            anchor="w")
        tk.Label(head,
                 text=f"{self.ctx.store.settings.org_name} - simulated "
                      f"phishing awareness, localhost only",
                 bg=T.BG, fg=T.MUTED, font=(T.FONT, 10)).pack(anchor="w")

        tot = program_totals(self.ctx.engine)
        cnt = self.ctx.engine.counts()

        tiles = tk.Frame(self, bg=T.BG)
        tiles.pack(fill="x", padx=28, pady=(14, 0))
        data = [
            (str(cnt["participants"]), "PARTICIPANTS", T.INK),
            (str(tot["campaigns"]), "CAMPAIGNS RUN", T.INK),
            (str(tot["sent"]), "EMAILS SIMULATED", T.INK),
            (f'{tot["click_rate"]:.0f}%', "CLICK RATE", T.BAD),
            (f'{tot["report_rate"]:.0f}%', "REPORT RATE", T.GOOD),
        ]
        for i, (v, lbl, color) in enumerate(data):
            tile = T.stat_tile(tiles, v, lbl, color)
            tile.grid(row=0, column=i, sticky="nsew", padx=(0, 12))
            tiles.columnconfigure(i, weight=1)

        # Safety / quick actions card
        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=18)
        tk.Label(card, text="Getting started", bg=T.CARD,
                 fg=T.INK, font=(T.FONT, 12, "bold")).pack(anchor="w",
                                                           padx=18,
                                                           pady=(14, 4))
        steps = [
            ("1.", "Add participants (internal staff only) in Participants."),
            ("2.", "Review the built-in awareness email Templates."),
            ("3.", "Create a campaign via New Campaign - the 7-step wizard "
                   "walks you through scope, content, schedule, and the "
                   "authorization workflow."),
            ("4.", "Watch delivery in Inbox Simulation; clicked participants "
                   "trigger just-in-time training moments."),
            ("5.", "Export CSV / text reports from Reports."),
        ]
        for num, txt in steps:
            row = tk.Frame(card, bg=T.CARD)
            row.pack(anchor="w", padx=18, pady=2)
            tk.Label(row, text=num, bg=T.CARD, fg=T.ACCENT,
                     font=(T.FONT, 10, "bold")).pack(side="left")
            tk.Label(row, text="  " + txt, bg=T.CARD, fg=T.INK,
                     font=(T.FONT, 10), wraplength=620,
                     justify="left").pack(side="left")

        st = tk.Frame(card, bg=T.CARD)
        st.pack(anchor="w", padx=18, pady=(10, 14))
        tk.Label(st, text="Safety envelope:", bg=T.CARD, fg=T.MUTED,
                 font=(T.FONT, 9, "bold")).pack(side="left")
        tk.Label(st, text="  safe mode ON - 500 recipient cap - 60/min rate "
                          "cap - localhost-only - no credential capture",
                 bg=T.CARD, fg=T.SAFE_FG,
                 font=(T.FONT, 9, "bold")).pack(side="left")


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------

class ParticipantsView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Participants", bg=T.BG,
                 fg=T.INK, font=(T.FONT, 20, "bold")).pack(side="left")
        ttk.Button(bar, text="Import CSV...", command=self._import).pack(
            side="right", padx=6)
        ttk.Button(bar, text="Add participant", style="Accent.TButton",
                   command=self._add).pack(side="right")

        tk.Label(self, text="Internal staff only - external addresses are "
                            "rejected by the safety envelope.", bg=T.BG,
                 fg=T.MUTED, font=(T.FONT, 9)).pack(anchor="w", padx=28)

        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)

        cols = ("name", "email", "dept", "loc", "status")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 selectmode="extended")
        for cid, txt, w, anch in (("name", "Name", 180, "w"),
                                  ("email", "Email", 230, "w"),
                                  ("dept", "Department", 120, "w"),
                                  ("loc", "Location", 110, "w"),
                                  ("status", "Status", 90, "center")):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor=anch)
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0),
                       pady=2)
        sb.pack(side="right", fill="y", pady=2)
        self.tree.tag_configure("inactive", foreground="#94a3b8")

        btns = tk.Frame(card, bg=T.CARD)
        btns.pack(fill="x", side="bottom", padx=8, pady=8)
        ttk.Button(btns, text="Edit", command=self._edit).pack(side="left",
                                                               padx=4)
        ttk.Button(btns, text="Toggle active", command=self._toggle).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=4)
        self._reload()

    def _reload(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for p in self.ctx.store.participants_sorted():
            self.tree.insert("", "end", iid=p.id, values=(
                p.name, p.email, p.department, p.location,
                "Active" if p.active else "Inactive"),
                tags=() if p.active else ("inactive",))

    def _add(self) -> None:
        ParticipantDialog(self, self._do_add)

    def _do_add(self, data: dict) -> None:
        p = M.Participant.create(data["name"], data["email"],
                                 data["department"], data["location"],
                                 data["note"])
        p.active = data["active"]
        with self.ctx.store.lock:
            self.ctx.store.participants[p.id] = p
        self.ctx.store.save(force=True)
        self._reload()

    def _sel(self) -> Optional[M.Participant]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.ctx.store.participants.get(sel[0])

    def _edit(self) -> None:
        p = self._sel()
        if p is None:
            info(self, "SeaSim", "Select a participant first.")
            return
        ParticipantDialog(self, lambda d: self._do_edit(p.id, d), p)

    def _do_edit(self, pid: str, d: dict) -> None:
        p = self.ctx.store.participants.get(pid)
        if p is None:
            return
        p.name, p.email = d["name"], d["email"]
        p.department, p.location = d["department"], d["location"]
        p.note, p.active = d["note"], d["active"]
        self.ctx.store.save(force=True)
        self._reload()

    def _toggle(self) -> None:
        p = self._sel()
        if p is None:
            info(self, "SeaSim", "Select a participant first.")
            return
        p.active = not p.active
        self.ctx.store.save(force=True)
        self._reload()

    def _delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            info(self, "SeaSim", "Select one or more participants first.")
            return
        if not confirm(self, "Delete participants",
                       f"Delete {len(sel)} participant(s)? "
                       f"Past campaign events are kept."):
            return
        with self.ctx.store.lock:
            for pid in sel:
                self.ctx.store.participants.pop(pid, None)
        self.ctx.store.save(force=True)
        self._reload()

    def _import(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="Import participants CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            added, skipped = self._parse_csv(path)
        except Exception as exc:
            error(self, "Import failed", str(exc))
            return
        info(self, "Import complete",
             f"Added {added} participant(s). Skipped {skipped} "
             f"(invalid or duplicate).")

    def _parse_csv(self, path: str):
        import csv as _csv

        added = skipped = 0
        existing = {p.email for p in self.ctx.store.participants.values()}
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = _csv.reader(fh)
            rows = list(reader)
        if not rows:
            return 0, 0
        start = 0
        if rows[0] and rows[0][0].strip().lower() in ("name", "full name"):
            start = 1
        for row in rows[start:]:
            if not row or not row[0].strip():
                continue
            name = row[0].strip()
            email = (row[1].strip().lower() if len(row) > 1 else "")
            dept = row[2].strip() if len(row) > 2 and row[2].strip() \
                else "Operations"
            loc = row[3].strip() if len(row) > 3 and row[3].strip() else "HQ"
            if "@" not in email or email in existing:
                skipped += 1
                continue
            p = M.Participant.create(name, email, dept, loc)
            with self.ctx.store.lock:
                self.ctx.store.participants[p.id] = p
            existing.add(email)
            added += 1
        self.ctx.store.save(force=True)
        self._reload()
        return added, skipped


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TemplatesView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Email Templates", bg=T.BG,
                 fg=T.INK, font=(T.FONT, 20, "bold")).pack(side="left")
        ttk.Button(bar, text="New template", style="Accent.TButton",
                   command=self._new).pack(side="right")

        tk.Label(self, text="Built-ins are read-only. Custom templates can "
                            "be edited or deleted. No credential capture, "
                            "ever.", bg=T.BG, fg=T.MUTED,
                 font=(T.FONT, 9)).pack(anchor="w", padx=28)

        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)
        cols = ("name", "cat", "diff", "tech")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 selectmode="browse")
        for cid, txt, w in (("name", "Template", 260),
                            ("cat", "Category", 110),
                            ("diff", "Difficulty", 90),
                            ("tech", "Techniques", 320)):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0),
                       pady=2)
        sb.pack(side="right", fill="y", pady=2)
        self.tree.tag_configure("builtin", foreground="#475569")

        btns = tk.Frame(card, bg=T.CARD)
        btns.pack(fill="x", side="bottom", padx=8, pady=8)
        ttk.Button(btns, text="Preview", command=self._preview).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Edit", command=self._edit).pack(side="left",
                                                               padx=4)
        ttk.Button(btns, text="Duplicate", command=self._dup).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=4)
        self._reload()

    def _reload(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        tpl_list = sorted(self.ctx.store.templates.values(),
                          key=lambda t: (t.builtin, t.name.lower()))
        for t in tpl_list:
            self.tree.insert("", "end", iid=t.id, values=(
                t.name + ("  (built-in)" if t.builtin else ""),
                t.category, t.difficulty, ", ".join(t.techniques)),
                tags=("builtin",) if t.builtin else ())

    def _sel(self) -> Optional[M.EmailTemplate]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.ctx.store.templates.get(sel[0])

    def _preview(self) -> None:
        t = self._sel()
        if t is None:
            info(self, "SeaSim", "Select a template first.")
            return
        body = t.render_body("Jordan", self.ctx.store.settings.org_name,
                             "https://seasim.local/sim/preview")
        text = (f"PREVIEW (simulated send)\n\n"
                f"Name       : {t.name}\n"
                f"Category   : {t.category}  -  Difficulty: {t.difficulty}\n"
                f"Techniques : {', '.join(t.techniques) or 'n/a'}\n\n"
                f"Subject:\n{t.render_subject()}\n\n"
                f"Body:\n{body}\n\n"
                f"Spot-the-phish indicators:\n" +
                "\n".join(f"  - {i}" for i in t.phishing_indicators))
        show_text(self, f"Template preview - {t.name}", text, mono=True)

    def _new(self) -> None:
        TemplateEditorDialog(self, self._save_new)

    def _save_new(self, tpl: M.EmailTemplate) -> None:
        with self.ctx.store.lock:
            self.ctx.store.templates[tpl.id] = tpl
        self.ctx.store.save(force=True)
        self._reload()

    def _edit(self) -> None:
        t = self._sel()
        if t is None:
            info(self, "SeaSim", "Select a template first.")
            return
        if t.builtin:
            if not confirm(self, "Built-in template",
                           "Built-ins are read-only. Duplicate it into an "
                           "editable copy?"):
                return
            copy = M.EmailTemplate.create(
                t.name + " (copy)", t.category, t.difficulty, t.techniques,
                t.subject, t.body, t.link_label, t.phishing_indicators)
            with self.ctx.store.lock:
                self.ctx.store.templates[copy.id] = copy
            self.ctx.store.save(force=True)
            self._reload()
            return
        TemplateEditorDialog(self, lambda nt: self._save_edit(t.id, nt), t)

    def _save_edit(self, tid: str, nt: M.EmailTemplate) -> None:
        old = self.ctx.store.templates.get(tid)
        if old is None:
            return
        nt.id = old.id
        nt.builtin = False
        nt.created = old.created
        from seasim.engine.models import now_iso
        nt.updated = now_iso()
        with self.ctx.store.lock:
            self.ctx.store.templates[tid] = nt
        self.ctx.store.save(force=True)
        self._reload()

    def _dup(self) -> None:
        t = self._sel()
        if t is None:
            info(self, "SeaSim", "Select a template first.")
            return
        copy = M.EmailTemplate.create(
            t.name + " (copy)", t.category, t.difficulty, t.techniques,
            t.subject, t.body, t.link_label, t.phishing_indicators)
        with self.ctx.store.lock:
            self.ctx.store.templates[copy.id] = copy
        self.ctx.store.save(force=True)
        self._reload()

    def _delete(self) -> None:
        t = self._sel()
        if t is None:
            info(self, "SeaSim", "Select a template first.")
            return
        if t.builtin:
            warn(self, "Built-in template", "Built-ins cannot be deleted.")
            return
        if not confirm(self, "Delete template",
                       f"Delete '{t.name}'? Campaigns referencing it keep "
                       f"a snapshot reference."):
            return
        with self.ctx.store.lock:
            self.ctx.store.templates.pop(t.id, None)
        self.ctx.store.save(force=True)
        self._reload()


# ---------------------------------------------------------------------------
# Campaigns list
# ---------------------------------------------------------------------------

class CampaignsView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Campaigns", bg=T.BG,
                 fg=T.INK, font=(T.FONT, 20, "bold")).pack(side="left")
        ttk.Button(bar, text="New campaign", style="Accent.TButton",
                   command=lambda: self.app.navigate("wizard")).pack(
            side="right")

        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)
        cols = ("name", "status", "tpl", "n", "mode", "created")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 selectmode="browse")
        for cid, txt, w, anch in (
                ("name", "Campaign", 220, "w"),
                ("status", "Status", 100, "center"),
                ("tpl", "Template", 200, "w"),
                ("n", "Recipients", 90, "center"),
                ("mode", "Mode", 150, "w"),
                ("created", "Created", 140, "w")):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor=anch)
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0),
                       pady=2)
        sb.pack(side="right", fill="y", pady=2)

        btns = tk.Frame(card, bg=T.CARD)
        btns.pack(fill="x", side="bottom", padx=8, pady=8)
        ttk.Button(btns, text="Open detail", command=self._open).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Authorize & launch...", style="Accent.TButton",
                   command=self._launch).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel delivery", command=self._cancel).pack(
            side="left", padx=4)
        ttk.Button(btns, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=4)
        self._reload()

    def _reload(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for c in self.ctx.store.campaigns_sorted():
            tpl = self.ctx.store.templates.get(c.template_id)
            self.tree.insert("", "end", iid=c.id, values=(
                c.name, c.status, tpl.name if tpl else "(missing)",
                len(c.participant_ids), c.mode, c.created))

    def _sel(self) -> Optional[M.Campaign]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.ctx.store.campaigns.get(sel[0])

    def _open(self) -> None:
        c = self._sel()
        if c is None:
            info(self, "SeaSim", "Select a campaign first.")
            return
        self.app.open_campaign_detail(c.id)

    def _launch(self) -> None:
        c = self._sel()
        if c is None:
            info(self, "SeaSim",
                 "Select a Draft campaign, then press 'Authorize & launch' "
                 "to open the 3-step authorization workflow.")
            return
        if c.status != M.CAMPAIGN_DRAFT:
            info(self, "SeaSim",
                 f"'{c.name}' is {c.status}. Only Draft campaigns need "
                 f"authorization.")
            return
        self.app.launch_with_consent(c.id)

    def _cancel(self) -> None:
        c = self._sel()
        if c is None:
            return
        if c.status != M.CAMPAIGN_ACTIVE:
            info(self, "SeaSim", "Only Active campaigns can be cancelled.")
            return
        if confirm(self, "Cancel delivery",
                   "Stop the delivery run and mark the campaign Completed?"):
            self.ctx.engine.cancel_delivery(c.id)
            self._reload()

    def _delete(self) -> None:
        c = self._sel()
        if c is None:
            return
        if c.status == M.CAMPAIGN_ACTIVE:
            warn(self, "SeaSim", "Cancel the delivery before deleting.")
            return
        if not confirm(self, "Delete campaign",
                       f"Delete '{c.name}' and all its event data?"):
            return
        self.ctx.engine.delete_campaign(c.id)
        self._reload()


# ---------------------------------------------------------------------------
# Campaign detail (events per participant)
# ---------------------------------------------------------------------------

class CampaignDetailView(ViewBase):
    def __init__(self, ctx: ViewContext, campaign_id: str) -> None:
        super().__init__(ctx)
        self.campaign_id = campaign_id

    def build(self) -> None:
        c = self.ctx.engine.get_campaign(self.campaign_id)
        if c is None:
            tk.Label(self, text="Campaign not found.", bg=T.BG).pack(pady=30)
            return
        st = campaign_stats(self.ctx.engine, c.id)

        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=28, pady=(24, 6))
        row = tk.Frame(head, bg=T.BG)
        row.pack(fill="x")
        ttk.Button(row, text="< Campaigns",
                   command=lambda: self.app.navigate("campaigns")).pack(
            side="left")
        tk.Label(head, text=c.name, bg=T.BG, fg=T.INK,
                 font=(T.FONT, 20, "bold")).pack(anchor="w", pady=(8, 0))
        meta = (f"{st.template_name} - difficulty {st.template_difficulty} - "
                f"{len(c.participant_ids)} recipients - mode: {c.mode}")
        tk.Label(head, text=meta, bg=T.BG, fg=T.MUTED,
                 font=(T.FONT, 10)).pack(anchor="w")
        chips = tk.Frame(head, bg=T.BG)
        chips.pack(anchor="w", pady=6)
        fg, bgc = T.status_colors(c.status)
        T.badge(chips, f"  {c.status}  ", fg, bgc).pack(side="left")
        if c.consent:
            T.badge(chips, f"  consent: {c.consent_by} @ {c.consent_at}  ",
                    T.SAFE_FG, T.SAFE_BG).pack(side="left", padx=6)
        else:
            T.badge(chips, "  NOT AUTHORIZED  ", T.BAD,
                    T.DANGER_BG).pack(side="left", padx=6)

        # Metric strip
        tiles = tk.Frame(self, bg=T.BG)
        tiles.pack(fill="x", padx=28, pady=(4, 0))
        for i, (v, lbl, col) in enumerate([
                (str(st.sent), "SENT", T.INK),
                (str(st.opened), "OPENED", T.WARN),
                (str(st.clicked), "CLICKED", T.BAD),
                (str(st.reported), "REPORTED", T.GOOD),
                (str(st.dismissed), "DISMISSED", T.MUTED),
                (f"{st.click_rate:.0f}%", "CLICK RATE", T.BAD),
                (f"{st.resilience:.0f}%", "RESILIENCE", T.GOOD)]):
            tile = T.stat_tile(tiles, v, lbl, col)
            tile.grid(row=0, column=i, sticky="nsew", padx=(0, 8))
            tiles.columnconfigure(i, weight=1)

        # Department table
        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=14)
        tk.Label(card, text="Outcomes by participant",
                 bg=T.CARD, fg=T.INK, font=(T.FONT, 12, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4))
        cols = ("name", "dept", "status", "when", "score")
        tree = ttk.Treeview(card, columns=cols, show="headings")
        for cid, txt, w, anch in (("name", "Participant", 170, "w"),
                                  ("dept", "Dept", 100, "w"),
                                  ("status", "Status", 100, "center"),
                                  ("when", "Last action", 160, "w"),
                                  ("score", "Risk", 60, "center")):
            tree.heading(cid, text=txt)
            tree.column(cid, width=w, anchor=anch)
        sb = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(fill="both", expand=True, padx=10, pady=(2, 8), side="left")
        sb.pack(side="right", fill="y", pady=(2, 8))
        for st_code, fgc, bgc in (("Clicked", T.BAD, T.DANGER_BG),
                                  ("Reported", T.GOOD, T.SAFE_BG),
                                  ("Opened", T.WARN, "#fef3c7")):
            tree.tag_configure(st_code, foreground=fgc)

        for e in self.ctx.engine.campaign_events(c.id):
            p = self.ctx.engine.get_participant(e.participant_id)
            if p is None:
                continue
            when = (e.clicked_at or e.reported_at or e.opened_at
                    or e.dismissed_at or "-")
            tree.insert("", "end", values=(
                p.name, p.department, e.status, when,
                e.risk_score or ""), tags=(e.status,))


# ---------------------------------------------------------------------------
# Inbox simulation
# ---------------------------------------------------------------------------

class InboxView(ViewBase):
    def build(self) -> None:
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(bar, text="Inbox Simulation", bg=T.BG,
                 fg=T.INK, font=(T.FONT, 20, "bold")).pack(side="left")
        ttk.Button(bar, text="Refresh", command=self._reload).pack(
            side="right")

        tk.Label(self, text="Simulated emails arrive HERE - never in a real "
                            "mailbox. Play the participant: open, click, "
                            "report, or dismiss.",
                 bg=T.BG, fg=T.MUTED, font=(T.FONT, 9)).pack(anchor="w",
                                                             padx=28)

        # Status hint (tells the user what to do next)
        self.hint = tk.Label(self, text="", bg=T.BG, fg=T.INK,
                             font=(T.FONT, 10, "bold"), wraplength=800,
                             justify="left")
        self.hint.pack(anchor="w", padx=28, pady=(6, 0))

        # Campaign picker (shows ALL campaigns; drafts included with hint)
        pick = tk.Frame(self, bg=T.BG)
        pick.pack(fill="x", padx=28, pady=(8, 4))
        tk.Label(pick, text="Campaign:", bg=T.BG, fg=T.INK,
                 font=(T.FONT, 10, "bold")).pack(side="left")
        self.cb = ttk.Combobox(pick, state="readonly", font=(T.FONT, 10),
                               width=52)
        self.cb.pack(side="left", padx=8)
        self.camps = self.ctx.store.campaigns_sorted()
        self.cb["values"] = [
            f"{c.name}  ({c.status}, {len(c.participant_ids)} recipients)"
            for c in self.camps]
        if self.camps:
            # Default to a LAUNCHED campaign if any exist - stale drafts
            # must never mask the campaign the user just launched.
            idx = 0
            for i, c in enumerate(self.camps):
                if c.status != M.CAMPAIGN_DRAFT:
                    idx = i
                    break
            self.cb.current(idx)
            self.cb.bind("<<ComboboxSelected>>", lambda e: self._load())

        card = T.card(self)
        card.pack(fill="both", expand=True, padx=28, pady=12)
        cols = ("to", "subject", "status", "actions")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 selectmode="browse")
        for cid, txt, w in (("to", "To", 190), ("subject", "Subject", 300),
                            ("status", "Status", 100), ("actions", "ID", 90)):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0),
                       pady=2)
        sb.pack(side="right", fill="y", pady=2)

        btns = tk.Frame(card, bg=T.CARD)
        btns.pack(fill="x", side="bottom", padx=8, pady=8)
        ttk.Button(btns, text="Open (mark opened)",
                   command=lambda: self._act("open")).pack(side="left", padx=4)
        ttk.Button(btns, text="Click link", style="Accent.TButton",
                   command=lambda: self._act("click")).pack(side="left",
                                                            padx=4)
        ttk.Button(btns, text="Report Phish", command=lambda:
                   self._act("report")).pack(side="left", padx=4)
        ttk.Button(btns, text="Dismiss", command=lambda:
                   self._act("dismiss")).pack(side="left", padx=4)

        self._update_hint()
        self._load()
        self.after(1200, self._auto_refresh)

    def _auto_refresh(self) -> None:
        """Live-update rows + hint while the view is open (delivery runs
        in a background thread - the list must fill in real time)."""
        if not self.winfo_exists():
            return
        try:
            self._refresh_rows()
            self._update_hint()
        except Exception:
            pass
        self.after(1200, self._auto_refresh)

    def _refresh_rows(self) -> None:
        idx = self.cb.current() if self.camps else -1
        if idx < 0 or idx >= len(self.camps):
            return
        c = self.camps[idx]
        # Re-read campaign state (it may have just launched/completed).
        fresh = self.ctx.store.campaigns.get(c.id)
        if fresh is not None:
            c = fresh
            self.camps[idx] = c
        events = self.ctx.engine.campaign_events(c.id)
        current = set(self.tree.get_children())
        wanted = {e.id for e in events}
        if current == wanted:
            return
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        tpl = self.ctx.engine.get_template(c.template_id)
        for e in events:
            p = self.ctx.engine.get_participant(e.participant_id)
            if p is None:
                continue
            subj = tpl.render_subject() if tpl else "(missing)"
            self.tree.insert("", "end", iid=e.id, values=(
                f"{p.name} <{p.email}>", subj, e.status, e.id[:12]),
                tags=(e.status,))

    def _update_hint(self) -> None:
        if not self.camps:
            self.hint.config(
                text="No campaigns yet - create one via 'New Campaign', then "
                     "authorize & launch it. Delivered emails appear here.",
                fg=T.MUTED)
            return
        c = self.camps[max(0, self.cb.current())]
        if c.status == M.CAMPAIGN_DRAFT:
            self.hint.config(
                text="This campaign is a DRAFT - nothing has been sent. "
                     "Go to Campaigns, select it, press 'Authorize & "
                     "launch...', complete the 3-step authorization, and "
                     "the delivered emails will appear here.",
                fg=T.WARN)
        elif c.status == M.CAMPAIGN_ACTIVE:
            self.hint.config(text="Delivering now - rows appear as emails "
                                  "are simulated-sent.", fg=T.ACCENT)
        else:
            self.hint.config(text="Delivery finished - select a row below "
                                  "and play the participant.", fg=T.GOOD)

    def _load(self) -> None:
        self._update_hint()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._refresh_rows()
        self.tree.tag_configure("Clicked", foreground=T.BAD)
        self.tree.tag_configure("Reported", foreground=T.GOOD)
        self.tree.tag_configure("Opened", foreground=T.WARN)

    def _reload(self) -> None:
        # Rebuild the whole view cleanly (drop stale widgets first).
        for w in self.winfo_children():
            w.destroy()
        self.build()

    def _sel_event(self) -> Optional[M.CampaignEvent]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.ctx.store.events.get(sel[0])

    def _act(self, action: str) -> None:
        e = self._sel_event()
        if e is None:
            info(self, "SeaSim", "Select a simulated email first.")
            return
        if action == "open":
            self.ctx.engine.mark_opened(e.id)
        elif action == "click":
            self.ctx.engine.click(e.id)
        elif action == "report":
            self.ctx.engine.report(e.id)
        elif action == "dismiss":
            self.ctx.engine.dismiss(e.id)
        # JIT training moments open via the app event pump (single path).
        self._load()
