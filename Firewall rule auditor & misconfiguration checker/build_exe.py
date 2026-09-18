"""Build FRAMC as a standalone Windows EXE with PyInstaller.

    pip install pyinstaller
    python build_exe.py
    # → dist/FRAMC/FRAMC.exe  (run it; opens localhost UI in the browser)

Adds vendor formats samples into the bundle for first-run demo.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "build")


def main() -> None:
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    entry = os.path.join(HERE, "run.py")
    icon = os.path.join(HERE, "frontend", "static", "favicon.ico")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "FRAMC",
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", BUILD,
        "--add-data",
        f"{os.path.join(HERE, 'frontend')}{os.pathsep}frontend",
        "--add-data",
        f"{os.path.join(HERE, 'samples')}{os.pathsep}samples",
        "--collect-submodules", "backend",
        "--hidden-import", "waitress",
    ]
    if os.path.exists(icon):
        cmd += ["--icon", icon]

    if sys.platform == "win32":
        cmd += ["--console"]

    cmd.append(entry)

    print("running PyInstaller…")
    rc = subprocess.call(cmd, cwd=HERE)
    if rc != 0:
        print("PyInstaller failed")
        sys.exit(rc)

    exe = os.path.join(DIST, "FRAMC", "FRAMC.exe")
    print("\nBuild complete:")
    print(f"  {exe}")
    print("\nRun with:  dist\\FRAMC\\FRAMC.exe  "
          "(or --host 0.0.0.0 --port 8765 for LAN access)")


if __name__ == "__main__":
    main()