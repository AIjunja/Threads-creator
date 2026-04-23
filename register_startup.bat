@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%venv\Scripts\python.exe" (
    echo [AI Thread App] Setup is required before startup registration.
    call "%APP_DIR%setup.bat"
    if errorlevel 1 exit /b 1
)

set "PYTHONUTF8=1"
"%APP_DIR%venv\Scripts\python.exe" "%APP_DIR%notifier.py" --register
if errorlevel 1 (
    echo Failed to register startup notification.
    pause
    exit /b 1
)

echo.
echo Startup notification registered.
echo It will show a Windows toast after sign-in.
pause
exit /b 0
