"""One-shot PyInstaller build script.

Produces a standalone ``LogAnonymizer.exe`` under ./dist.

Usage:
    python -m pip install -r requirements.txt
    python build_exe.py

Optional: put an ``app.ico`` under assets/ to brand the exe.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT, "dist")
ASSET_DIR = os.path.join(ROOT, "assets")

APP_ENTRY = os.path.join(ROOT, "app.py")
APP_NAME = "LogAnonymizer"
APP_VERSION = "1.0.0"


def main() -> int:
    print("[build] cleaning old dist artifacts...")
    for p in (DIST_DIR, os.path.join(ROOT, "build")):
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name", APP_NAME,
        # docs + core package get bundled so the frozen binary is self-contained
        "--add-data", f"{os.path.join(ROOT, 'core')}{os.pathsep}core",
        "--distpath", DIST_DIR,
        "--workpath", os.path.join(ROOT, "build", "pyinstaller"),
        "--specpath", os.path.join(ROOT, "build"),
    ]

    if os.path.exists(os.path.join(ASSET_DIR, "app.ico")):
        cmd += ["--icon", os.path.join(ASSET_DIR, "app.ico")]

    cmd.append(APP_ENTRY)

    print("[build] running:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print("[build] PyInstaller failed with exit code", rc)
        return rc

    exe = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    print(f"[build] done -> {exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())