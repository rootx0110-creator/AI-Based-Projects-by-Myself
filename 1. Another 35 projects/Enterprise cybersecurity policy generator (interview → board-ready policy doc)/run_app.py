"""PolicyForge — Enterprise Cybersecurity Policy Generator.

Desktop wrapper for the single-file web app (index.html).
Use directly:        python run_app.py
Used by the EXE:    build_exe.ps1  (via PyInstaller)
"""
import os
import sys


def resource(name):
    """Resolve a bundled resource when frozen by PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def main():
    import webview

    window = webview.create_window(
        "PolicyForge — Enterprise Cybersecurity Policy Generator",
        resource("index.html"),
        width=1280,
        height=850,
        min_size=(980, 640),
        background_color="#080d1c",
    )
    webview.start()


if __name__ == "__main__":
    main()