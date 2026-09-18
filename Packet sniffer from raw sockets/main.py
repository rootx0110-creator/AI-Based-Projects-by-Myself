"""main.py — Packet Sniffer from Raw Sockets (entrypoint).

Run (Windows):  python main.py            (from an Administrator terminal)
Build .exe:     build_exe.bat  ->  dist/PacketSniffer.exe

When launched as a frozen .exe without administrator rights, the app asks
Windows for elevation (UAC prompt) and restarts itself elevated — raw
sockets require admin on Windows.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _is_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_elevated() -> bool:
    """Re-launch this exe with the UAC 'runas' verb. True on success."""
    try:
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1)  # SW_SHOWNORMAL
        return int(ret) > 32
    except Exception:
        return False


def _warn_box(message: str) -> None:
    try:
        from tkinter import Tk, messagebox
        root = Tk()
        root.withdraw()
        messagebox.showwarning("Packet Sniffer", message)
        root.destroy()
    except Exception:
        print(message)


def main() -> int:
    frozen = getattr(sys, "frozen", False)      # running as built .exe

    if sys.platform == "win32" and not _is_admin():
        if frozen:
            if _relaunch_elevated():
                return 0                        # elevated copy took over
            _warn_box(
                "Elevation was declined.\n\nRaw sockets need administrator "
                "rights: capture will fail with a permission error unless "
                "you right-click the exe and choose 'Run as administrator'.")
        else:
            print("=" * 62)
            print(" WARNING: not running as Administrator.")
            print(" Raw sockets need elevated privileges on Windows;")
            print(" Start capture will likely fail with a permission error.")
            print("=" * 62)

    print("Starting Packet Sniffer GUI…")
    from gui.app import launch
    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
