"""
PyInstallerでビルドされたexeからStreamlitを起動するランチャー
"""
import sys
import os
from pathlib import Path

# _MEIPASSパスを設定
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
    sys.path.insert(0, str(base_path / "src"))
    
    # Streamlitを起動
    import streamlit.web.cli as stcli
    
    script_path = str(base_path / "main.py")
    
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.port=8501",
        "--server.address=localhost",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.enableXsrfProtection=false",
        "--server.enableCORS=true",
        "--global.developmentMode=false",
    ]
    
    sys.exit(stcli.main())
