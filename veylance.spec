# -*- mode: python ; coding: utf-8 -*-
#
# Build with:  pyinstaller veylance.spec
# Output:      dist/VeylanceID.exe  (single file)
#
# The two ONNX models are bundled as read-only data (see datas= below).
# User data (database, enrolled faces, snapshots, PIN) is NOT bundled —
# it's written at runtime to %LOCALAPPDATA%\VeylanceID, per paths.py.

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('models/face_detection_yunet_2023mar.onnx', 'models'),
        ('models/face_recognition_sface_2021dec.onnx', 'models'),
    ],
    hiddenimports=[],
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
    name='VeylanceID',
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
    icon=None,
)
