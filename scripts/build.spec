# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import subprocess
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata, collect_all
import streamlit

block_cipher = None

# Streamlitのパス取得
streamlit_path = Path(streamlit.__file__).parent

# プロジェクトルート（build.specがscripts/内にあるため）
project_root = Path(os.getcwd())

# サンプルデータ入りデータベースを最新のコードで生成
print("Generating sample data with the latest code...")
result = subprocess.run(
    [sys.executable, str(project_root / 'scripts' / 'init_sample_data.py'), '--force'],
    cwd=str(project_root),
    capture_output=True,
    text=True
)
if result.returncode != 0:
    print(f"Warning: Failed to generate sample data: {result.stderr}")
else:
    print("Sample data generation completed successfully")

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

# pyarrowの完全な収集
try:
    pyarrow_datas, pyarrow_binaries, pyarrow_hiddenimports = collect_all('pyarrow')
    datas += pyarrow_datas
    datas += copy_metadata('pyarrow')
    print(f"PyArrow collected: {len(pyarrow_datas)} data files, {len(pyarrow_binaries)} binaries")
except Exception as e:
    print(f"Warning: Failed to collect pyarrow: {e}")

datas += collect_data_files('streamlit', include_py_files=True)
datas += collect_data_files('streamlit.web')
datas += collect_data_files('streamlit.runtime')

a = Analysis(
    [str(project_root / 'scripts' / 'launcher.py')],
    pathex=[],
    binaries=pyarrow_binaries if 'pyarrow_binaries' in locals() else [],
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
            'altair',
            'pydeck',
            'PIL',
            'pyarrow',
            'pyarrow.lib',
            'pyarrow.vendored',
        ] + collect_submodules('shift_scheduler') 
          + collect_submodules('pyarrow')
          + (pyarrow_hiddenimports if 'pyarrow_hiddenimports' in locals() else []),
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
