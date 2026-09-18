# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: builds the double-clickable GUI app ``dist/arpscan.exe``.

Usage:
    python -m PyInstaller arpscan.spec --noconfirm --clean

Design notes:
* Windowed build (``console=False``): double-clicking opens the Tkinter GUI
  instead of a console that flashes and closes.
* Entry is ``entry_gui.py`` (a top-level script) because ``arpscan/__main__.py``
  uses a relative import, which PyInstaller cannot run as a main script.
* scapy is bundled with ``collect_all`` so the raw-ARP backend works; on
  machines without Npcap/admin the auto fallback switches to the system
  backend.
* tkinter must NOT be excluded here (it is the GUI toolkit).
"""

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("scapy")

a = Analysis(
    ["entry_gui.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib"],
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
    name="arpscan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)