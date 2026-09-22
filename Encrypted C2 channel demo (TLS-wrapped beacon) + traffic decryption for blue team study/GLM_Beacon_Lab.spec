# -*- mode: python ; coding: utf-8 -*-
"""
GLM Beacon Lab -- PyInstaller spec.
One-file windowed EXE, zero third-party runtime dependencies.
Build:  pyinstaller GLM_Beacon_Lab.spec
"""

import os

block_cipher = None
ROOT = os.path.abspath(SPECPATH)

a = Analysis(
    ["app.py"],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy", "PIL", "cryptography",
        "pytest", "setuptools", "pkg_resources", "unittest", "pydoc_data",
    ],
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
    name="GLM_Beacon_Lab",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)
