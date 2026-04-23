@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%venv\Scripts\python.exe" (
    echo [AI Thread App] First run detected. Running setup...
    call "%APP_DIR%setup.bat"
    if errorlevel 1 exit /b 1
)

"%APP_DIR%venv\Scripts\python.exe" -c "import customtkinter" >nul 2>nul
if errorlevel 1 (
    echo [AI Thread App] Missing dependencies detected. Running setup...
    call "%APP_DIR%setup.bat"
    if errorlevel 1 exit /b 1
)

"%APP_DIR%venv\Scripts\python.exe" -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy()" >nul 2>nul
if errorlevel 1 (
    echo [AI Thread App] The Windows UI runtime check failed.
    echo Reinstall Python with Tcl/Tk support, then run this file again.
    echo Download Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

set "PYTHONUTF8=1"
echo [AI Thread App] Starting app...
"%APP_DIR%venv\Scripts\python.exe" "%APP_DIR%app.py"

if errorlevel 1 (
    echo.
    echo The app exited with an error.
    echo Check the message above or the debug log at: %USERPROFILE%\thread_app_debug.log
    pause
    exit /b 1
)

exit /b 0
