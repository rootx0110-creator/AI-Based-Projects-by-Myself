# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['F:/AI Training/Projects/Host-based intrusion detection agent (file integrity + process monitor)/main.py'],
    pathex=[],
    binaries=[],
    datas=[('F:/AI Training/Projects/Host-based intrusion detection agent (file integrity + process monitor)/assets/icon.png', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pandas', 'numpy'],
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
    name='HIDS_Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['F:/AI Training/Projects/Host-based intrusion detection agent (file integrity + process monitor)/assets/icon.ico'],
)
