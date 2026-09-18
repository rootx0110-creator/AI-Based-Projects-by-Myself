# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for NetPulse (single-file, windowed, with icon).

Build:  pyinstaller build.spec
Output: dist/NetPulse.exe
"""
import os

block_cipher = None
ROOT = os.path.abspath(SPECPATH)

a = Analysis(
    ["src\\main.py"],
    pathex=[os.path.join(ROOT, "src")],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=["psutil", "pyqtgraph", "numpy"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scapy", "wmi", "win32pdh"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NetPulse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    # manifest="assets/netpulse.manifest",  # uncomment + build to request admin
    uac_admin=False,             # set True to always elevate (full process stats)
)
