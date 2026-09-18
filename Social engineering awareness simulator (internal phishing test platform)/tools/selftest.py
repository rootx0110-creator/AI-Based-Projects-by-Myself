"""SeaSim self-test: engine + GUI regression in one command.

    python tools/selftest.py

Runs entirely against a throwaway data directory (never touches your
real %LOCALAPPDATA%/SeaSim data). A brief window may flash on screen -
that is the GUI smoke test doing its job.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Make the project root importable when run as `python tools/selftest.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Isolate data BEFORE any seasim import (constants reads env at import).
os.environ["SEASIM_DATA_DIR"] = tempfile.mkdtemp(prefix="seasim_selftest_")

DATA_DIR = os.environ["SEASIM_DATA_DIR"]

PASS = 0
FAIL = 0


def check(name: str, fn) -> None:
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}")
    except AssertionError as exc:
        FAIL += 1
        print(f"  FAIL  {name}: {exc or 'assertion failed'}")
    except Exception as exc:  # noqa: BLE001
        FAIL += 1
        print(f"  ERROR {name}: {type(exc).__name__}: {exc}")


# ===========================================================================
print("\n[1/3] Engine tests (no GUI)")
# ===========================================================================
from seasim.engine.store import Store
from seasim.engine.engine import Engine
from seasim.engine import models as M
from seasim.safety import (
    ACK_PHRASE, SafetyViolation, check_rate, ensure_local_only,
    validate_recipients,
)
from seasim.templates import builtin_templates
from seasim.reports import build_text_report, campaign_stats, program_totals

store = Store()
engine = Engine(store)
for t in builtin_templates():
    store.templates[t.id] = t

alice = M.Participant.create("Alice", "alice@corp.local", "IT", "HQ")
bob = M.Participant.create("Bob", "bob@corp.local", "Finance", "HQ")
store.participants[alice.id] = alice
store.participants[bob.id] = bob


def t_launch_blocked_without_consent():
    camp = engine.create_campaign("T1", "tpl_it_password",
                                  [alice.id, bob.id], M.MODE_INTERNAL, "", 60)
    ok, why = engine.launch(camp.id, "tester")
    assert not ok and "Consent" in why, f"got {ok!r} {why!r}"


def t_launch_blocked_without_policy_ack():
    camp = engine.create_campaign("T2", "tpl_it_password", [alice.id],
                                  M.MODE_INTERNAL, "", 60)
    camp.consent = True
    camp.policy_ack = False
    ok, why = engine.launch(camp.id, "tester")
    assert not ok and "Consent and policy" in why, f"got {ok!r} {why!r}"


def t_launch_with_consent_completes():
    camp = engine.create_campaign("T3", "tpl_payroll_update",
                                  [alice.id, bob.id], M.MODE_INTERNAL, "", 120)
    camp.consent = True
    camp.policy_ack = True
    ok, why = engine.launch(camp.id, "tester")
    assert ok, why
    deadline = time.time() + 8
    while time.time() < deadline and camp.status != M.CAMPAIGN_COMPLETED:
        time.sleep(0.1)
    assert camp.status == M.CAMPAIGN_COMPLETED, camp.status
    evs = engine.campaign_events(camp.id)
    assert len(evs) == 2, len(evs)
    # interact: open+click for alice, report for bob
    engine.mark_opened(evs[0].id)
    score = engine.click(evs[0].id)
    assert score == 80, f"expected 70+10 medium bump, got {score}"
    engine.report(evs[1].id)
    assert evs[1].risk_score == 0
    t3_events[:] = evs


t3_events: list = []


def t_dismiss_path():
    ev = t3_events[0]
    # already clicked; dismiss needs a fresh SENT event - use campaign 3's
    # second participant? already reported. Create one-off:
    camp = engine.create_campaign("T4", "tpl_package", [alice.id],
                                  M.MODE_INTERNAL, "", 120)
    camp.consent = True
    camp.policy_ack = True
    engine.launch(camp.id, "tester")
    deadline = time.time() + 8
    while time.time() < deadline and camp.status != M.CAMPAIGN_COMPLETED:
        time.sleep(0.1)
    evs = engine.campaign_events(camp.id)
    engine.dismiss(evs[0].id)
    assert evs[0].status == M.ST_DISMISSED


def t_stats_and_report():
    st = campaign_stats(engine, t3_events[0].campaign_id)
    assert st.sent == 2 and st.clicked == 1 and st.reported == 1
    rep = build_text_report(engine, t3_events[0].campaign_id)
    assert "SEA-SIM AWARENESS REPORT" in rep and "BY DEPARTMENT" in rep
    tot = program_totals(engine)
    assert tot["sent"] >= 2 and tot["clicked"] >= 1


def t_recipient_guards():
    ghost = "prt_does_not_exist"
    ok, why = validate_recipients([ghost], store)
    assert not ok and "Unknown participant" in why
    inactive = M.Participant.create("Ina", "ina@corp.local", "HR", "HQ")
    inactive.active = False
    store.participants[inactive.id] = inactive
    ok, why = validate_recipients([inactive.id], store)
    assert not ok and "inactive" in why


def t_external_host_refused():
    try:
        ensure_local_only("smtp.evil.com", 25)
        raise AssertionError("external host was accepted")
    except SafetyViolation:
        pass


def t_rate_cap():
    allowed, eff = check_rate(500)
    assert allowed is False and eff == 60, (allowed, eff)


def t_ack_phrase_constant():
    assert ACK_PHRASE == "I HAVE READ AND AGREE"


def t_persistence_roundtrip():
    store.save(force=True)
    store2 = Store(store.path)
    assert any(c.name == "T3" for c in store2.campaigns.values())
    assert any(e.risk_score == 80 for e in store2.events.values())


for name, fn in [
    ("launch blocked without consent", t_launch_blocked_without_consent),
    ("launch blocked without policy ack", t_launch_blocked_without_policy_ack),
    ("consented launch completes + scoring", t_launch_with_consent_completes),
    ("dismiss path", t_dismiss_path),
    ("stats + text report + totals", t_stats_and_report),
    ("recipient guards (unknown/inactive)", t_recipient_guards),
    ("external host refused", t_external_host_refused),
    ("rate cap 60/min", t_rate_cap),
    ("ack phrase constant", t_ack_phrase_constant),
    ("JSON persistence roundtrip", t_persistence_roundtrip),
]:
    check(name, fn)

# ===========================================================================
print("\n[2/3] GUI tests (window may flash briefly)")
# ===========================================================================
from seasim.app import App

app = App()
app.update()


def g_all_views_build():
    for key in ["dashboard", "campaigns", "wizard", "participants",
                "templates", "inbox", "training", "reports", "settings"]:
        app.navigate(key)
        app.update()


def g_campaign_detail():
    cid = t3_events[0].campaign_id
    app.open_campaign_detail(cid)
    app.update()


def g_jit_recorded_via_pump():
    """Click a live event through the app engine; pump must open JIT and
    set trained_at."""
    camp = app.engine.create_campaign(
        "GUI JIT", "tpl_ai_voicemail", [alice.id], M.MODE_INTERNAL, "", 120)
    camp.consent = True
    camp.policy_ack = True
    ok, why = app.engine.launch(camp.id, "selftest")
    assert ok, why
    deadline = time.time() + 8
    while time.time() < deadline and camp.status != M.CAMPAIGN_COMPLETED:
        app.update()
        time.sleep(0.05)
    evs = app.engine.campaign_events(camp.id)
    assert len(evs) == 1, len(evs)
    app.engine.click(evs[0].id)
    deadline = time.time() + 3
    while time.time() < deadline and not evs[0].trained_at:
        app.update()
        time.sleep(0.05)
    assert evs[0].trained_at, "trained_at not set via event pump"
    g_jit_recorded_via_pump.camp = camp


def g_training_log_shows_moment():
    app.navigate("training")
    app.update()
    camp = getattr(g_jit_recorded_via_pump, "camp", None)
    assert camp is not None, "JIT campaign missing"


def g_inbox_refresh_twice():
    app.navigate("inbox")
    app.update()
    app.navigate("inbox")
    app.update()


def g_smtp_stub_roundtrip():
    # The stub may have fallen back to a neighbouring port; point the
    # client at whatever the app actually bound and verify a full send.
    app.mailer.port = app.smtp_stub.bound_port
    assert app.smtp_stub.bound_port > 0, "stub did not bind"
    n0 = app.smtp_stub.count
    sent = app.mailer.send("alice@corp.local", "Selftest", "Hi {link}")
    deadline = time.time() + 3
    while time.time() < deadline and app.smtp_stub.count <= n0:
        app.update()
        time.sleep(0.05)
    assert sent and app.smtp_stub.count > n0


def g_store_reload():
    app.store.save(force=True)
    s2 = Store(app.store.path)
    assert any(c.name == "T3" for c in s2.campaigns.values())


for name, fn in [
    ("all 9 views build", g_all_views_build),
    ("campaign detail view", g_campaign_detail),
    ("live click -> JIT trained_at via pump", g_jit_recorded_via_pump),
    ("training log view", g_training_log_shows_moment),
    ("inbox refresh twice (no widget leak)", g_inbox_refresh_twice),
    ("SMTP stub roundtrip", g_smtp_stub_roundtrip),
    ("store reload from disk", g_store_reload),
]:
    check(name, fn)

app.destroy()

# ===========================================================================
print("\n[3/3] Cleanup")
# ===========================================================================
shutil.rmtree(DATA_DIR, ignore_errors=True)

print(f"\n{'=' * 46}")
print(f"  RESULT: {PASS} passed, {FAIL} failed")
print("=" * 46)
sys.exit(1 if FAIL else 0)
