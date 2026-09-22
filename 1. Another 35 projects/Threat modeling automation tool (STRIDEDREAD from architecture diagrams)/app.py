"""STRIDEForge - Threat Modeling Automation Tool (STRIDE + DREAD).

Run:        python app.py        -> http://127.0.0.1:1234
Build exe:  build_exe.bat       -> dist\\STRIDEForge.exe
"""

import os
import sys
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request, Response

from threat_engine.analyzer import analyze_architecture
from threat_engine.report import generate_html_report


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, rel)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    model = request.get_json(silent=True) or {}
    try:
        result = analyze_architecture(model)
    except Exception as exc:  # surface clean JSON errors to the UI
        return jsonify({"error": "Analysis failed: %s" % exc, "summary": None, "threats": []}), 400
    status = 400 if result.get("error") else 200
    return jsonify(result), status


@app.route("/api/report", methods=["POST"])
def api_report():
    model = request.get_json(silent=True) or {}
    analysis = analyze_architecture(model)
    if analysis.get("error"):
        return jsonify({"error": analysis["error"]}), 400
    html_doc = generate_html_report(model, analysis)
    return Response(
        html_doc,
        mimetype="text/html",
        headers={
            "Content-Disposition": 'attachment; filename="threat_model_report.html"',
            "X-Report-Title": (model.get("name") or "threat-model").replace(" ", "_"),
        },
    )


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and str(sys.argv[1]).isdigit() else 1234
    if getattr(sys, "frozen", False):
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:%d" % port)).start()
    print("\n  STRIDEForge  ->  http://127.0.0.1:%d  (Ctrl+C to stop)\n" % port)
    app.run(host="127.0.0.1", port=port, debug=not getattr(sys, "frozen", False), use_reloader=not getattr(sys, "frozen", False))