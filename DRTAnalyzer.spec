# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [('docs', 'docs'), ('README.md', '.'), ('CHANGELOG.md', '.'), ('THIRD_PARTY_NOTICES.md', '.')]
datas += copy_metadata('numpy')
datas += copy_metadata('scipy')
datas += copy_metadata('PySide6')
datas += copy_metadata('PySide6_Essentials')
datas += copy_metadata('PySide6_Addons')
datas += copy_metadata('shiboken6')
datas += copy_metadata('pyqtgraph')
datas += copy_metadata('openpyxl')


a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=['PySide6.QtSvg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'tkinter', 'matplotlib', 'pytest', '_pytest', 'pyqtgraph.opengl'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DRTAnalyzer',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DRTAnalyzer',
)
