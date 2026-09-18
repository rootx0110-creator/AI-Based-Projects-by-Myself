#!/usr/bin/env python3
"""Build the forensic toolkit into a single windowed EXE with PyInstaller."""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")


def main():
    os.chdir(ROOT)
    for d in (DIST, BUILD):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "ForensicAcquisitionToolkit",
        "--windowed",
        "--onefile",
        "--icon", os.path.join(ROOT, "assets", "app.ico"),
        "--collect-all", "customtkinter",
        "--paths", ROOT,
        os.path.join(ROOT, "main.py"),
    ]
    subprocess.check_call(cmd)
    print("\n[OK] EXE built at:", os.path.join(DIST, "ForensicAcquisitionToolkit.exe"))


if __name__ == "__main__":
    main()