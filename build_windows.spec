# -*- mode: python ; coding: utf-8 -*-
# TT Cookie Robot - Windows Build Spec
# Run: pyinstaller build_windows.spec --clean

block_cipher = None

import os
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[SPEC_DIR],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('gui', 'gui'),
        ('translations', 'translations'),
        ('assets/flags', 'assets/flags'),
        ('assets/icon.ico', 'assets'),
        ('assets/icon.png', 'assets'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        # Playwright
        'playwright',
        'playwright.async_api',
        'playwright.sync_api',
        # Standard library
        'asyncio',
        'queue',
        'threading',
        'dataclasses',
        'typing',
        'logging',
        'json',
        'random',
        'datetime',
        'socket',
        # External packages
        'requests',
        'tldextract',
        'lxml',
        'lxml.etree',
        # MongoDB
        'pymongo',
        'pymongo.mongo_client',
        'pymongo.server_api',
        'dns',
        'dns.resolver',
        # Proxy testing
        'socks',
        # Core modules
        'core.octo_api',
        'core.octo_api_async',
        'core.automation',
        'core.automation.helpers',
        'core.automation.youtube',
        'core.automation.gmail',
        'core.automation.google_auth_flow',
        'core.browser',
        'core.translator',
        'core.auto_state',
        'core.auto_state_db',
        'core.database',
        'core.auto_scheduler',
        'core.notifications',
        'core.google_auth',
        'core.scheduler',
        'core.updater',
        # GUI modules
        'gui.main_window',
        'gui.styles',
        'gui.widgets',
        'gui.widgets.profile_item',
        'gui.widgets.worker_thread',
        'gui.widgets.no_scroll',
        'gui.tabs',
        'gui.dialogs',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version='version_info.txt',  # Optional: version info
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
