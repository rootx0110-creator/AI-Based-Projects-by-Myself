# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Custom Proxy Server (windowed .exe)."""

import os

block_cipher = None
root = os.path.abspath(SPECPATH)

a = Analysis(
    ["main.py"],
    pathex=[root],
    binaries=[],
    datas=[("assets/icon.png", "assets")] if os.path.exists(
        os.path.join(root, "assets", "icon.png")) else [],
    hiddenimports=["encodings.idna"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "pydoc_data"],
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
    name="CustomProxyServer",
    icon=os.path.join(root, "assets", "icon.ico") if os.path.exists(
        os.path.join(root, "assets", "icon.ico")) else None,
    console=False,
    disable_windowed_traceback=False,
    upx=False,
)
