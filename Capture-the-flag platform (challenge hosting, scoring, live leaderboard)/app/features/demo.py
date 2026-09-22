"""Demo data seeder: creates users, solves, and failed attempts so the
leaderboard, charts, and feed look alive on first run."""
import random

from ..db import utcnow_iso

NAMES = ["neo", "trinity", "morpheus", "cipher", "dozer", "tank",
         "switch", "apoc", "mouse", "sati"]


def ensure_demo_data(db) -> None:
    if db._data.get("demo_seeded"):
        return  # once only
    random.seed(1337)
    challenges = db.all_challenges()
    if not challenges:
        return
    # users
    users = []
    for i, name in enumerate(NAMES, start=1):
        u = db.get_user_by_name(name)
        if not u:
            u = db.create_user(name, f"pass-{name}-123")
        users.append(u)

    import datetime as _dt
    base = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=6)
    subs = []
    sid = max((s["id"] for s in db.all_submissions()), default=0)

    # each user solves a random-ish prefix of challenges over time
    plan = {
        "neo": 6, "trinity": 5, "morpheus": 4, "cipher": 3, "dozer": 3,
        "tank": 2, "switch": 2, "apoc": 1, "mouse": 1, "sati": 0,
    }
    for u in users:
        n = plan.get(u["username"], 0)
        chosen = challenges[:n]
        t = base
        for ch in chosen:
            sid += 1
            subs.append(dict(id=sid, user_id=u["id"], challenge_id=ch["id"],
                             submitted="flag{guess}", correct=True,
                             ip="127.0.0.1",
                             submitted_at=(t + _dt.timedelta(minutes=random.randint(5, 90))).isoformat()))
            t = t + _dt.timedelta(minutes=random.randint(10, 50))
        # a couple of failed attempts for realism
        if n < len(challenges):
            sid += 1
            subs.append(dict(id=sid, user_id=u["id"],
                             challenge_id=challenges[n]["id"],
                             submitted="flag{wrong}", correct=False, ip="127.0.0.1",
                             submitted_at=t.isoformat()))
    db._data["submissions"].extend(subs)
    db._data["demo_seeded"] = True
    db.save()
