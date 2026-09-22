import os
import sys
import webbrowser
import threading
import socket
import random
from datetime import datetime

from flask import Flask, render_template, request, jsonify, abort, Response

from database import Store
import ai_engine
from report import render_report

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BASE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = APP_DIR

DATA_DIR = os.path.join(APP_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hintengine.db")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.config["JSON_SORT_KEYS"] = False

store = Store(DB_PATH)

CATEGORIES = ["Web", "Crypto", "Forensics", "Reversing", "OSINT", "Pwn", "Misc"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


def _challenge_view(cid):
    ch = store.get_challenge(cid)
    if not ch:
        abort(404)
    ch["hint_count"] = store.hint_count(cid)
    ch["hints_used"] = [h["level"] for h in store.hint_history(cid)]
    return ch


@app.route("/")
def dashboard():
    stats = store.stats()
    todo_items = store.challenges(status="todo")
    return render_template("dashboard.html", stats=stats, recent=store.recent_hints(),
                           categories=CATEGORIES, todo_items=todo_items)


@app.route("/challenges")
def challenges():
    status = request.args.get("status", "")
    category = request.args.get("category", "")
    q = request.args.get("q", "").strip()
    items = store.challenges(status=status or None, category=category or None, q=q or None)
    for it in items:
        it["hint_count"] = store.hint_count(it["id"])
    return render_template("challenges.html", items=items, categories=CATEGORIES,
                           difficulty=DIFFICULTIES, sel_status=status, sel_cat=category, q=q)


@app.route("/challenge/<int:cid>")
def challenge_page(cid):
    ch = _challenge_view(cid)
    return render_template("challenge.html", ch=ch, history=store.hint_history(cid))


@app.route("/settings")
def settings_page():
    s = store.get_settings()
    ai_enabled = str(s.get("enabled")) in ("1", "true", "True")
    return render_template("settings.html", cats=CATEGORIES, diffs=DIFFICULTIES,
                           settings=s, ai_enabled=ai_enabled)


@app.route("/api/stats")
def api_stats():
    return jsonify(store.stats())


@app.route("/api/challenges", methods=["POST"])
def api_add_challenge():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    category = body.get("category") or "Misc"
    if category not in CATEGORIES:
        category = "Misc"
    difficulty = body.get("difficulty") or "Easy"
    if difficulty not in DIFFICULTIES:
        difficulty = "Easy"
    hints = [h.strip() for h in (body.get("hints") or "").splitlines() if h.strip()]
    flag = (body.get("flag") or "").strip()
    cid = store.add_challenge(title, category, difficulty, body.get("description", ""),
                              flag, hints)
    return jsonify({"id": cid, "status": "created"})


@app.route("/api/challenge/<int:cid>/hint", methods=["POST"])
def api_hint(cid):
    ch = store.get_challenge(cid)
    if not ch:
        abort(404)
    history = store.hint_history(cid)
    result = ai_engine.make_hint(store, ch, history, store.get_settings())
    store.log_hint(cid, result["level"], result["source"], result["content"])
    remaining = max(0, len(ch["hints_json"]) - result["level"])
    return jsonify({
        "level": result["level"],
        "source": result["source"],
        "content": result["content"],
        "source_label": "AI Coach" if result["source"] == "ai" else
                        ("Prepared hint" if result["source"] == "authored" else "Engine hint"),
        "hint_count": store.hint_count(cid),
        "remaining_prepared": remaining,
    })


@app.route("/api/challenge/<int:cid>/verify", methods=["POST"])
def api_verify(cid):
    body = request.get_json(silent=True) or {}
    answer = (body.get("answer") or "").strip()
    result = store.verify_solve(cid, answer)
    if result is None:
        abort(404)
    return jsonify(result)


@app.route("/api/challenge/<int:cid>/solve", methods=["POST"])
def api_solve(cid):
    ch = store.get_challenge(cid)
    if not ch:
        abort(404)
    store.mark_solved(cid)
    return jsonify({"status": "solved"})


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        return jsonify(store.get_settings())
    body = request.get_json(silent=True) or {}
    safe = {}
    for key in ("provider", "base_url", "api_key", "model"):
        if key in body:
            safe[key] = (body[key] or "").strip()
    safe["enabled"] = "1" if body.get("enabled") else "0"
    for k, v in safe.items():
        store.set_setting(k, v)
    return jsonify(store.get_settings())


@app.route("/api/settings/test", methods=["POST"])
def api_settings_test():
    body = request.get_json(silent=True) or {}
    merged = store.get_settings()
    for key in ("provider", "base_url", "api_key", "model", "enabled"):
        if key in body:
            merged[key] = body[key]
    return jsonify(ai_engine.test_connection(merged))


@app.route("/report")
def report_preview():
    stats = store.stats()
    challenges, log = store.report_data()
    return render_template("report_page.html", stats=stats, challenges=challenges,
                           log=log, rendered=render_report(
                               stats, challenges, log,
                               datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")))


@app.route("/download/report")
def download_report():
    stats = store.stats()
    challenges, log = store.report_data()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    html = render_report(stats, challenges, log,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    return Response(html, mimetype="text/html", headers={
        "Content-Disposition": f'attachment; filename="ctf_hint_report_{stamp}.html"'})


if __name__ == "__main__":
    def _free_port(preferred):
        for p in (preferred, *random.sample(range(8800, 9999), 400)):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", p))
                    return p
                except OSError:
                    continue
        return preferred

    port = _free_port(int(os.environ.get("PORT", "8890")))
    url = f"http://127.0.0.1:{port}"
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"AI-Driven CTF Hint Engine running at {url}   (Ctrl+C to quit)")
    app.run(host="127.0.0.1", port=port, debug=False)