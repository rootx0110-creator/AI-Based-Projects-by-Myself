"""Deliberately vulnerable local test target for SQLInspect live probing.

Run:  python tests/test_target.py
Then in SQLInspect: URL mode -> http://127.0.0.1:5099/vuln?id=1
Enable LIVE probing + the authorization checkbox, and scan.

This server simulates common injection behaviours:
  - /vuln?id=1       boolean-blind + time-based + error-based on ?id=
  - /clean           a non-vulnerable endpoint (should stay SAFE)

Authorised-lab use only. Binds 127.0.0.1.
"""

import re
import threading
import time

from flask import Flask, request

app = Flask(__name__)


@app.route("/vuln")
def vuln():
    v = request.args.get("id", "")
    if re.search(r"sleep\s*\(\s*2", v, re.I):
        time.sleep(2)
    if "extractvalue" in v or "updatexml" in v:
        return ("SQL error: You have an error in your SQL syntax near 'extractvalue'", 500)
    if "1'='2" in v or v.endswith("=2"):
        return "no rows", 200
    if "1'='1" in v or v.endswith("=1"):
        return "row found", 200
    return "default row", 200


@app.route("/clean")
def clean():
    return "ok", 200


if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(
        host="127.0.0.1", port=5099, debug=False, use_reloader=False), daemon=True).start()
    print("Vulnerable test target on http://127.0.0.1:5099")
    print("  /vuln?id=1   (injectable)   /clean (safe)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass