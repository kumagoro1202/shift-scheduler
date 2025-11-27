@echo off
REM ユーザーディレクトリのデータベースをリセット
echo シフトシステムのデータベースをリセットします
echo.

set USER_DB=%USERPROFILE%\.shift_scheduler\shift.db

if exist "%USER_DB%" (
    echo データベースファイルを削除しています...
    del /F "%USER_DB%"
    echo 削除完了
) else (
    echo データベースファイルは存在しません
)

echo.
echo 次回アプリケーション起動時に新しいデータベースが作成されます
echo.
pause
