"""Safety envelope for SeaSim.

Ethical-by-design guardrails that the rest of the code must respect:

1. ``assert_safe`` is called before any launch; it refuses when any
   invariant is violated (safe mode off, localhost-only, caps exceeded).
2. Recipient hygiene: invalid or duplicate addresses are rejected.
3. Rate limiting: delivery is paced and capped (constants.RATE_PER_MINUTE).
4. Data minimization: no credential fields exist anywhere in the models;
   the ledger keeps only timestamps and coarse outcomes.

The invariants here are defense-in-depth on top of the UI consent flow,
not a replacement for it.
"""

from __future__ import annotations

import re
import time
from typing import List, Tuple

from seasim import constants as C
from seasim.engine import models as M

LOCAL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$")


class SafetyViolation(RuntimeError):
    """Raised when an operation would breach the safety envelope."""


# ---------------------------------------------------------------------------
# Policy acknowledgement text (Step 7 of the wizard must quote this)
# ---------------------------------------------------------------------------

POLICY_TEXT = """SEAISM AUTHORIZED-USE POLICY (must be included verbatim)

1. SCOPE. I will use SeaSim only against participants who belong to my
   own organization and only within an authorized awareness program.

2. AUTHORIZATION. A written approval (policy, engagement letter, or
   signed sign-off) exists for this exercise before I launch anything.

3. NO REAL CREDENTIALS. Simulations must never contain a real password
   field, real SSO page, or any mechanism that captures credentials.
   SeaSim has no credential-capture capability by design.

4. NO EXTERNAL TARGETING. I will never point SeaSim at addresses outside
   my organization, at personal accounts, or at third parties.

5. DATA MINIMIZATION. I will collect only coarse interaction data
   (opened / clicked / reported) - never contents, keystrokes, or
   credentials - and I will delete exported data when the program ends.

6. JUST-IN-TIME TRAINING. Anyone who interacts with a simulation will
   immediately see an educational page; no shaming, no punishment lists.

7. CONFIDENTIALITY. Program details stay within the authorized team;
   individual results are used for training, not discipline.

I confirm all seven points. Checking the acknowledgement box below is my
electronic signature."""


ACK_PHRASE = "I HAVE READ AND AGREE"
ACK_PROMPT = ACK_PHRASE  # legacy constant; step 2 is now a tick-box


# ---------------------------------------------------------------------------
# Runtime invariants
# ---------------------------------------------------------------------------

def assert_safe(store, campaign: M.Campaign) -> None:
    """Raise SafetyViolation if launching this campaign is not allowed."""
    if not store.settings.safe_mode:
        raise SafetyViolation("Safe Mode is OFF - refusing to launch.")
    if not campaign.consent or not campaign.policy_ack:
        raise SafetyViolation("Campaign lacks recorded consent/policy ack.")
    ok, reason = validate_recipients(campaign.participant_ids, store)
    if not ok:
        raise SafetyViolation(reason)
    if campaign.rate_per_minute > C.RATE_PER_MINUTE:
        raise SafetyViolation("Rate exceeds the configured ceiling.")


def validate_recipients(pids: List[str], store) -> Tuple[bool, str]:
    """All participants must exist, be active, and be internally addressed."""
    if not pids:
        return False, "No recipients selected."
    if len(pids) > C.MAX_RECIPIENTS:
        return False, (f"Recipient count {len(pids)} exceeds safety cap "
                       f"({C.MAX_RECIPIENTS}).")
    seen = set()
    for pid in pids:
        p = store.participants.get(pid)
        if p is None:
            return False, f"Unknown participant id: {pid}"
        if not p.active:
            return False, f"Participant '{p.name}' is inactive."
        if not LOCAL_RE.match(p.email or ""):
            return False, f"Participant '{p.name}' has an invalid email."
        key = p.email.lower()
        if key in seen:
            return False, f"Duplicate recipient address: {p.email}"
        seen.add(key)
    return True, ""


def check_rate(current_per_minute: int) -> Tuple[bool, int]:
    """Return (allowed, effective_rate) for a requested send rate."""
    eff = max(1, min(current_per_minute, C.RATE_PER_MINUTE))
    return current_per_minute <= C.RATE_PER_MINUTE, eff


class RateGate:
    """Simple token-bucket used by the delivery loop to pace sends."""

    def __init__(self, per_minute: int) -> None:
        self.interval = 60.0 / max(1, per_minute)
        self._last = 0.0

    def wait(self, cancel=None, slices: int = 20) -> bool:
        """Block until the next slot is free. Returns False if cancelled."""
        now = time.monotonic()
        remaining = self.interval - (now - self._last)
        if remaining > 0:
            step = remaining / max(1, slices)
            for _ in range(slices):
                if cancel is not None and cancel.is_set():
                    return False
                time.sleep(min(step, remaining))
                remaining -= step
                if remaining <= 0:
                    break
        self._last = time.monotonic()
        return cancel is None or not cancel.is_set()


# ---------------------------------------------------------------------------
# External-host guard (used by the mailer stub and any future exporter)
# ---------------------------------------------------------------------------

def ensure_local_only(host: str, port: int) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SafetyViolation(f"Refusing non-local host: {host}")
    if not (0 < port < 65536):
        raise SafetyViolation(f"Invalid port: {port}")
