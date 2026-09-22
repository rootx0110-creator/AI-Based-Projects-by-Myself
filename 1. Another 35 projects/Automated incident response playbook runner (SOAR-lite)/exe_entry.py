"""Entry point for the standalone EXE build (see build_exe.ps1).

Boots the SOAR-Lite Flask app, opens the browser, and blocks.
Everything (server, seeding, live execution workers) is started by app.py.
"""

import os
import sys
import threading
import webbrowser

# be explicit: open browser by default in EXE mode
os.environ.setdefault("SOAR_OPEN_BROWSER", "1")

import app  # noqa: E402  (bundled at bundle root by PyInstaller)

if __name__ == "__main__":
    import socket

    def pick_port(preferred):
        preferred = int(preferred)
        for port in range(preferred, preferred + 12):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        return preferred

    port = pick_port(os.environ.get("SOAR_PORT", "5000"))
    url = f"http://127.0.0.1:{port}"

    print("\n  SOAR-Lite - Automated Incident Response Playbook Runner (EXE)")
    print(f"  -> {url}")
    print("  Close this window to stop the SOC dashboard.\n")

    if os.environ.get("SOAR_OPEN_BROWSER") != "0":
        threading.Timer(0.9, lambda: webbrowser.open(url)).start()

    try:
        app.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass