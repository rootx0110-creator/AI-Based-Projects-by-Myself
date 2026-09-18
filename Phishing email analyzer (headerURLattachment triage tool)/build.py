"""Build script: packages main.py into a single-file Windows .exe via PyInstaller."""

import os
import sys
import subprocess

APP_NAME = "PhishingEmailAnalyzer"
MAIN = "main.py"

def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--icon", os.path.join("assets", "icon.ico"),
        MAIN,
    ]
    print("[BUILD]", " ".join(cmd))
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode == 0:
        out = os.path.join("dist", f"{APP_NAME}.exe")
        print(f"\n[BUILD OK] Executable created: {out}")
    else:
        print(f"\n[BUILD FAILED] Exit code: {result.returncode}")

if __name__ == "__main__":
    build()