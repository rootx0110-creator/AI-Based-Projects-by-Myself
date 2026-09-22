"""Flask server for the AI SOC Triage Assistant."""
import os
import uuid

from flask import Flask, jsonify, render_template, request, send_file

from app.engine import brain, llm
from app.demo_data import DEMOS
from app.report_generator import generate_report_html

# app/ directory (works in dev and inside the PyInstaller bundle)
APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB


@app.route("/")
def index():
    return render_template(
        "index.html",
        llm_available=llm.is_configured(),
        demos=DEMOS,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "llm_available": llm.is_configured()})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Empty message."}), 400
    if len(text) > 20000:
        return jsonify({"error": "Message too long (20k char limit)."}), 400

    use_llm = data.get("use_llm")
    context = brain.triage(text, use_llm=use_llm)
    payload = brain.to_json(context)
    payload["report_token"] = uuid.uuid4().hex
    return jsonify(payload)


@app.route("/api/report", methods=["POST"])
def api_report():
    data = request.get_json(silent=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Empty message."}), 400

    use_llm = data.get("use_llm")
    context = brain.triage(text, use_llm=use_llm)
    html = generate_report_html(context)

    import io
    return send_file(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=f"soc_triage_report_{context['timestamp'].replace(':', '').replace('-', '')}.html",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8756"))
    # Public bind allows container use; set PORT to change. Local dev: 127.0.0.1
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False)
