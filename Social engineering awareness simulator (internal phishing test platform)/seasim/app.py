"""SeaSim application shell: main window, navigation, and runtime wiring.

Hosts the sidebar + content views, pumps the engine event bus onto the
Tk thread via a queue, runs the loopback SMTP stub, autosaves the store,
and owns the launch-with-consent flow.
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional, Tuple

from seasim import constants as C
from seasim.engine import models as M
from seasim.engine.engine import Engine
from seasim.engine.store import Store
from seasim.mailer import LocalSmtpStub, SmtpMailer
from seasim.templates import builtin_templates
from seasim.ui import theme as T
from seasim.ui.dialogs import confirm, info, warn
from seasim.ui.views import (
    CampaignDetailView, CampaignsView, DashboardView, InboxView,
    ParticipantsView, TemplatesView, ViewContext, Sidebar,
)
from seasim.ui.views2 import (
    ReportsView, SettingsView, TrainingView, WizardView,
)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(C.APP_TITLE)
        self.configure(bg=T.BG)
        self.geometry(f"{C.WINDOW_DEFAULT_W}x{C.WINDOW_DEFAULT_H}")
        self.minsize(C.WINDOW_MIN_W, C.WINDOW_MIN_H)

        # Core objects
        self.store = Store()
        self.engine = Engine(self.store)
        self.ctx = ViewContext(self)
        # Cross-thread event pump (engine threads -> Tk thread).
        # Created FIRST: the SMTP stub logger also uses this queue -
        # background threads must never call Tk directly (deadlocks on
        # Python 3.14 / Tk 9.0).
        self._q: "queue.Queue[tuple]" = queue.Queue()
        self.mailer = SmtpMailer()
        self.smtp_stub = LocalSmtpStub(
            logger=lambda line: self._q.put(("log", {"line": line})))
        self.smtp_stub.start()   # loopback sink; failure is non-fatal
        # Point the client at the port the stub actually bound (it can
        # fall back to +1..+10 when 8025 is already taken).
        self.mailer.port = self.smtp_stub.bound_port
        self.engine.subscribe(self._on_engine_event)

        self._seed_templates()
        self._build()
        self._pump()
        self.after(1000, self._autosave_tick)
        self.after(120000, self._housekeeping_tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- setup -----------------------------------------------------------

    def _seed_templates(self) -> None:
        existing = {t.name for t in self.store.templates.values()}
        for t in builtin_templates():
            if t.name not in existing:
                self.store.templates[t.id] = t
        self.store.save(force=True)

    def _build(self) -> None:
        # Header band
        self.header = tk.Frame(self, bg=T.INK, height=6)
        self.header.pack(fill="x", side="top")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True)

        self.sidebar = Sidebar(body, self.navigate)
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(body, bg=T.BG)
        self.content.pack(side="left", fill="both", expand=True)

        # Status bar
        self.status = tk.Label(
            self, text="", bg="#f1f5f9", fg=T.MUTED, anchor="w",
            font=(T.FONT, 9))
        self.status.pack(fill="x", side="bottom")
        self.set_status("Safe mode ON - localhost-only - no external "
                        "connections")

        # Sidebar safety chips
        self.sidebar.safe_chip.config(
            text="  SAFE MODE: ON  " if self.store.settings.safe_mode
            else "  SAFE MODE OFF  ",
            fg=T.SAFE_FG if self.store.settings.safe_mode else T.BAD,
            bg=T.SAFE_BG if self.store.settings.safe_mode else T.DANGER_BG)

        self.views: Dict[str, Callable[[], object]] = {
            "dashboard": DashboardView,
            "campaigns": CampaignsView,
            "wizard": WizardView,
            "participants": ParticipantsView,
            "templates": TemplatesView,
            "inbox": InboxView,
            "training": TrainingView,
            "reports": ReportsView,
            "settings": SettingsView,
        }
        self.navigate("dashboard")

    # -- navigation ---------------------------------------------------------

    def navigate(self, key: str) -> None:
        self.sidebar.highlight(key)
        for w in self.content.winfo_children():
            w.destroy()
        cls = self.views.get(key)
        if cls is None:
            return
        view = cls(self.ctx)
        view.pack(fill="both", expand=True)
        if hasattr(view, "build"):
            view.build()

    def rebuild_views(self) -> None:
        """Re-run current view after data reset/import."""
        self.navigate(self.sidebar.buttons and next(
            (k for k, b in self.sidebar.buttons.items()
             if b.cget("bg") == T.ACCENT), "dashboard"))

    def open_campaign_detail(self, campaign_id: str) -> None:
        self.sidebar.highlight("")
        for w in self.content.winfo_children():
            w.destroy()
        view = CampaignDetailView(self.ctx, campaign_id)
        view.pack(fill="both", expand=True)
        view.build()

    def set_status(self, text: str) -> None:
        self.status.config(text=text)

    # -- launch flow ---------------------------------------------------------

    def launch_with_consent(self, campaign_id: str,
                            after: Optional[Callable[[bool], None]] = None) \
            -> None:
        """Run the consent workflow, then launch. Safe against re-entry."""
        camp = self.engine.get_campaign(campaign_id)
        if camp is None:
            return
        if camp.status == M.CAMPAIGN_ACTIVE:
            info(self, "SeaSim", "Campaign is already running.")
            if after:
                after(False)
            return

        # Wizard path passes a fresh draft; campaigns list may re-launch
        # a draft after a failed consent - both are fine. The dialog runs
        # non-blocking with a completion callback so re-entry can never
        # nest modally (a bug we hit during testing).
        from seasim.consent import ConsentDialog

        def _done(result: Optional[Tuple[bool, str, str]]) -> None:
            self._finish_consent(camp, result, after)

        ConsentDialog(self, self.engine, camp, block=False,
                      on_complete=_done)

    def _finish_consent(self, camp: M.Campaign,
                        result: Optional[Tuple[bool, str, str]],
                        after: Optional[Callable[[bool], None]]) -> None:
        """Apply the consent result and launch if authorized."""
        if camp.status != M.CAMPAIGN_DRAFT:
            if after:
                after(False)
            return
        if not result:
            self.store.settings.log_consent(
                "declined", "operator",
                f"Campaign '{camp.name}' - authorization not completed.")
            self.store.save(force=True)
            info(self, "Authorization not completed",
                 f"'{camp.name}' remains a DRAFT - nothing was sent.\n\n"
                 f"To launch it later: Campaigns -> select it -> "
                 f"'Authorize & launch...' and complete all 3 pages.")
            if after:
                after(False)
            return

        name, role = result
        camp.consent = True
        camp.policy_ack = True
        self.store.settings.operator_name = name
        self.store.settings.log_consent(
            "authorized", f"{name} ({role})",
            f"Campaign '{camp.name}' - {len(camp.participant_ids)} "
            f"recipients.")
        ok, why = self.engine.launch(camp.id, name)
        if not ok:
            error_dialog(self, "Launch blocked", why)
            if after:
                after(False)
            return
        self.set_status(f"Delivering '{camp.name}' - localhost only - "
                        f"rate {camp.rate_per_minute}/min")
        if after:
            after(True)

    # -- engine events -> Tk thread ------------------------------------------

    def _on_engine_event(self, kind: str, payload: dict) -> None:
        self._q.put((kind, payload))

    def _pump(self) -> None:
        """Drain engine events queued from background threads."""
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "log":
                    self.set_status(payload.get("line", ""))
                elif kind == "delivery":
                    pid = payload.get("participant")
                    p = self.store.participants.get(pid)
                    who = p.name if p else pid
                    self.set_status(f"Simulated send -> {who}")
                elif kind == "training":
                    status = payload.get("status")
                    ev = self.store.events.get(payload.get("event"))
                    if (ev is not None
                            and status in (M.ST_CLICKED, M.ST_REPORTED)
                            and self.store.settings.jit_training
                            and not ev.trained_at):
                        camp = self.engine.get_campaign(ev.campaign_id)
                        tpl = (self.engine.get_template(camp.template_id)
                               if camp else None)
                        p = self.engine.get_participant(ev.participant_id)
                        if tpl is not None:
                            from seasim.jit import JITWindow
                            self.engine.mark_trained(ev.id)
                            JITWindow(self, tpl, p.name if p else "", status)
        except queue.Empty:
            pass
        self.after(120, self._pump)

    # -- timers -----------------------------------------------------------

    def _autosave_tick(self) -> None:
        try:
            self.store.autosave_tick()
        except Exception:
            pass
        self.after(2000, self._autosave_tick)

    def _housekeeping_tick(self) -> None:
        """Trim very old events to keep the JSON store bounded."""
        try:
            with self.store.lock:
                if len(self.store.events) > C.MAX_CAMPAIGNS * 100:
                    events = sorted(self.store.events.values(),
                                    key=lambda e: e.id)
                    for e in events[:len(self.store.events)
                                    - C.MAX_CAMPAIGNS * 100]:
                        self.store.events.pop(e.id, None)
                    self.store.mark_dirty()
        except Exception:
            pass
        self.after(600000, self._housekeeping_tick)

    def _on_close(self) -> None:
        if confirm(self, "Exit SeaSim",
                   "Save state and exit? Active deliveries will stop."):
            self.engine._cancel.set()
            self.smtp_stub.stop()
            self.store.save(force=True)
            self.destroy()


def error_dialog(master, title: str, msg: str) -> None:
    from tkinter import messagebox
    messagebox.showerror(title, msg, parent=master)


def main() -> None:
    app = App()
    app.mainloop()
