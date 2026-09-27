# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Coleta recursivamente recursos, binários e hiddenimports de faster_whisper, ctranslate2 e live2d
datas_fw, binaries_fw, hiddenimports_fw = collect_all('faster_whisper')
datas_ct, binaries_ct, hiddenimports_ct = collect_all('ctranslate2')
datas_l2d, binaries_l2d, hiddenimports_l2d = collect_all('live2d')

added_files = [
    ('InterfaceAva', 'InterfaceAva'),
    ('assets/live2d/kuri_model', 'assets/live2d/kuri_model'),
    ('models/whisper-base', 'models/whisper-base'),
    ('models/silero-vad', 'models/silero-vad'),
    ('kuri_skills', 'kuri_skills'),
    ('prompt_kuri.txt', '.'),
] + datas_fw + datas_ct + datas_l2d

hiddenimports = [
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtOpenGLWidgets',
    'live2d.v3',
    'OpenGL',
    'sounddevice',
    'engineio.async_drivers.threading', # às vezes necessário para async
] + hiddenimports_fw + hiddenimports_ct + hiddenimports_l2d

a = Analysis(
    ['kuri_desktop.py'],
    pathex=[],
    binaries=binaries_fw + binaries_ct + binaries_l2d,
    datas=added_files,
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
    [],
    exclude_binaries=True,
    name='KuriIA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Mantemos temporariamente True para depuração de erros
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='kuri.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KuriIA',
)
