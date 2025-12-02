@echo off
setlocal
chcp 65001 > nul
cls

echo ================================================
echo   シフト管理システム - データベース初期化
echo ================================================
echo.
echo この操作ではアプリのローカルデータベースを作り直します。
echo 既存データはすべて削除されます。
echo.
set /p ANSWER=続行しますか？ (y/N): 

if /I not "%ANSWER%"=="Y" (
    echo.
    echo キャンセルしました。
    goto END
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo.
echo データベースを初期化しています...
python scripts\setup_database.py --force --refresh-static

if errorlevel 1 (
    echo.
    echo エラーが発生しました。
    goto END
)

echo.
echo 完了しました。Streamlit アプリを起動できます。

:END
echo.
pause
endlocal
