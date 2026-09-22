"""Entry point: starts the SOC Triage Assistant web server.

As a packaged exe, the console window doubles as the server log and shows the
local URL. Close the console (or Ctrl+C) to stop the server.
"""
import os
import sys
import webbrowser
import threading

# Ensure project root is importable both as script and frozen exe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.server import app  # noqa: E402


def _open_browser(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    # 8756 avoids clashing with other common Flask apps on 5000
    port = int(os.environ.get("PORT", "8756"))
    url = f"http://127.0.0.1:{port}"

    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, _open_browser, args=(url,)).start()

    print("=" * 60)
    print("  SOC Triage Assistant — AI Chatbot for Tier-1 SOC Triage")
    print(f"  Running at: {url}")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)

    app.run(host="127.0.0.1", port=port, debug=False)
