# lab_app.py
# Tiny intentionally-vulnerable Flask app used to demo / verify the
# XSS Payload Tester against YOUR OWN lab. Run directly and point
# the tester at it.

import html

from flask import Flask, request, render_template_string

app = Flask(__name__)

SEARCH_PAGE = """<!doctype html><html><head><title>Lab Search</title></head><body>
<h1>Lab Search (vulnerable on purpose)</h1>
<p>You searched for: <b>{{ q | safe }}</b></p>
<script>var term = "{{ q }}";</script>
</body></html>"""

FORM_PAGE = """<!doctype html><html><body>
<h1>Lab Form</h1>
<form method="post"><input name="v" placeholder="type something"><button>Submit</button></form>
<p>Echo: {{ v | safe }}</p>
</body></html>"""

SAFE_PAGE = """<!doctype html><html><body>
<h1>Lab Green Page (input is escaped)</h1>
<p>You said: {{ v }}</p>
</body></html>"""


@app.route("/search")
def search():
    q = request.args.get("q", "")
    return render_template_string(SEARCH_PAGE, q=q)


@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        v = request.form.get("v", "")
        return render_template_string(FORM_PAGE, v=v)
    return render_template_string(FORM_PAGE, v="")


@app.route("/safe")
def safe():
    v = request.args.get("v", html.escape(request.args.get("v", "")))
    return render_template_string(SAFE_PAGE, v=v)


if __name__ == "__main__":
    print("Sample vulnerable lab running at http://127.0.0.1:5987")
    app.run(host="127.0.0.1", port=5987, threaded=True)