"""PyInstaller launcher for the SentinelForge web app.

Builds resources and logs to a sensible place when frozen, starts the Flask
server on 127.0.0.1:8600 and opens the browser.

Use `--windowed` on Windows so a console is not required; the server keeps
running in-process.
"""

import os
import sys
import threading
import webbrowser

PORT = 8600

if getattr(sys, "frozen", False):
    BASE = sys._MEIPASS  # PyInstaller one-file extraction dir
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

# Bundled Flask template/static and loganomaly package live next to the exe
# extraction root; put it on sys.path so imports resolve in both modes.
sys.path.insert(0, BASE)

from app import app  # noqa: E402  (import after sys.path setup)
import app as appmod  # noqa: E402


def _log(msg):
    try:
        print(msg)
    except Exception:
        pass


def _open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}/")


if __name__ == "__main__":
    if appmod.BASE == BASE:
        pass  # normal source run
    _log("SentinelForge - AI-assisted log anomaly detector")
    _log(f"Serving at http://127.0.0.1:{PORT}/")
    threading.Timer(1.6, _open_browser).start()
    # debug=False keeps Flask logs quiet inside the windowed exe
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)