# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Cookie Robot
Build command: pyinstaller build.spec
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all necessary data and submodules
datas = [
    ('config.json', '.'),
]

hiddenimports = [
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'playwright',
    'playwright.sync_api',
    'playwright.async_api',
    'requests',
    'schedule',
    # Local modules
    'gui',
    'gui.main_window',
    'core',
    'core.automation',
    'core.google_auth',
    'core.octo_api',
    'core.scheduler',
    'core.translator',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name='CookieRobot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to .ico file if you have one
)
