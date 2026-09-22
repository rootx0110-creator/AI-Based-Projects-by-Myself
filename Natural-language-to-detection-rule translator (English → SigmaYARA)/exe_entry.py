"""Entry point for the standalone EXE build (see build_exe.ps1).

Boots the NL2Rule Translator Flask app, opens the browser, and blocks.
Everything (server, rules engine) is started by app.py.
"""

import os
import sys
import threading
import webbrowser

os.environ.setdefault("NL2OPEN", "1")

import app  # noqa: E402  (bundled at bundle root by PyInstaller)

if __name__ == "__main__":
    import socket

    def pick_port(preferred):
        preferred = int(preferred)
        for port in range(preferred, preferred + 15):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        return preferred

    port = pick_port(os.environ.get("NL2PORT", "5001"))
    url = f"http://127.0.0.1:{port}"

    print("\n  NL2Rule Translator - Natural Language to Detection Rules (EXE)\n"
          f"  -> {url}\n"
          "  Close this window to stop the server.\n")

    if os.environ.get("NL2OPEN") != "0":
        threading.Timer(0.9, lambda: webbrowser.open(url)).start()

    try:
        app.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass