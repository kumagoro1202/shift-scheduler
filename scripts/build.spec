# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
import streamlit

block_cipher = None

# Streamlitのパス取得
streamlit_path = Path(streamlit.__file__).parent

# プロジェクトルート（build.specがscripts/内にあるため）
project_root = Path(os.getcwd())

# Streamlitのメタデータとデータファイルを収集
datas = [
    (str(project_root / 'src'), 'src'),
    (str(project_root / 'pages'), 'pages'),
    (str(project_root / 'main.py'), '.'),  # main.pyをルートディレクトリに含める
    (str(project_root / 'data' / 'shift.db'), 'data'),  # サンプルデータ入りのデータベースを含める
]
datas += copy_metadata('streamlit')
datas += copy_metadata('altair')
datas += copy_metadata('pillow')
datas += copy_metadata('pydeck')
datas += copy_metadata('plotly')
# pyarrowはオプショナルなので、存在する場合のみメタデータを収集
try:
    datas += copy_metadata('pyarrow')
except Exception:
    pass
datas += collect_data_files('streamlit', include_py_files=True)
datas += collect_data_files('streamlit.web')
datas += collect_data_files('streamlit.runtime')

a = Analysis(
    [str(project_root / 'scripts' / 'launcher.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'streamlit.web',
        'streamlit.web.cli',
        'streamlit.web.server',
        'streamlit.web.server.server',
        'streamlit.web.server.routes',
        'streamlit.runtime',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.runtime.state',
        'streamlit.runtime.uploaded_file_manager',
        'streamlit.components',
        'streamlit.components.v1',
        'tornado.web',
        'tornado.websocket',
        'tornado.httpserver',
        'pandas',
        'openpyxl',
        'plotly',
        'pyarrow',
        'pyarrow.lib',
        'src.database',
        'src.optimizer',
        'src.utils',
        'src.availability_checker',
        'src.break_scheduler',
        'altair',
        'pydeck',
        'PIL',
    ],
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
    name='shift_system',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='shift_system',
)
