# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['editor/wizard_editor.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('editor/templates', 'templates'),
        ('hallmark-scribble/shared/ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin'),
        ('hallmark-scribble/shared/ffmpeg/bin/ffplay.exe', 'ffmpeg/bin'),
        ('hallmark-scribble/shared/ffmpeg/bin/ffprobe.exe', 'ffmpeg/bin'),
    ],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'cv2', 'vlc'],
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
    [],
    exclude_binaries=True,
    name='Hallmark Editor',
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Hallmark Editor',
)
