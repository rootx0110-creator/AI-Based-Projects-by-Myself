#!/usr/bin/env python3
"""
Build a standalone Windows EXE for PortScanPro using PyInstaller.

Usage:
    python build_exe.py            # onefile build -> dist/PortScanPro.exe
    python build_exe.py --onedir   # faster startup, folder of files

Notes:
  * scapy is optional at runtime; include it with --with-scapy for SYN support.
    (EXE still works without scapy - SYN mode prints a friendly hint instead.)
  * Run this script on the OS you target: Windows -> PortScanPro.exe.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "port_scanner.py"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "PortScanPro.spec"


def run(cmd: list[str]) -> int:
    print("  $ " + " ".join(cmd))
    return subprocess.call(cmd)


def ensure_pyinstaller() -> bool:
    if shutil.which("pyinstaller"):
        return True
    print("[*] pyinstaller not found - installing...")
    return run([sys.executable, "-m", "pip", "install", "pyinstaller"]) == 0


def clean() -> None:
    for d in (BUILD,):
        shutil.rmtree(d, ignore_errors=True)
    if SPEC.exists():
        SPEC.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build PortScanPro EXE")
    ap.add_argument("--onedir", action="store_true", help="build a folder instead of a single file")
    ap.add_argument("--with-scapy", action="store_true", help="bundle scapy (enables SYN scan in the EXE)")
    ap.add_argument("--icon", help="optional .ico file for the EXE")
    args = ap.parse_args()

    if not ENTRY.exists():
        print(f"[-] missing {ENTRY}")
        return 1
    if not ensure_pyinstaller():
        print("[-] could not install pyinstaller")
        return 1

    clean()

    cmd = [sys.executable, "-m", "PyInstaller"]
    cmd += ["--onefile"] if not args.onedir else ["--onedir"]
    cmd += ["--console", "--clean", "--noconfirm"]
    cmd += ["--name", "PortScanPro"]
    if args.icon:
        cmd += ["--icon", args.icon]
    if args.with_scapy:
        cmd += ["--hidden-import", "scapy.all"]
    cmd += [
        "--hidden-import", "colorama",
        "--collect-submodules", "colorama",
        str(ENTRY),
    ]

    code = run(cmd)
    if code != 0:
        print("[-] build failed")
        return code

    exe = DIST / "PortScanPro" / "PortScanPro.exe" if args.onedir else DIST / "PortScanPro.exe"
    if exe.exists():
        print()
        print(f"[+] SUCCESS -> {exe}")
        print("[!] Distribution tip: SYN scan needs admin rights + Npcap on the target machine.")
        return 0
    print("[-] build finished but EXE not found?!")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
