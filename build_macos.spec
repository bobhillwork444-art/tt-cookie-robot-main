# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Get current directory
current_dir = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('translations', 'translations'),
        ('assets/flags', 'assets/flags'),
        ('gui', 'gui'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'playwright',
        'playwright.async_api',
        'asyncio',
        'requests',
        'tldextract',
        'lxml',
        'lxml.etree',
    ] + collect_submodules('gui') + collect_submodules('core'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TTCookieRobot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TTCookieRobot',
)

app = BUNDLE(
    coll,
    name='TT Cookie Robot.app',
    icon='assets/icon.icns',
    bundle_identifier='com.ttteam.cookierobot',
    info_plist={
        'CFBundleName': 'TT Cookie Robot',
        'CFBundleDisplayName': 'TT Cookie Robot',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13.0',
    },
)
