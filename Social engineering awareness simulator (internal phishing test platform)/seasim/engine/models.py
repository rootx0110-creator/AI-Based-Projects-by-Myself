"""Core domain models for SeaSim.

Plain dataclasses with JSON-friendly ``to_dict`` / ``from_dict`` methods.
No framework, no database - just records persisted by ``store.py``.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from seasim.constants import ORG_DEFAULT


def new_id(prefix: str) -> str:
    """Short readable id, e.g. ``cmp_3f9a2c``."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    "Executive", "Finance", "HR", "IT", "Operations",
    "Sales", "Marketing", "Support", "Legal", "Engineering",
]

LOCATIONS = ["HQ", "Branch A", "Branch B", "Remote", "Data Center"]


@dataclass
class Participant:
    id: str
    name: str
    email: str
    department: str = "Operations"
    location: str = "HQ"
    active: bool = True
    note: str = ""

    @staticmethod
    def create(name: str, email: str, department: str, location: str,
               note: str = "") -> "Participant":
        return Participant(
            id=new_id("prt"), name=name.strip(), email=email.strip().lower(),
            department=department, location=location, note=note,
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Participant":
        return cls(
            id=d["id"], name=d.get("name", ""), email=d.get("email", ""),
            department=d.get("department", "Operations"),
            location=d.get("location", "HQ"),
            active=bool(d.get("active", True)), note=d.get("note", ""),
        )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

# Difficulty drives the wizard's difficulty selector and JIT framing.
DIFFICULTY_LEVELS = ["Low", "Medium", "High"]

TECHNIQUES = [
    "Urgency", "Authority", "Curiosity", "Fear of loss",
    "Payment / invoice", "Account security", "Calendar / meeting",
    "Rewards / gift card",
]

CATEGORY_AI = "AI-themed"       # needs explicit consent in wizard
CATEGORY_CLASSIC = "Classic"


@dataclass
class EmailTemplate:
    id: str
    name: str
    category: str = CATEGORY_CLASSIC          # Classic | AI-themed | Custom
    difficulty: str = "Medium"                # Low | Medium | High
    techniques: List[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""                            # plain text, {link} placeholder
    link_label: str = "Open"
    phishing_indicators: List[str] = field(default_factory=list)
    builtin: bool = True
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    @staticmethod
    def create(name: str, category: str, difficulty: str, techniques: List[str],
               subject: str, body: str, link_label: str = "Open",
               indicators: Optional[List[str]] = None) -> "EmailTemplate":
        return EmailTemplate(
            id=new_id("tpl"), name=name, category=category, difficulty=difficulty,
            techniques=list(techniques), subject=subject, body=body,
            link_label=link_label, phishing_indicators=list(indicators or []),
            builtin=False,
        )

    def render_subject(self) -> str:
        return self.subject

    def render_body(self, first_name: str, org: str, link: str) -> str:
        return (
            self.body.replace("{first_name}", first_name)
                     .replace("{org}", org)
                     .replace("{link}", link)
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EmailTemplate":
        return cls(
            id=d["id"], name=d.get("name", "Untitled"),
            category=d.get("category", CATEGORY_CLASSIC),
            difficulty=d.get("difficulty", "Medium"),
            techniques=list(d.get("techniques", [])),
            subject=d.get("subject", ""), body=d.get("body", ""),
            link_label=d.get("link_label", "Open"),
            phishing_indicators=list(d.get("phishing_indicators", [])),
            builtin=bool(d.get("builtin", False)),
            created=d.get("created", now_iso()),
            updated=d.get("updated", now_iso()),
        )


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

CAMPAIGN_DRAFT = "Draft"
CAMPAIGN_ACTIVE = "Active"
CAMPAIGN_COMPLETED = "Completed"
CAMPAIGN_ARCHIVED = "Archived"
CAMPAIGN_STATUSES = [CAMPAIGN_DRAFT, CAMPAIGN_ACTIVE, CAMPAIGN_COMPLETED,
                     CAMPAIGN_ARCHIVED]

# How a simulation is launched against participants.
MODE_INTERNAL = "Internal simulation page"
MODE_TRACKED_LINK = "Tracked link (Landing page)"
SIM_MODES = [MODE_INTERNAL, MODE_TRACKED_LINK]


@dataclass
class Campaign:
    id: str
    name: str
    template_id: str
    participant_ids: List[str] = field(default_factory=list)
    mode: str = MODE_INTERNAL
    scheduled: str = ""                # ISO date or "" for immediate
    rate_per_minute: int = 60
    status: str = CAMPAIGN_DRAFT
    consent: bool = False
    consent_by: str = ""
    consent_at: str = ""
    policy_ack: bool = False
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)
    completed_at: str = ""

    @staticmethod
    def create(name: str, template_id: str) -> "Campaign":
        return Campaign(id=new_id("cmp"), name=name, template_id=template_id)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Campaign":
        return cls(
            id=d["id"], name=d.get("name", "Campaign"),
            template_id=d.get("template_id", ""),
            participant_ids=list(d.get("participant_ids", [])),
            mode=d.get("mode", MODE_INTERNAL),
            scheduled=d.get("scheduled", ""),
            rate_per_minute=int(d.get("rate_per_minute", 60)),
            status=d.get("status", CAMPAIGN_DRAFT),
            consent=bool(d.get("consent", False)),
            consent_by=d.get("consent_by", ""),
            consent_at=d.get("consent_at", ""),
            policy_ack=bool(d.get("policy_ack", False)),
            created=d.get("created", now_iso()),
            updated=d.get("updated", now_iso()),
            completed_at=d.get("completed_at", ""),
        )


# ---------------------------------------------------------------------------
# Events (what happened to each email)
# ---------------------------------------------------------------------------

# Statuses for a simulated email, in typical lifecycle order.
ST_SENT = "Sent"                # delivered to the simulated inbox
ST_OPENED = "Opened"            # participant opened the email
ST_CLICKED = "Clicked"          # participant clicked the simulated link
ST_REPORTED = "Reported"        # participant used "Report Phish" in the inbox
ST_DISMISSED = "Dismissed"      # participant deleted it without action

EVENT_STATUSES = [ST_SENT, ST_OPENED, ST_CLICKED, ST_REPORTED, ST_DISMISSED]


@dataclass
class CampaignEvent:
    id: str
    campaign_id: str
    participant_id: str
    status: str = ST_SENT
    opened_at: str = ""
    clicked_at: str = ""
    reported_at: str = ""
    dismissed_at: str = ""
    trained_at: str = ""           # when JIT training moment completed
    risk_score: int = 0            # 0..100, set at training/report time

    @staticmethod
    def create(campaign_id: str, participant_id: str) -> "CampaignEvent":
        return CampaignEvent(
            id=new_id("evt"), campaign_id=campaign_id,
            participant_id=participant_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CampaignEvent":
        return cls(
            id=d["id"], campaign_id=d.get("campaign_id", ""),
            participant_id=d.get("participant_id", ""),
            status=d.get("status", ST_SENT),
            opened_at=d.get("opened_at", ""),
            clicked_at=d.get("clicked_at", ""),
            reported_at=d.get("reported_at", ""),
            dismissed_at=d.get("dismissed_at", ""),
            trained_at=d.get("trained_at", ""),
            risk_score=int(d.get("risk_score", 0)),
        )


# ---------------------------------------------------------------------------
# Settings + consent record
# ---------------------------------------------------------------------------

@dataclass
class AppSettings:
    org_name: str = ORG_DEFAULT
    operator_name: str = ""
    safe_mode: bool = True                 # always True; display-only guard
    jit_training: bool = True              # auto-show training on click
    landing_page_track: bool = True        # record clicks on tracked links
    reminder_days: int = 14                # nudge for non-responders
    default_rate: int = 60
    consent_log: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AppSettings":
        return cls(
            org_name=d.get("org_name", ORG_DEFAULT),
            operator_name=d.get("operator_name", ""),
            safe_mode=bool(d.get("safe_mode", True)),
            jit_training=bool(d.get("jit_training", True)),
            landing_page_track=bool(d.get("landing_page_track", True)),
            reminder_days=int(d.get("reminder_days", 14)),
            default_rate=int(d.get("default_rate", 60)),
            consent_log=list(d.get("consent_log", [])),
        )

    def log_consent(self, action: str, by: str, note: str = "") -> None:
        self.consent_log.append({
            "at": now_iso(), "action": action, "by": by, "note": note,
        })
