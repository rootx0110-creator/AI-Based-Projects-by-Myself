#!/usr/bin/env python3
"""
Beacon Detection Lab - launcher.py
Windowed entry point for the packaged Windows executable
(dist/BeaconDetectionLab.exe, built with PyInstaller - see build.bat).

Double-click behavior: starts the local dashboard on the first free
loopback port (8000+), opens the default web browser, and serves the
analysis UI. Fatal errors are logged to %TEMP%/BeaconDetectionLab.log
and shown in a message box.

Defensive/educational tool only. Nothing here generates or executes
network attacks - it analyzes logs and PCAP files.
"""

from __future__ import annotations

import sys
import tempfile
import traceback
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import dashboard

LOG_FILE = Path(tempfile.gettempdir()) / "BeaconDetectionLab.log"


def log(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} {message}\n")
    except OSError:
        pass


def show_error(message: str) -> None:
    log("FATAL " + message)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, message, "Beacon Detection Lab", 0x10)
            return
        except Exception:
            pass
    try:  # stderr can be None in windowed builds
        print(message, file=sys.stderr)
    except Exception:
        pass


def main() -> int:
    log(f"launching (frozen={getattr(sys, 'frozen', False)})")

    httpd = None
    for port in range(dashboard.PORT, dashboard.PORT + 30):
        try:
            httpd = dashboard.start_server(port)
            break
        except OSError:
            continue
    if httpd is None:
        show_error(
            "Could not open a local port (tried 8000-8029).\n\n"
            "Another instance may already be running - check "
            "http://127.0.0.1:8000 in your browser."
        )
        return 1

    url = f"http://{dashboard.HOST}:{httpd.server_address[1]}"
    log(f"serving {url}")
    try:
        webbrowser.open(url)
    except Exception as exc:
        log(f"browser open failed: {exc}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception:
        show_error("The dashboard stopped unexpectedly:\n"
                   + traceback.format_exc(limit=3))
        return 1
    finally:
        httpd.server_close()

    log("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
