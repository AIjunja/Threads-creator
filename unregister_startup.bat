@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if exist "%APP_DIR%venv\Scripts\python.exe" (
    set "PYTHON_CMD=%APP_DIR%venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

set "PYTHONUTF8=1"
"%PYTHON_CMD%" "%APP_DIR%notifier.py" --unregister
if errorlevel 1 (
    echo Failed to unregister startup notification.
    pause
    exit /b 1
)

echo.
echo Startup notification unregistered.
pause
exit /b 0
