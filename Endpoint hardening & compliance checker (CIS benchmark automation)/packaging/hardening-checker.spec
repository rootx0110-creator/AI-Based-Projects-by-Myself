# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Endpoint Hardening & Compliance Checker.

Build:  pyinstaller packaging/hardening-checker.spec
Result: dist/HardeningChecker.exe (onefile, windowed)
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ["../run.py"],
    pathex=[".."],
    binaries=[],
    datas=[
        ("../hardening_checker/reporting/templates", "hardening_checker/reporting/templates"),
        ("../assets/icon.ico", "assets"),
        ("../assets/icon.png", "assets"),
    ],
    hiddenimports=[
        "hardening_checker.rules.windows_rules",
        "hardening_checker.rules.linux_rules",
        "hardening_checker.rules.macos_rules",
        "hardening_checker.gui",
        "hardening_checker.gui.app",
        "hardening_checker.gui.main_window",
        "hardening_checker.gui.workers",
        "hardening_checker.gui.widgets",
        "hardening_checker.gui.theme",
        "hardening_checker.reporting.html_report",
        "hardening_checker.reporting.pdf_report",
        "hardening_checker.reporting.templates_env",
        "jinja2",
        "reportlab",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PyQt5", "PyQt6"],
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
    name="HardeningChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # windowed: no console flash on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(Path(SPECPATH).parent / "assets" / "icon.ico"),
)
