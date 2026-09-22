# =============================================================================
#  NL2Rule Translator - Flask application
#
#  Run:            python app.py
#  Then open:      http://127.0.0.1:5001
#  Build EXE:      .\build_exe.ps1
# =============================================================================
import os
import re
import tempfile
import threading
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

from engine.report import build_report_html
from engine.translator import looks_like_rule, translate
from examples.examples import EXAMPLES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
@app.route("/")
def page_index():
    return render_template("index.html", active="home", version="1.0.0")


@app.route("/examples")
def page_examples():
    return render_template("examples.html", active="examples", examples=EXAMPLES)


@app.route("/about")
def page_about():
    return render_template("about.html", active="about", version="1.0.0")


# ---------------------------------------------------------------------------
# translation API
# ---------------------------------------------------------------------------
@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Please describe a behavior to translate."}), 400
    if looks_like_rule(text):
        return jsonify({
            "error": ("It looks like you pasted a rule, not natural language. "
                      "Describe the behavior you want to DETECT in plain English."),
        }), 422
    try:
        result = translate(text)
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Translation failed: {exc}"}), 500
    return jsonify(result)


@app.route("/api/translate/preview", methods=["POST"])
def api_translate_preview():
    """Lightweight preview for the typing-as-you-go path (entities only)."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": True, "count": 0, "entities": {}})
    from engine.entities import extract_entities, summarize
    entities = extract_entities(text)
    return jsonify({"ok": True, "count": entities.count(),
                    "entities": summarize(entities)})


# ---------------------------------------------------------------------------
# report download
# ---------------------------------------------------------------------------
@app.route("/api/report", methods=["POST"])
def api_report():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Nothing to report on."}), 400
    result = translate(text)
    fname = "nl2rule-report-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".html"
    fpath = os.path.join(REPORT_OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(build_report_html(result, version="1.0.0"))
    return send_file(fpath, as_attachment=True, download_name=fname,
                     mimetype="text/html")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "version": "1.0.0", "time": datetime.utcnow().isoformat()})


@app.route("/api/examples")
def api_examples():
    return jsonify({"examples": EXAMPLES})


@app.route("/api/examples-by-index")
def api_examples_index():
    i = request.args.get("i", type=int)
    if i is None or not (0 <= i < len(EXAMPLES)):
        return jsonify({"error": "bad index"}), 404
    return jsonify(EXAMPLES[i])


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return render_template("index.html", active=""), 404


def _pick_port(preferred):
    import socket
    preferred = int(preferred)
    for port in range(preferred, preferred + 15):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


if __name__ == "__main__":
    port = _pick_port(os.environ.get("NL2PORT", "5001"))
    url = f"http://127.0.0.1:{port}"
    print("\n  NL2Rule Translator - Natural Language -> Sigma / YARA\n"
          f"  -> {url}\n")
    if os.environ.get("NL2OPEN", "1") != "0":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port,
            debug=os.environ.get("NL2DEBUG") == "1", use_reloader=False)