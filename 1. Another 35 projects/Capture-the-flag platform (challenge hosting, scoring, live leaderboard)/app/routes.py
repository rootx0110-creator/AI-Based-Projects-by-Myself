"""HTTP routes (thin controllers) for the CTF platform."""
import io
import json
from datetime import datetime, timezone

from flask import (Blueprint, Response, abort, current_app, jsonify,
                   make_response, redirect, render_template, request,
                   session, url_for)

from . import config, services
from .db import utcnow_iso
from .websocket import hub

bp = Blueprint("ctf", __name__)


# ------------------------------------------------------------- view helpers
def db():
    return current_app.extensions["ctf_db"]


def current_user():
    uid = session.get("uid")
    return db().get_user(uid) if uid else None


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user():
            return redirect(url_for("ctf.login", next=request.path))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*a, **kw):
        u = current_user()
        if not u or not u["is_admin"]:
            abort(403)
        return f(*a, **kw)
    return wrapper


def broadcast(kind: str, **kw) -> None:
    hub.broadcast(services.feed_event(kind, **kw))


# --------------------------------------------------------------------- main
@bp.route("/")
def index():
    user = current_user()
    cfg = db().ctf_config()
    stats = services.platform_stats(db())
    board = db().scoreboard()[:5]
    recent = []
    for s in sorted(db().all_submissions(), key=lambda x: x["submitted_at"], reverse=True)[:8]:
        u = db().get_user(s["user_id"])
        ch = db().get_challenge(s["challenge_id"])
        if not u or not ch:
            continue
        recent.append(dict(user=u["username"], challenge=ch["title"],
                           correct=s["correct"], at=s["submitted_at"]))
    return render_template("index.html", user=user, cfg=cfg, stats=stats,
                           board=board, recent=recent)


@bp.route("/health")
def health():
    return {"status": "ok", "time": utcnow_iso()}


# --------------------------------------------------------------------- auth
@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = services.authenticate(db(), request.form.get("username", ""),
                                     request.form.get("password", ""))
        if user:
            session["uid"] = user["id"]
            session.permanent = True
            broadcast("user_login", user=user["username"])
            return redirect(request.args.get("next") or url_for("ctf.index"))
        error = "Invalid credentials."
    return render_template("login.html", error=error, cfg=db().ctf_config())


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        user, err = services.register_user(db(), request.form.get("username", ""),
                                           request.form.get("password", ""))
        if user:
            session["uid"] = user["id"]
            session.permanent = True
            broadcast("user_join", user=user["username"])
            return redirect(url_for("ctf.challenges"))
        error = err
    return render_template("register.html", error=error, cfg=db().ctf_config())


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("ctf.index"))


# --------------------------------------------------------------- challenges
@bp.route("/challenges")
@login_required
def challenges():
    user = current_user()
    solved_ids = db().user_solved_ids(user["id"])
    items = []
    for ch in db().all_challenges():
        if ch["hidden"] and not user["is_admin"]:
            continue
        n_solves = len(db().solves_for_challenge(ch["id"]))
        items.append({
            "id": ch["id"], "title": ch["title"], "category": ch["category"],
            "points": services.current_points_for_challenge(db(), ch),
            "static_points": ch["points"], "dynamic": bool(ch.get("dynamic")),
            "solves": n_solves, "solved": ch["id"] in solved_ids,
            "description": ch["description"],
        })
    cats = sorted({i["category"] for i in items})
    return render_template("challenges.html", user=user, challenges=items,
                           categories=cats, cfg=db().ctf_config())


@bp.route("/api/submit", methods=["POST"])
@login_required
def api_submit():
    data = request.get_json(silent=True) or request.form
    ch = db().get_challenge(int(data.get("challenge_id", 0)))
    if not ch:
        return jsonify({"ok": False, "message": "Unknown challenge."}), 404
    result, code = services.submit_flag(db(), current_user(), ch,
                                        data.get("flag", ""), request.remote_addr or "")
    if result.get("ok"):
        broadcast("solve", user=current_user()["username"],
                  challenge=ch["title"], category=ch["category"],
                  points=result.get("points", 0))
    else:
        broadcast("attempt", user=current_user()["username"],
                  challenge=ch["title"], correct=False)
    return jsonify(result), code


@bp.route("/api/solves/<int:cid>")
def api_solves(cid):
    ch = db().get_challenge(cid)
    if not ch:
        abort(404)
    rows = []
    for s in sorted(db().solves_for_challenge(cid), key=lambda x: x["submitted_at"]):
        u = db().get_user(s["user_id"])
        if u:
            rows.append(dict(user=u["username"], at=s["submitted_at"]))
    return jsonify({"challenge": ch["title"], "solves": rows})


# --------------------------------------------------------------- scoreboard
@bp.route("/scoreboard")
def scoreboard():
    return render_template("scoreboard.html", cfg=db().ctf_config())


@bp.route("/api/scoreboard")
def api_scoreboard():
    return jsonify({"board": db().scoreboard(),
                    "updated": utcnow_iso()})


@bp.route("/api/stats")
def api_stats():
    return jsonify(services.platform_stats(db()))


@bp.route("/api/graph")
def api_graph():
    """Score-over-time series per team + category breakdown for charts."""
    events = services.solve_timeline(db(), limit=100000)
    series = {}
    users = {u["id"]: u["username"] for u in db().all_users() if not u["is_admin"]}
    totals = {name: 0 for name in users.values()}
    for e in events:
        if e["user"] in totals:
            totals[e["user"]] += e["points"]
            series.setdefault(e["user"], []).append({"t": e["at"], "score": totals[e["user"]]})
    out = []
    for name, pts in series.items():
        out.append({"name": name, "points": pts})
    return jsonify({"series": out,
                    "categories": services.category_breakdown(db())})


# -------------------------------------------------------------------- admin
@bp.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", cfg=db().ctf_config())


@bp.route("/admin/api/overview")
@admin_required
def admin_overview():
    users = [{"id": u["id"], "username": u["username"], "admin": u["is_admin"]}
             for u in db().all_users()]
    chs = []
    for ch in db().all_challenges():
        chs.append({**ch, "solves": len(db().solves_for_challenge(ch["id"]))})
    return jsonify({"users": users, "challenges": chs, "config": db().ctf_config()})


@bp.route("/admin/api/challenge", methods=["POST"])
@admin_required
def admin_challenge_save():
    data = request.get_json(silent=True) or {}
    cid = data.get("id")
    fields = {
        "title": (data.get("title") or "").strip(),
        "category": (data.get("category") or "misc").strip().lower(),
        "points": int(data.get("points") or 100),
        "description": data.get("description") or "",
        "flag": (data.get("flag") or "").strip(),
        "dynamic": bool(data.get("dynamic")),
        "hidden": bool(data.get("hidden")),
        "flag_hint": data.get("flag_hint") or None,
    }
    if not fields["title"] or not fields["flag"]:
        return jsonify({"ok": False, "message": "Title and flag are required."}), 400
    if cid:
        ok = db().update_challenge(int(cid), **fields)
        msg = "Challenge updated." if ok else "Challenge not found."
    else:
        db().create_challenge(**fields)
        msg = "Challenge created."
    broadcast("admin", message=msg)
    return jsonify({"ok": True, "message": msg})


@bp.route("/admin/api/challenge/<int:cid>", methods=["DELETE"])
@admin_required
def admin_challenge_delete(cid):
    ok = db().delete_challenge(cid)
    return jsonify({"ok": ok, "message": "Deleted." if ok else "Not found."})


@bp.route("/admin/api/config", methods=["POST"])
@admin_required
def admin_config():
    data = request.get_json(silent=True) or {}
    db().set_ctf_config(
        ctf_name=data.get("ctf_name") or "CTF",
        registration_open=bool(data.get("registration_open")),
        competition_open=bool(data.get("competition_open")),
    )
    broadcast("admin", message="Platform settings updated.")
    return jsonify({"ok": True})


# ------------------------------------------------------------------- report
@bp.route("/report")
@login_required
def report():
    """In-app report page: preview + download button (keeps the nav)."""
    return render_template("report_page.html", cfg=db().ctf_config())


@bp.route("/report/standalone")
@login_required
def report_standalone():
    """Standalone report doc (inline CSS, no nav) — used for preview/download."""
    return _render_report()


@bp.route("/report/download")
@login_required
def report_download():
    html = _render_report(download=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Content-Disposition"] = (
        f'attachment; filename="ctf-report-{stamp}.html"')
    return resp


def _render_report(download: bool = False) -> str:
    cfg = db().ctf_config()
    board = db().scoreboard()
    challenges = []
    for ch in db().all_challenges():
        solves = sorted(db().solves_for_challenge(ch["id"]),
                        key=lambda s: s["submitted_at"])
        solvers = []
        for s in solves:
            u = db().get_user(s["user_id"])
            if u:
                solvers.append({"name": u["username"], "at": s["submitted_at"],
                                "first_blood": s["id"] == solves[0]["id"]})
        challenges.append({"ch": ch, "points": services.current_points_for_challenge(db(), ch),
                           "solvers": solvers, "solve_count": len(solves)})
    stats = services.platform_stats(db())
    timeline = services.solve_timeline(db(), limit=50)
    return render_template("report.html", cfg=cfg, board=board,
                           challenges=challenges, stats=stats,
                           timeline=timeline, download=download,
                           generated=datetime.now(timezone.utc))
