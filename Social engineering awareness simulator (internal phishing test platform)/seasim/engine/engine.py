"""The SeaSim engine: campaign lifecycle, delivery simulation, and events.

Everything that changes campaigns/events flows through this class. It
enforces the safety interlocks (see safety.py) before any launch and
emits change events consumed by the UI and the local mailer stub.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from seasim import constants as C
from seasim.engine import models as M
from seasim.engine.models import (
    Campaign, CampaignEvent, EmailTemplate, Participant, now_iso,
)


class Engine:
    def __init__(self, store) -> None:      # store: seasim.engine.store.Store
        self.store = store
        self._bus: List[Callable[[str, dict], None]] = []
        self._delivery_thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()

    # -- event bus ----------------------------------------------------------

    def subscribe(self, cb: Callable[[str, dict], None]) -> None:
        """cb(kind, payload) kinds: 'delivery', 'status', 'training'."""
        self._bus.append(cb)

    def _emit(self, kind: str, payload: dict) -> None:
        for cb in list(self._bus):
            try:
                cb(kind, payload)
            except Exception:
                pass

    # -- lookup helpers -------------------------------------------------------

    def get_participant(self, pid: str) -> Optional[Participant]:
        return self.store.participants.get(pid)

    def get_template(self, tid: str) -> Optional[EmailTemplate]:
        return self.store.templates.get(tid)

    def get_campaign(self, cid: str) -> Optional[Campaign]:
        return self.store.campaigns.get(cid)

    def campaign_events(self, cid: str) -> List[CampaignEvent]:
        return self.store.events_for(cid)

    def event_for(self, cid: str, pid: str) -> Optional[CampaignEvent]:
        for e in self.campaign_events(cid):
            if e.participant_id == pid:
                return e
        return None

    # -- campaign lifecycle ---------------------------------------------------

    def create_campaign(self, name: str, template_id: str,
                        participant_ids: List[str], mode: str,
                        scheduled: str, rate: int) -> Campaign:
        camp = Campaign.create(name, template_id)
        camp.participant_ids = list(participant_ids)
        camp.mode = mode
        camp.scheduled = scheduled
        camp.rate_per_minute = max(1, min(int(rate), C.RATE_PER_MINUTE))
        camp.status = M.CAMPAIGN_DRAFT
        with self.store.lock:
            self.store.campaigns[camp.id] = camp
        self.store.mark_dirty()
        self.store.save(force=True)
        self.store._notify("campaigns")
        return camp

    def _validate_launch(self, camp: Campaign) -> Tuple[bool, str]:
        """Full safety interlock check. Returns (ok, reason).

        Consent is checked FIRST: no campaign may proceed to any other
        validation outcome without an explicit authorization record.
        """
        if not self.store.settings.safe_mode:
            return False, "Safe Mode must be ON to launch simulations."
        if not camp.consent or not camp.policy_ack:
            return False, ("Consent and policy acknowledgement are required "
                           "before launch.")
        if camp.status != M.CAMPAIGN_DRAFT:
            return False, f"Campaign is {camp.status}, only Drafts can launch."
        if not camp.participant_ids:
            return False, "No participants selected."
        if len(camp.participant_ids) > C.MAX_RECIPIENTS:
            return False, (f"{len(camp.participant_ids)} recipients exceeds "
                           f"the {C.MAX_RECIPIENTS} safety cap.")
        tpl = self.get_template(camp.template_id)
        if tpl is None:
            return False, "Campaign template is missing."
        if camp.scheduled:
            try:
                when = datetime.fromisoformat(camp.scheduled)
            except ValueError:
                return False, "Scheduled date is invalid."
            if when < datetime.now() - timedelta(minutes=5):
                return False, "Scheduled date is in the past."
        return True, ""

    def launch(self, campaign_id: str, consent_by: str) -> Tuple[bool, str]:
        """Gate a Draft through consent, then start simulated delivery."""
        camp = self.get_campaign(campaign_id)
        if camp is None:
            return False, "Campaign not found."

        ok, reason = self._validate_launch(camp)
        if not ok:
            return False, reason

        camp.consent_by = consent_by or "operator"
        camp.consent_at = now_iso()

        camp.status = M.CAMPAIGN_ACTIVE
        camp.updated = now_iso()
        self.store.settings.log_consent(
            "launch", camp.consent_by,
            f"Campaign '{camp.name}' launched for "
            f"{len(camp.participant_ids)} participants.",
        )
        self.store.mark_dirty()
        self.store.save(force=True)

        self._emit("status", {"campaign": camp.id, "status": camp.status})
        self._start_delivery(camp)
        return True, ""

    def _start_delivery(self, camp: Campaign) -> None:
        """Background thread: emit one 'delivery' event per participant,
        rate-limited. Purely local and simulated - nothing leaves the host."""
        self._cancel.clear()

        def worker() -> None:
            delay = 60.0 / max(1, camp.rate_per_minute)
            for pid in camp.participant_ids:
                if self._cancel.is_set():
                    return
                evt = CampaignEvent.create(camp.id, pid)
                with self.store.lock:
                    self.store.events[evt.id] = evt
                self.store.mark_dirty()
                self._emit("delivery", {
                    "campaign": camp.id, "participant": pid, "event": evt.id,
                })
                # Sleep in small slices so cancel stays responsive.
                end = threading.Event()
                steps = 20
                for _ in range(steps):
                    if self._cancel.is_set():
                        return
                    end.wait(delay / steps)

            with self.store.lock:
                c = self.store.campaigns.get(camp.id)
                if c is not None:
                    c.status = M.CAMPAIGN_COMPLETED
                    c.completed_at = now_iso()
                    c.updated = now_iso()
            self.store.mark_dirty()
            self.store.save(force=True)
            self._emit("status", {"campaign": camp.id,
                                  "status": M.CAMPAIGN_COMPLETED})

        self._delivery_thread = threading.Thread(
            target=worker, name=f"delivery-{camp.id}", daemon=True,
        )
        self._delivery_thread.start()

    def cancel_delivery(self, campaign_id: str) -> None:
        """Stop a running (or finish an active) campaign."""
        self._cancel.set()
        camp = self.get_campaign(campaign_id)
        if camp is not None and camp.status == M.CAMPAIGN_ACTIVE:
            camp.status = M.CAMPAIGN_COMPLETED
            camp.completed_at = now_iso()
            camp.updated = now_iso()
            self.store.mark_dirty()
            self.store.save(force=True)
            self._emit("status", {"campaign": camp.id, "status": camp.status})

    def archive_campaign(self, campaign_id: str) -> None:
        camp = self.get_campaign(campaign_id)
        if camp is not None and camp.status in (M.CAMPAIGN_COMPLETED,
                                                M.CAMPAIGN_ARCHIVED):
            camp.status = (M.CAMPAIGN_ARCHIVED if camp.status
                           == M.CAMPAIGN_COMPLETED else M.CAMPAIGN_COMPLETED)
            camp.updated = now_iso()
            self.store.mark_dirty()
            self.store.save(force=True)
            self.store._notify("campaigns")

    def delete_campaign(self, campaign_id: str) -> None:
        """Remove campaign and its events (Drafts/Completed only)."""
        camp = self.get_campaign(campaign_id)
        if camp is None or camp.status == M.CAMPAIGN_ACTIVE:
            return
        with self.store.lock:
            self.store.campaigns.pop(campaign_id, None)
            for eid in [e.id for e in self.store.events.values()
                        if e.campaign_id == campaign_id]:
                self.store.events.pop(eid, None)
        self.store.mark_dirty()
        self.store.save(force=True)
        self.store._notify("campaigns")

    # -- inbox simulation actions ---------------------------------------------

    def inbox_actions(self, cid: str) -> List[Tuple[CampaignEvent, Participant, EmailTemplate]]:
        """Events + related records for the Inbox view (Active/Completed)."""
        camp = self.get_campaign(cid)
        if camp is None:
            return []
        tpl = self.get_template(camp.template_id)
        out: List[Tuple[CampaignEvent, Participant, EmailTemplate]] = []
        for e in self.campaign_events(cid):
            p = self.get_participant(e.participant_id)
            if p is not None and tpl is not None:
                out.append((e, p, tpl))
        return out

    def mark_opened(self, event_id: str) -> None:
        e = self.store.events.get(event_id)
        if e is None or e.status != M.ST_SENT:
            return
        e.status = M.ST_OPENED
        e.opened_at = now_iso()
        self.store.mark_dirty()
        self.store.save()
        self._emit("delivery", {"campaign": e.campaign_id, "event": e.id,
                                "action": "opened"})

    def _finish_interaction(self, e: CampaignEvent, new_status: str,
                            ts_field: str) -> int:
        """Set terminal status, compute risk score, return score."""
        e.status = new_status
        setattr(e, ts_field, now_iso())

        camp = self.get_campaign(e.campaign_id)
        score = 0
        if camp is not None:
            score = self.risk_score(camp.template_id, e.status)
        e.risk_score = score
        self.store.mark_dirty()
        self.store.save(force=True)
        self._emit("training", {"campaign": e.campaign_id, "event": e.id,
                                "status": new_status, "score": score})
        return score

    def click(self, event_id: str) -> int:
        """Participant clicked. Risky - triggers JIT training moment."""
        e = self.store.events.get(event_id)
        if e is None:
            return 0
        return self._finish_interaction(e, M.ST_CLICKED, "clicked_at")

    def report(self, event_id: str) -> int:
        """Participant used 'Report Phish'. Positive outcome."""
        e = self.store.events.get(event_id)
        if e is None:
            return 0
        return self._finish_interaction(e, M.ST_REPORTED, "reported_at")

    def dismiss(self, event_id: str) -> None:
        """Participant deleted the email without engaging."""
        e = self.store.events.get(event_id)
        if e is None:
            return
        self._finish_interaction(e, M.ST_DISMISSED, "dismissed_at")

    def mark_trained(self, event_id: str) -> None:
        e = self.store.events.get(event_id)
        if e is None:
            return
        e.trained_at = now_iso()
        self.store.mark_dirty()
        self.store.save()

    # -- scoring / JIT ---------------------------------------------------------

    def risk_score(self, template_id: str, status: str) -> int:
        """Susceptibility score 0..100. Higher = more risk signaled."""
        if status == M.ST_CLICKED:
            base = 70
        elif status == M.ST_OPENED:
            base = 30
        else:
            return 0
        tpl = self.get_template(template_id)
        if tpl is None:
            return base
        bump = {"Low": 0, "Medium": 10, "High": 20}.get(tpl.difficulty, 0)
        return min(100, base + bump)

    def jit_template(self, campaign_id: str) -> Optional[Tuple[str, str, str]]:
        """Returns (title, body, tip) for the training moment of a campaign."""
        camp = self.get_campaign(campaign_id)
        if camp is None:
            return None
        return self.jit_for_template(camp.template_id)

    def jit_for_template(self, template_id: str) -> Optional[Tuple[str, str, str]]:
        tpl = self.get_template(template_id)
        if tpl is None:
            return None
        tips = {
            "Low": "Trust, but verify: slow down when a message asks for action.",
            "Medium": "Check the sender address and hover links before clicking.",
            "High": "Even familiar names can be spoofed - verify via a second channel.",
        }
        title = f"Training moment - '{tpl.name}'"
        body = (
            "You clicked a link in a simulated phishing email.\n\n"
            "This was part of an authorized awareness exercise. No credentials "
            "were collected and nothing left your machine.\n\n"
            "Why this email could fool someone:\n"
        )
        if tpl.phishing_indicators:
            body += "\n".join(f"  - {i}" for i in tpl.phishing_indicators)
        else:
            body += "\n  - Look for pressure, unusual requests, and odd links."
        tip = tips.get(tpl.difficulty, tips["Medium"])
        return title, body, tip

    # -- scheduling ---------------------------------------------------------------

    def due_campaigns(self) -> List[Campaign]:
        """Drafts whose scheduled date has arrived (for auto-launch prompts)."""
        out: List[Campaign] = []
        for c in self.store.campaigns_sorted():
            if c.status == M.CAMPAIGN_DRAFT and c.scheduled:
                try:
                    when = datetime.fromisoformat(c.scheduled)
                except ValueError:
                    continue
                if when <= datetime.now():
                    out.append(c)
        return out

    def non_responders(self, cid: str) -> List[Participant]:
        """Participants with events still at 'Sent' - reminder candidates."""
        camp = self.get_campaign(cid)
        if camp is None:
            return []
        out: List[Participant] = []
        for e in self.campaign_events(cid):
            if e.status == M.ST_SENT:
                p = self.get_participant(e.participant_id)
                if p is not None:
                    out.append(p)
        return out

    def counts(self) -> Dict[str, int]:
        with self.store.lock:
            return {
                "participants": len(self.store.participants),
                "templates": len(self.store.templates),
                "campaigns": len(self.store.campaigns),
                "events": len(self.store.events),
            }
