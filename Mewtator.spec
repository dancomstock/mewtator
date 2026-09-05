# -*- mode: python ; coding: utf-8 -*-

import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


PROJECT_ROOT = Path(SPECPATH).resolve()
IS_WINDOWS = sys.platform == 'win32'

sv_datas, sv_binaries, sv_hiddenimports = collect_all('sv_ttk')
hiddenimports = list(sv_hiddenimports)

hiddenimports += [
    'PIL._imagingtk',
    'PIL._tkinter_finder',
]

if IS_WINDOWS:
    hiddenimports += collect_submodules('pywinstyles')

a = Analysis(
    [str(PROJECT_ROOT / 'app' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=sv_binaries,
    datas=[
        (str(PROJECT_ROOT / 'locales'), 'locales'),
        (str(PROJECT_ROOT / 'assets'), 'assets'),
        (str(PROJECT_ROOT / 'bundled_mods'), 'bundled_mods'),
    ] + sv_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Mewtator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # Avoid compressing ELF/shared-library payloads on Linux...
    upx=IS_WINDOWS,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # .ico is only relevant to the Windows executable...
    icon=str(PROJECT_ROOT / 'assets' / 'icons' / 'mewtator.ico') if IS_WINDOWS else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=IS_WINDOWS,
    upx_exclude=[],
    name='Mewtator',
)

DIST_DIR = Path(DISTPATH) / 'Mewtator'
for folder_name in ('locales', 'assets', 'bundled_mods'):
    source_dir = PROJECT_ROOT / folder_name
    target_dir = DIST_DIR / folder_name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)