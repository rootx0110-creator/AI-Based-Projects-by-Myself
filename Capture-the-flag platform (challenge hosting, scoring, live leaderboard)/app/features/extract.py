"""Report data extraction: builds the payload used by the HTML report.

Kept separate so other formats (CSV/PDF) can reuse it later.
"""
from . import services


def extract_report_payload(db) -> dict:
    board = db.scoreboard()
    challenges = []
    for ch in db.all_challenges():
        solves = sorted(db.solves_for_challenge(ch["id"]),
                        key=lambda s: s["submitted_at"])
        solvers = []
        for i, s in enumerate(solves):
            u = db.get_user(s["user_id"])
            if u:
                solvers.append({"name": u["username"],
                                "at": s["submitted_at"],
                                "first_blood": i == 0})
        challenges.append({"ch": ch,
                           "points": services.current_points_for_challenge(db, ch),
                           "solvers": solvers,
                           "solve_count": len(solvers)})
    return {"board": board, "challenges": challenges,
            "stats": services.platform_stats(db),
            "timeline": services.solve_timeline(db, limit=50)}
