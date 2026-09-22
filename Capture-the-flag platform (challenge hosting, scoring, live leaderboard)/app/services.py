"""Business logic services: auth, submissions, scoring, stats, feed.

Kept framework-agnostic so routes stay thin.
"""
from datetime import datetime, timezone

from . import config
from .db import JSONDatabase, verify_password


def current_points_for_challenge(db: JSONDatabase, ch: dict) -> int:
    """Points a challenge pays right now (dynamic scoring support)."""
    if not ch.get("dynamic"):
        return ch["points"]
    n = max(1, len(db.solves_for_challenge(ch["id"])))
    return max(config.DYNAMIC_MINIMUM, ch["points"] - config.DYNAMIC_SLOPE * (n - 1))


# --------------------------------------------------------------------- auth
def authenticate(db: JSONDatabase, username: str, password: str):
    user = db.get_user_by_name(username)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


def register_user(db: JSONDatabase, username: str, password: str):
    """Returns (user, error_message)."""
    username = (username or "").strip()
    if len(username) < 3:
        return None, "Username must be at least 3 characters."
    if len(password) < 4:
        return None, "Password must be at least 4 characters."
    if db.get_user_by_name(username):
        return None, "Username already taken."
    cfg = db.ctf_config()
    if not cfg.get("registration_open", True):
        return None, "Registration is closed."
    return db.create_user(username, password, is_admin=False), None


# -------------------------------------------------------------- submissions
def submit_flag(db: JSONDatabase, user, ch: dict, submitted: str, ip: str = ""):
    """Validate a flag submission. Returns (result_dict, status_code)."""
    cfg = db.ctf_config()
    if not cfg.get("competition_open", True):
        return {"ok": False, "message": "Competition is paused."}, 403

    submitted_norm = (submitted or "").strip()
    if not submitted_norm:
        return {"ok": False, "message": "Enter a flag first."}, 400

    # case-insensitive compare, exact match
    correct = submitted_norm.lower() == ch["flag"].strip().lower()

    db.add_submission(user["id"], ch["id"], submitted_norm, correct, ip=ip)
    if not correct:
        return {"ok": False, "message": "Incorrect flag. Keep digging!"}, 200

    already = any(s["user_id"] == user["id"] and s["correct"]
                  for s in db.solves_for_challenge(ch["id"]))
    awarded = current_points_for_challenge(db, ch)
    return {"ok": True, "message": f"Correct! +{awarded} points",
            "points": awarded}, 200


def first_blood_user(db: JSONDatabase, ch: dict):
    solves = db.solves_for_challenge(ch["id"])
    if not solves:
        return None
    first = min(solves, key=lambda s: s["submitted_at"])
    u = db.get_user(first["user_id"])
    return u["username"] if u else None


# -------------------------------------------------------------------- stats
def platform_stats(db: JSONDatabase):
    users = [u for u in db.all_users() if not u["is_admin"]]
    subs = db.all_submissions()
    correct = [s for s in subs if s["correct"]]
    total_points = 0
    for ch in db.all_challenges():
        total_points += current_points_for_challenge(db, ch)
    return {
        "teams": len(users),
        "challenges": len([c for c in db.all_challenges() if not c["hidden"]]),
        "submissions": len(subs),
        "accuracy": round(100.0 * len(correct) / len(subs), 1) if subs else 0.0,
        "total_points": total_points,
        "solves": len(correct),
    }


def category_breakdown(db: JSONDatabase):
    """Returns {category: {total, solved, points}} across users."""
    out = {}
    for ch in db.all_challenges():
        if ch["hidden"]:
            continue
        cat = ch["category"] or "misc"
        solved = len(db.solves_for_challenge(ch["id"]))
        entry = out.setdefault(cat, dict(total=0, solved=0, points=0))
        entry["total"] += 1
        entry["solved"] += solved
        entry["points"] += current_points_for_challenge(db, ch)
    return out


def top_solvers(db: JSONDatabase, limit=5):
    rows = db.scoreboard()[:limit]
    return rows


def solve_timeline(db: JSONDatabase, limit=200):
    """Chronological list of correct solves for charts/heatmap."""
    events = []
    for s in db.all_submissions():
        if not s["correct"]:
            continue
        u = db.get_user(s["user_id"])
        ch = db.get_challenge(s["challenge_id"])
        if not u or not ch:
            continue
        events.append({
            "at": s["submitted_at"],
            "user": u["username"],
            "challenge": ch["title"],
            "category": ch["category"],
            "points": current_points_for_challenge(db, ch),
        })
    events.sort(key=lambda e: e["at"])
    return events[-limit:]


# --------------------------------------------------------------------- feed
def feed_event(kind: str, **kw):
    """Standard shape for websocket events (and the HTML report)."""
    return dict(kind=kind, at=datetime.now(timezone.utc).isoformat(), **kw)
