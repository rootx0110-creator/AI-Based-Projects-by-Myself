# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: builds the console CLI ``dist/arpscan-cli.exe``.

Same app as ``arpscan.spec`` but with a console attached, for terminal use
and scripting (``arpscan-cli.exe 192.168.1.0/24 -f json``).
"""

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("scapy")

a = Analysis(
    ["entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="arpscan-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)